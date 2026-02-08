# Entry Rules

This document defines **daily-evaluated entry algorithms** for high-growth, high-volatility stocks.

Goal: **enter positions with structural strength and momentum** while relying on separate protection rules to cap downside.

All entry signals are **evaluated once per trading day at a fixed, configurable time**. If conditions are met at evaluation time, an entry signal is generated immediately.

---

## Indicators

- 200 DMA calculated on daily data (used by some entry types and tracking)
- 200 WMA: 1000 DMA on daily data
- ATR(14) calculated on daily data (used by protection rules after entry)

---

## Entry Type 1 — All-Time High (ATH) Breakout

**Purpose:** capture momentum ignition during price discovery.

### Preconditions

- Stock has ≥ **252 trading days** of price history

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

- None (beyond having enough history for the signal)

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

A stock is tracked if either of these conditions are met:
- **Daily Close ≤ 200 DMA × 1.05** (within 5% or below 200 DMA)
- **Daily Close ≤ 200 Weekly Moving Average × 1.10** (within 10% or below 200 WMA)

### Daily Report

For each tracked stock, report:
- What triggered the report, 200 DMA or 200 WMA
- **Drop from all-time high:** Percentage decline from the highest close within the last 3 years
- **Position relative to 200 DMA:** Percentage above or below the 200-day moving average
- **Position relative to 200 WMA:** Percentage above or below the 200-week moving average

### Notes
- Reports are generated daily for all stocks meeting the conditions
- For the tracking report, the all-time high is the highest close within the last 3 years
