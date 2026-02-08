"""High-growth entry engine implementing docs/high-growth/entry.md for watchlist symbols.

Detects entry signals and tracks stocks performing poorly relative to 200 DMA.
Sends alerts but does not place orders.
"""

import logging
from datetime import date
from typing import Dict, Any, List, Optional

from storage.db import Database
from storage.models import PriceHistory, HighGrowthEntryState
from data_provider import DataProvider

logger = logging.getLogger(__name__)


class HighGrowthEntryEngine:
    """Applies high-growth entry rules per symbol."""

    SMA200_PERIOD = 200
    DMA1000_PERIOD = 1000  # 200 WMA = 200×5 days = 1000 DMA

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
        self.entry_state = HighGrowthEntryState(db)

    def process_symbol(self, symbol: str) -> None:
        """Process a single symbol according to high-growth entry rules."""
        logger.info("Processing high-growth entries for %s", symbol)

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

        current_close = float(latest["close"])
        current_date = latest["date"]

        self._ensure_historical_cache(symbol)
        hist = self.price_history.get_historical_prices(symbol, days=self.DMA1000_PERIOD + 100)
        if len(hist) < self.SMA200_PERIOD:
            logger.info("Not enough history for 200DMA / entry rules on %s (have %d days)", symbol, len(hist))
            return

        closes = [float(row["close"]) for row in hist]
        dates = [row["date"] for row in hist]
        dma200_series = self._compute_sma_series(closes, self.SMA200_PERIOD)
        latest_dma200 = dma200_series[-1]

        if latest_dma200 is not None:
            wma200_as_dma1000 = None
            if len(hist) >= self.DMA1000_PERIOD:
                dma1000_series = self._compute_sma_series(closes, self.DMA1000_PERIOD)
                wma200_as_dma1000 = dma1000_series[-1]
            tracking_msg = self._check_tracking(
                symbol, hist, closes, latest_dma200, current_close, wma200_as_dma1000
            )
            if tracking_msg:
                self._send_tracking_alert(symbol, tracking_msg)

        state = self.entry_state.get_state(symbol) or self.entry_state.create_default_state(symbol)
        messages: List[str] = []

        msg1 = self._check_entry_type1(symbol, hist, closes, dates, state)
        if msg1:
            messages.append(msg1)

        msg3 = self._check_entry_type3(symbol, hist, closes, dates, dma200_series, state)
        if msg3:
            messages.append(msg3)

        msg4 = self._check_entry_type4(symbol, hist, closes, dates, dma200_series, state)
        if msg4:
            messages.append(msg4)

        if messages:
            self._send_entry_alerts(symbol, current_close, latest_dma200, messages)

        self.entry_state.upsert_state(state)

    def _ensure_historical_cache(self, symbol: str) -> None:
        """Ensure we have enough history cached for 200DMA, 1000 DMA (200 WMA), and entry rules."""
        min_days = self.DMA1000_PERIOD + 100
        hist = self.price_history.get_historical_prices(symbol, days=min_days)
        if len(hist) >= min_days:
            return

        logger.info("Fetching additional historical data for %s", symbol)
        for row in self.data_provider.get_historical_prices(symbol, days=min_days):
            self.price_history.insert_or_update(
                symbol=symbol,
                date=row["date"],
                open=row["open"],
                high=row["high"],
                low=row["low"],
                close=row["close"],
                volume=row["volume"],
            )

    @staticmethod
    def _compute_sma_series(values: List[float], period: int) -> List[Optional[float]]:
        """Compute a simple moving average series for the given period."""
        sma: List[Optional[float]] = [None] * len(values)
        if len(values) < period:
            return sma

        running_sum = sum(values[:period])
        sma[period - 1] = running_sum / period

        for i in range(period, len(values)):
            running_sum += values[i] - values[i - period]
            sma[i] = running_sum / period

        return sma

    def _check_entry_type1(
        self,
        symbol: str,
        hist: List[Dict[str, Any]],
        closes: List[float],
        dates: List[date],
        state: Dict[str, Any],
    ) -> Optional[str]:
        """Entry Type 1 — All-Time High (ATH) Breakout. Reports every day a new ATH is captured."""
        if len(closes) < 252:
            return None

        current_close = closes[-1]
        ath_prior = max(closes[:-1])

        if current_close <= ath_prior:
            return None

        last_ath_close = state.get("last_ath_close")
        state["last_ath_close"] = max(float(last_ath_close), current_close) if last_ath_close else current_close
        state["last_ath_signal_date"] = dates[-1]
        state["breakout_level"] = current_close
        state["breakout_date"] = dates[-1]

        return (
            "Entry Type 1 — All-Time High (ATH) Breakout\n"
            f"- Symbol: {symbol}\n"
            f"- Latest close: {current_close:.2f}\n"
            f"- Prior ATH close: {ath_prior:.2f}"
        )

    def _check_entry_type3(
        self,
        symbol: str,
        hist: List[Dict[str, Any]],
        closes: List[float],
        dates: List[date],
        dma200_series: List[Optional[float]],
        state: Dict[str, Any],
    ) -> Optional[str]:
        """Entry Type 3 — High Tight Flag / Volatility Contraction. One-shot per symbol."""
        if state.get("type3_signal_date") or len(closes) < 150:
            return None

        lookback = min(120, len(closes) - 1)
        start_idx = len(closes) - 1 - lookback

        min_price = closes[start_idx]
        impulse_idx = None
        for i in range(start_idx + 1, len(closes) - 15):
            if closes[i] < min_price:
                min_price = closes[i]
                continue
            if (closes[i] - min_price) / min_price >= 0.8:
                impulse_idx = i
                break

        if impulse_idx is None:
            return None

        impulse_high = closes[impulse_idx]
        cons_start = impulse_idx + 1
        cons_end = len(closes) - 2
        if cons_end - cons_start + 1 < 15:
            return None

        cons_closes = closes[cons_start : cons_end + 1]
        cons_dma200 = dma200_series[cons_start : cons_end + 1]

        for c, ma in zip(cons_closes, cons_dma200):
            if ma is not None and c < ma:
                return None

        drawdown = (impulse_high - min(cons_closes)) / impulse_high
        if drawdown > 0.35 + 1e-8:
            return None

        cons_high = max(cons_closes)
        current_close = closes[-1]
        if current_close <= cons_high:
            return None

        state["type3_signal_date"] = dates[-1]
        return (
            "Entry Type 3 — High Tight Flag / Volatility Contraction\n"
            f"- Symbol: {symbol}\n"
            f"- Impulse high: {impulse_high:.2f}\n"
            f"- Consolidation high: {cons_high:.2f}\n"
            f"- Latest close (breakout above consolidation): {current_close:.2f}"
        )

    def _check_entry_type4(
        self,
        symbol: str,
        hist: List[Dict[str, Any]],
        closes: List[float],
        dates: List[date],
        dma200_series: List[Optional[float]],
        state: Dict[str, Any],
    ) -> Optional[str]:
        """Entry Type 4 — First Pullback to 200 DMA After Breakout. One-shot per symbol."""
        if state.get("type4_signal_date"):
            return None

        breakout_level = state.get("breakout_level")
        breakout_date = state.get("breakout_date")
        if breakout_level is None or breakout_date is None:
            return None

        try:
            b_idx = next(i for i, d in enumerate(dates) if d == breakout_date)
        except StopIteration:
            return None

        if max(closes[b_idx:]) < 1.3 * float(breakout_level):
            return None

        for i in range(b_idx + 1, len(closes)):
            ma = dma200_series[i]
            if ma is not None and closes[i] < ma - 1e-8:
                return None

        current_close = closes[-1]
        prev_close = closes[-2]
        current_dma200 = dma200_series[-1]
        if current_dma200 is None or current_close < current_dma200 or current_close <= prev_close + 1e-8:
            return None

        state["type4_signal_date"] = dates[-1]
        return (
            "Entry Type 4 — First Pullback to 200 DMA After Breakout\n"
            f"- Symbol: {symbol}\n"
            f"- Breakout level (prior ATH breakout): {float(breakout_level):.2f}\n"
            f"- Latest close (rebound near 200DMA): {current_close:.2f}\n"
            f"- 200DMA (today): {current_dma200:.2f}"
        )

    def _check_tracking(
        self,
        symbol: str,
        hist: List[Dict[str, Any]],
        closes: List[float],
        dma200: Optional[float],
        current_close: float,
        wma200: Optional[float] = None,
    ) -> Optional[str]:
        """Check if stock should be tracked (within 5% or below 200 DMA, or within 10% or below 200 WMA)."""
        triggered_by_dma = dma200 is not None and current_close <= dma200 * 1.05
        triggered_by_wma = wma200 is not None and current_close <= wma200 * 1.10
        if not triggered_by_dma and not triggered_by_wma:
            return None

        triggers = []
        if triggered_by_dma:
            triggers.append("200 DMA")
        if triggered_by_wma:
            triggers.append("200 WMA")
        trigger_text = " and ".join(triggers)

        ath = max(closes)
        drop_from_ath = ((ath - current_close) / ath) * 100
        pct_from_dma = ((current_close - dma200) / dma200) * 100 if dma200 else None
        pct_from_wma = ((current_close - wma200) / wma200) * 100 if wma200 else None

        lines = [
            f"Symbol: {symbol}",
            f"Triggered by: {trigger_text}",
            f"Drop from all-time high: {drop_from_ath:.2f}%",
            f"Position relative to 200 DMA: {pct_from_dma:+.2f}%" if pct_from_dma is not None else "Position relative to 200 DMA: N/A",
            f"Position relative to 200 WMA: {pct_from_wma:+.2f}%" if pct_from_wma is not None else "Position relative to 200 WMA: N/A",
        ]
        return "\n".join(lines)

    def _send_tracking_alert(self, symbol: str, message: str) -> None:
        """Send tracking alert for stocks performing poorly (200 DMA or 200 WMA)."""
        full_message = "Tracking Alert — Stock Near/Below 200 DMA or 200 WMA\n" + message
        for notifier in self.notifiers:
            if not notifier.enabled:
                continue
            try:
                notifier.send(full_message)
            except Exception as exc:
                logger.error("Failed to send tracking alert via %s: %s", notifier.name, exc)

    def _send_entry_alerts(self, symbol: str, current_close: float, dma200: float, messages: List[str]) -> None:
        """Send aggregated entry alerts via all enabled notifiers."""
        header = "\n".join([
            "High-Growth Entry Alert",
            f"Symbol: {symbol}",
            f"Latest close: {current_close:.2f}",
            "",
        ])
        message = header + "\n\n".join(messages)
        for notifier in self.notifiers:
            if not notifier.enabled:
                continue
            try:
                notifier.send(message)
            except Exception as exc:
                logger.error("Failed to send high-growth entry alert via %s: %s", notifier.name, exc)

