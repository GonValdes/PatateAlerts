"""High-growth exit engine implementing docs/high-growth/exit.md per lot.

Each lot corresponds to one real-world buy in config.bought_positions.
Tracks state in SQLite and sends notifications for stops and exits.
"""

import logging
from datetime import date
from typing import Dict, Any, List, Optional, Tuple

from storage.db import Database
from storage.models import PriceHistory, HighGrowthLotState
from data_provider import DataProvider

logger = logging.getLogger(__name__)


class HighGrowthExitEngine:
    """Applies high-growth exit rules per lot."""

    ATR_PERIOD = 14
    SMA200_PERIOD = 200
    DMA1000_PERIOD = 1000  # 200 WMA = 1000 DMA

    def __init__(
        self,
        db: Database,
        data_provider: DataProvider,
        notifiers: List,
    ) -> None:
        self.db = db
        self.data_provider = data_provider
        self.notifiers = notifiers

        self.price_history = PriceHistory(db)
        self.lot_state = HighGrowthLotState(db)

    def process_lot(self, lot: Dict[str, Any]) -> None:
        """Process a single lot according to exit rules.
        
        Args:
            lot: Dict with keys: id, symbol, entry_price, shares
        """
        lot_id = lot.get("id")
        symbol = lot.get("symbol")
        entry_price = float(lot.get("entry_price"))
        shares = int(lot.get("shares"))

        if not lot_id or not symbol:
            logger.error("Lot is missing required fields 'id' or 'symbol': %s", lot)
            return

        logger.info("Processing lot %s (%s)", lot_id, symbol)

        latest = self.data_provider.get_price_data(symbol)
        if not latest:
            logger.warning("Could not fetch latest price data for %s", symbol)
            return

        self.price_history.insert_or_update(
            symbol=symbol,
            date=latest["date"],
            open=latest["open"],
            high=latest["high"],
            low=latest["low"],
            close=latest["close"],
            volume=latest["volume"],
        )

        current_close = latest["close"]
        current_date = latest["date"]

        self._ensure_historical_cache(symbol)

        state = self.lot_state.get_state(lot_id)
        is_first_time = state is None
        if state is None:
            state = self.lot_state.create_default_state(
                lot_id=lot_id,
                symbol=symbol,
                entry_price=entry_price,
                shares=shares,
            )
        else:
            if (
                abs(state["entry_price"] - entry_price) > 1e-8
                or state["shares_original"] != shares
            ):
                logger.warning(
                    "Config for lot %s differs from stored state; updating static fields",
                    lot_id,
                )
                state["entry_price"] = entry_price
                state["shares_original"] = shares

        if state["atr_entry"] is None:
            atr_entry = self._compute_atr_entry(symbol)
            if atr_entry is None:
                logger.warning(
                    "Not enough data to compute ATR_entry for %s; skipping lot %s",
                    symbol,
                    lot_id,
                )
                self.lot_state.upsert_state(state)
                return

            state["atr_entry"] = atr_entry
            state["initial_stop_price"] = entry_price - 2.0 * atr_entry

        new_stops: List[str] = []
        exits: List[Tuple[str, int]] = []

        self._send_negative_trend_notification_if_needed(
            symbol=symbol,
            lot_id=lot_id,
            current_close=current_close,
            current_date=current_date,
            state=state,
        )

        if (
            state.get("initial_stop_price") is not None
            and current_close < state["initial_stop_price"]
        ):
            exits.append(("Early failure stop (Entry − 2 × ATR_entry)", state["shares_original"]))

        stop1_new = self._maybe_define_stop1(entry_price, state, current_close, symbol)
        if stop1_new is not None:
            new_stops.append(stop1_new)

        milestone_new = self._maybe_define_milestone_stops(entry_price, state, current_close, symbol)
        new_stops.extend(milestone_new)

        stop_exits = self._evaluate_stops(entry_price, state, current_close)
        exits.extend(stop_exits)

        if is_first_time or new_stops or exits:
            self._send_unified_notification(
                symbol, lot_id, entry_price, current_close, state, new_stops, exits, is_first_time
            )

        state["last_eval_date"] = current_date
        state["structural_exit_triggered"] = False
        state["early_failure_triggered"] = False
        self.lot_state.upsert_state(state)

    def _ensure_historical_cache(self, symbol: str, min_days: int = 260) -> None:
        """Ensure we have enough history cached for ATR, SMA200, and optionally 1000 DMA."""
        hist = self.price_history.get_historical_prices(symbol, days=min_days)
        if len(hist) >= min_days:
            return

        logger.info("Fetching additional historical data for %s", symbol)
        provider_hist = self.data_provider.get_historical_prices(symbol, days=min_days)
        for row in provider_hist:
            self.price_history.insert_or_update(
                symbol=symbol,
                date=row["date"],
                open=row["open"],
                high=row["high"],
                low=row["low"],
                close=row["close"],
                volume=row["volume"],
            )

    def _compute_atr_entry(self, symbol: str) -> Optional[float]:
        """Compute ATR(14) using simple average of True Range over last 14 days."""
        hist = self.price_history.get_historical_prices(symbol, days=self.ATR_PERIOD + 1)
        if len(hist) <= self.ATR_PERIOD:
            return None

        trs: List[float] = []
        prev_close: Optional[float] = None
        for row in hist:
            high = float(row["high"])
            low = float(row["low"])
            close = float(row["close"])
            if prev_close is None:
                tr = high - low
            else:
                tr = max(
                    high - low,
                    abs(high - prev_close),
                    abs(low - prev_close),
                )
            trs.append(tr)
            prev_close = close

        if len(trs) < self.ATR_PERIOD:
            return None

        recent_trs = trs[-self.ATR_PERIOD :]
        return sum(recent_trs) / float(len(recent_trs))

    def _compute_sma200(self, symbol: str) -> Optional[float]:
        """Compute 200-day simple moving average of closes."""
        hist = self.price_history.get_historical_prices(symbol, days=self.SMA200_PERIOD)
        if len(hist) < self.SMA200_PERIOD:
            return None

        closes = [float(row["close"]) for row in hist[-self.SMA200_PERIOD :]]
        if not closes:
            return None
        return sum(closes) / float(len(closes))

    def _compute_dma1000(self, symbol: str) -> Optional[float]:
        """Compute 1000-day SMA (200 WMA equivalent) for negative trend notification."""
        hist = self.price_history.get_historical_prices(symbol, days=self.DMA1000_PERIOD + 100)
        if len(hist) < self.DMA1000_PERIOD:
            return None
        closes = [float(row["close"]) for row in hist[-self.DMA1000_PERIOD :]]
        return sum(closes) / len(closes)

    def _send_negative_trend_notification_if_needed(
        self,
        symbol: str,
        lot_id: str,
        current_close: float,
        current_date: date,
        state: Dict[str, Any],
    ) -> None:
        """Notify when weekly close newly drops below 200 DMA or 200 WMA (no exit). Evaluated on Fridays.

        Edge-triggered: fires only on the transition from inactive to active for each condition
        (tracked per lot in state). While the condition persists, it stays silent. If the condition
        later clears and re-triggers, it notifies again.
        """
        if isinstance(current_date, str):
            try:
                current_date = date.fromisoformat(current_date)
            except (ValueError, TypeError):
                return
        if not hasattr(current_date, "weekday") or current_date.weekday() != 4:
            return

        sma200 = self._compute_sma200(symbol)
        below_dma = sma200 is not None and current_close < sma200

        self._ensure_historical_cache(symbol, min_days=self.DMA1000_PERIOD + 100)
        dma1000 = self._compute_dma1000(symbol)
        below_wma = dma1000 is not None and current_close < dma1000

        newly_below_dma = below_dma and not state.get("trend_below_dma_active")
        newly_below_wma = below_wma and not state.get("trend_below_wma_active")

        state["trend_below_dma_active"] = below_dma
        state["trend_below_wma_active"] = below_wma

        if not newly_below_dma and not newly_below_wma:
            return

        reasons = []
        if newly_below_dma:
            reasons.append("weekly close < 200 DMA")
        if newly_below_wma:
            reasons.append("weekly close < 200 WMA")
        message = (
            f"Negative trend — {symbol} ({lot_id})\n"
            f"Latest close (weekly): ${current_close:.2f}\n"
            f"Triggered: {' and '.join(reasons)}"
        )
        for notifier in self.notifiers:
            if not notifier.enabled:
                continue
            try:
                notifier.send(message)
                logger.info("Negative trend notification sent for lot %s", lot_id)
            except Exception as exc:
                logger.error("Failed to send negative trend notification via %s: %s", notifier.name, exc)

    def _maybe_define_stop1(
        self,
        entry_price: float,
        state: Dict[str, Any],
        current_close: float,
        symbol: str,
    ) -> Optional[str]:
        """Define Stop_1 (initial profit lock) when price reaches 1.5× entry. ATR recalculated at trigger."""
        if state.get("stop1_defined") or current_close < 1.5 * entry_price:
            return None

        atr_current = self._compute_atr_entry(symbol) or float(state["atr_entry"])
        logger.info("Recalculated ATR=%.2f for Stop_1 (was ATR_entry=%.2f)", atr_current, state.get("atr_entry"))

        stop_price = entry_price + atr_current
        state["stop1_price"] = stop_price
        state["stop1_defined"] = True
        exit_shares = max(1, int(round(state["shares_original"] * 0.25)))
        return f"Stop_1: ${stop_price:.2f} ({exit_shares} shares)"

    def _maybe_define_milestone_stops(
        self,
        entry_price: float,
        state: Dict[str, Any],
        current_close: float,
        symbol: str,
    ) -> List[str]:
        """Define Stop_2..Stop_5 when milestones M1..M4 are first reached. ATR recalculated at trigger."""
        messages: List[str] = []
        milestones = [
            ("m1_reached", "stop2_price", 2.0, "Stop_2", 0.20),
            ("m2_reached", "stop3_price", 3.0, "Stop_3", 0.10),
            ("m3_reached", "stop4_price", 4.0, "Stop_4", 0.10),
            ("m4_reached", "stop5_price", 6.0, "Stop_5", 0.10),
        ]

        for reached_key, stop_key, multiple, stop_name, exit_pct in milestones:
            if state.get(reached_key) or current_close < multiple * entry_price:
                continue

            atr_current = self._compute_atr_entry(symbol) or float(state["atr_entry"])
            logger.info("Recalculated ATR=%.2f for %s (was ATR_entry=%.2f)", atr_current, stop_name, state.get("atr_entry"))

            stop_price = multiple * entry_price - 2.0 * atr_current
            state[reached_key] = True
            state[stop_key] = stop_price
            exit_shares = max(1, int(round(state["shares_original"] * exit_pct)))
            messages.append(f"{stop_name}: ${stop_price:.2f} ({exit_shares} shares)")

        return messages

    def _evaluate_stops(
        self,
        entry_price: float,
        state: Dict[str, Any],
        current_close: float,
    ) -> List[Tuple[str, int]]:
        """Evaluate all active stops and compute share exits (percentages of original position)."""
        exits: List[Tuple[str, int]] = []
        original = int(state["shares_original"])
        stop_defs = [
            ("stop1_price", "stop1_triggered", "Stop_1 (+50% profit lock)", 0.25),
            ("stop2_price", "stop2_triggered", "Stop_2 (M1 +100%)", 0.20),
            ("stop3_price", "stop3_triggered", "Stop_3 (M2 +200%)", 0.10),
            ("stop4_price", "stop4_triggered", "Stop_4 (M3 +300%)", 0.10),
            ("stop5_price", "stop5_triggered", "Stop_5 (M4 +500%)", 0.10),
        ]

        for stop_key, trig_key, label, pct in stop_defs:
            price = state.get(stop_key)
            if price is None or state.get(trig_key) or current_close >= price:
                continue

            shares_to_sell = max(1, int(round(original * pct)))
            exits.append((label, shares_to_sell))
            state[trig_key] = True

        return exits

    def _send_unified_notification(
        self,
        symbol: str,
        lot_id: str,
        entry_price: float,
        current_close: float,
        state: Dict[str, Any],
        new_stops: List[str],
        exits: List[Tuple[str, int]],
        is_first_time: bool = False,
    ) -> None:
        """Send unified notification. First time: all applicable stops. Otherwise: new stops/exits only."""
        lines = [f"{symbol} ({lot_id})"]
        if exits:
            lines.append(f"Latest close: ${current_close:.2f}")
        if is_first_time:
            applicable_stops = self._get_all_applicable_stops(entry_price, current_close, state)
            for stop_name, stop_price, exit_shares in applicable_stops:
                lines.append(f"{stop_name}: ${stop_price:.2f} ({exit_shares} shares)")
        else:
            lines.extend(new_stops)
        
        for label, shares in exits:
            lines.append(f"SELL: {shares} shares — {label}")
        
        if len(lines) <= 1 and not is_first_time:
            return
        
        message = "\n".join(lines)
        for notifier in self.notifiers:
            if not notifier.enabled:
                continue
            try:
                notifier.send(message)
                logger.info("Unified notification sent for lot %s", lot_id)
            except Exception as exc:
                logger.error("Failed to send unified notification via %s: %s", notifier.name, exc)

    def _get_all_applicable_stops(
        self,
        entry_price: float,
        current_close: float,
        state: Dict[str, Any],
    ) -> List[Tuple[str, float, int]]:
        """Get all applicable stops where current price >= trigger price."""
        applicable_stops = []
        current_multiple = current_close / entry_price
        
        if state.get("initial_stop_price") is not None:
            applicable_stops.append(("Early Failure", state["initial_stop_price"], state["shares_original"]))
        
        symbol = state["symbol"]
        atr_current = self._compute_atr_entry(symbol) or state.get("atr_entry")
        if atr_current is None:
            return applicable_stops
        
        if current_multiple >= 1.5:
            stop1_price = state.get("stop1_price") or (entry_price + atr_current)
            exit_shares = max(1, int(round(state["shares_original"] * 0.25)))
            applicable_stops.append(("Stop_1", stop1_price, exit_shares))
        
        milestones = [
            (2.0, "stop2_price", 0.20, "Stop_2"),
            (3.0, "stop3_price", 0.10, "Stop_3"),
            (4.0, "stop4_price", 0.10, "Stop_4"),
            (6.0, "stop5_price", 0.10, "Stop_5"),
        ]
        
        for multiple, stop_key, exit_pct, stop_name in milestones:
            if current_multiple >= multiple:
                stop_price = state.get(stop_key) or (multiple * entry_price - 2.0 * atr_current)
                exit_shares = max(1, int(round(state["shares_original"] * exit_pct)))
                applicable_stops.append((stop_name, stop_price, exit_shares))
        
        return applicable_stops

