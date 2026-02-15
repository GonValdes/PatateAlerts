# Exit Rules

This document defines **exit and profit-protection rules** for individual high-growth, high-volatility stocks.

Goals: 
- **minimise capital losses on individual stocks**, especially from bad timing, slow downtrends, and repeated re-entries into structurally weak names.
- **protect capital and accumulated gains while allowing unlimited upside**.

Design principles:
- No selling into strength
- No profit targets
- Exits occur **only if price fails to hold defined stop levels**
- Stops only tighten over time; they are never loosened

Non-goals:
- No portfolio-level logic
- No position sizing rules
- No discretionary overrides

All exit conditions are **evaluated once per trading day at a fixed, configurable time**, using **daily closes**.

---

## Fixed Definitions (Set at Entry)

- `EntryPrice` = executed entry price
- `ATR_entry` = ATR(14) calculated on daily data at entry

These values are **never recalculated**.

---

## Layer - Price-Based Early Failure Stop

Purpose: provide constant downside protection against adverse price movement.

**Rule:**

- At entry, calculate a fixed stop level:

```
Stop Price = Entry Price − (2 × ATR(14))
```

- This stop level is **set once at entry and never moved**.
- Exit **100% immediately** if:

```
Daily close < Stop Price
```


---

## Layer — Initial Profit Lock (+50%)

### Activation Condition

```
Daily Close ≥ 1.5 × EntryPrice
```

### Stop Added (Permanent)

```
Stop_1 = EntryPrice + 1 × ATR_entry
```

### Exit on Failure

If:
```
Daily Close < Stop_1
```

Then:
```
Exit 25% of the original position
```

---

## Layer — Progressive Profit Protection (Milestone-Based)

Purpose:
- Gradually reduce downside exposure on extreme winners
- Preserve a meaningful long-term runner

### Gain Milestones

Milestones are evaluated **once**, on first touch.

```
M1 = 2.0 × EntryPrice   (+100%)
M2 = 3.0 × EntryPrice   (+200%)
M3 = 4.0 × EntryPrice   (+300%)
M4 = 6.0 × EntryPrice   (+500%)
```

---

### Stop Definition per Milestone

When milestone `Mi` is reached for the first time, define:

```
Stop_i = Mi − 2 × ATR_entry
```

Each stop:
- Is fixed at creation
- Is permanent
- Is never tightened or loosened

---

### Exit Size per Stop

All exit percentages refer to the **original position size**.

| Stop Triggered | % Exited |
|--------------|----------|
| Stop_2 (M1) | 20% |
| Stop_3 (M2) | 10% |
| Stop_4 (M3) | 10% |
| Stop_5 (M4) | 10% |


---

## Stop Resolution Logic

- All active stops coexist
- Stops are evaluated daily using **closing prices only**
- If multiple stops are breached on the same day:
  - Execute **all applicable exits**
- Each stop can trigger **only once**

At any time, the effective stop level is:

```
ActiveStop = max(all active Stop_i)
```

---

## Notification - Negative trends

Purpose: notify stocks enter a negative trend

**Rule:**

- If weekly close < 200 DMA → notification.
- If weekly close < 200 WMA → notification.


---


## Execution Notes

- Gaps below a stop exit at the first available price
- Intraday breaches are ignored
- After partial exits, remaining shares continue to be governed by higher stops only

---

## System Properties (Intentional)

- No trailing stops
- No volatility re-estimation
- No time-based profit exits
- No selling into strength

This exit system is designed to **cap losses early**, **lock gains progressively**, and **preserve asymmetric upside** on rare multi-bagger outcomes.

