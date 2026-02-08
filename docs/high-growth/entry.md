# Entry Rules

This document defines **daily-evaluated entry algorithms** for high-growth, high-volatility stocks.

Goal: **enter positions with structural strength and momentum** while relying on separate protection rules to cap downside.

Non-goals:

- No exits or stop logic (defined elsewhere)
- No portfolio or sizing rules
- No prediction or discretionary confirmation

All entry signals are **evaluated once per trading day at a fixed, configurable time**. If conditions are met at evaluation time, an entry signal is generated immediately.

---

## Global Entry Conditions

The following condition applies to **all entry types**:

- **Daily Close ≥ 200-day moving average (200 DMA)**

If this condition is not met, **no entry is allowed**, regardless of other signals.

Indicators:

- 200 DMA calculated on daily data
- ATR(14) calculated on daily data (used by protection rules after entry)

---

## Entry Type 1 — All-Time High (ATH) Breakout

**Purpose:** capture momentum ignition during price discovery.

### Preconditions

- Stock has ≥ **252 trading days** of price history
- Global entry condition satisfied

### Signal (evaluated daily)

1. Compute:
   - `ATH = maximum daily close over all prior trading days`
2. Generate entry signal if:

```
Daily Close > ATH
```

### Notes

- Signal triggers on the **first day** a new ATH is achieved
- Repeated ATH closes should not generate duplicate signals

---

## Entry Type 3 — High Tight Flag / Volatility Contraction

**Purpose:** continuation entry after a strong advance and controlled consolidation.

### Preconditions

- Global entry condition satisfied

### Signal (evaluated daily)

1. Detect prior impulse move:

   - Price increase ≥ **+80%**
   - Occurred within the last **120 trading days**

2. Detect consolidation phase:

   - Duration ≥ **15 trading days**
   - All daily closes ≥ 200 DMA
   - Maximum drawdown from impulse high ≤ **35%**

3. Define:

   - `Consolidation High = maximum daily close during consolidation`

4. Generate entry signal if:

```
Daily Close > Consolidation High
```

### Notes

- Volatility contraction is inferred from price containment only
- No volume or indicator filters are applied

---

## Entry Type 4 — First Pullback to 200 DMA After Breakout

**Purpose:** re-enter strong trends after deep but controlled corrections.

### Preconditions

- Global entry condition satisfied
- A valid breakout occurred previously:
  - All-time high breakout, or
  - Range breakout from a base lasting ≥ **6 months**

### Signal (evaluated daily)

1. After the breakout, price must have:

   - Traded ≥ **+30% above the breakout level**

2. Pullback phase:

   - Price declines toward the 200 DMA
   - **No daily close below the 200 DMA** during the pullback

3. Generate entry signal when:

```
Daily Close ≥ 200 DMA
AND
Daily Close > Previous Daily Close
```

### Hard Constraint

- **Only the first qualifying pullback is tradable**
- Subsequent pullbacks are ignored

---

## Evaluation Model Summary

- Entry conditions are checked **once per trading day** at a fixed time
- Signals are **event-based**, not predictive
- When a signal triggers:
  - Entry is executed according to the system’s execution model
  - Protection rules are activated immediately after entry

These rules prioritise **structural strength and momentum** while delegating risk control entirely to the protection system.

---

## Tracking

**Purpose:** Monitor stocks in the watchlist that are performing poorly relative to their all-time highs and the 200 DMA.

### Conditions

A stock is tracked if:
- **Daily Close ≤ 200 DMA × 1.05** (within 5% or below 200 SMA)

### Daily Report

For each tracked stock, report:
- **Drop from all-time high:** Percentage decline from the highest close ever recorded
- **Position relative to 200 DMA:** Percentage above or below the 200-day moving average

### Notes

- Tracking is informational only; no entry signals are generated
- Reports are generated daily for all stocks meeting the conditions
- All-time high is computed from all available historical data
