# /cs_portfolio — View Current Portfolio and P&L

## Usage

```
/cs_portfolio
```

No arguments. Displays all open positions, per-position P&L, aggregate totals, and cash balance.

## Instructions

When the user invokes `/cs_portfolio`, follow **every** step below in order.

---

### Step 1: Fetch Account Data from Kalshi

Call these MCP tools in parallel:

1. **`get_balance`** — gets current account balance and portfolio value.
2. **`get_positions`** — gets all open positions on Kalshi.

---

### Step 2: Enrich Positions with Current Market Prices

For each open position returned by `get_positions`, call **`get_market`** with the position's ticker to fetch the current market price.

If there are many positions, batch the `get_market` calls in parallel for speed.

From each position + market response, extract:

- `ticker`: the market ticker
- `title`: the market title (from `get_market`)
- `side`: YES or NO
- `quantity`: number of contracts held
- `avg_price_cents`: average entry price (from the position's `market_price` or compute from cost / quantity)
- `current_price_cents`: current last trade price from `get_market` (for YES side, use `last_price`; for NO side, use `100 - last_price`)
- `cost_cents`: total cost basis = `quantity * avg_price_cents`
- `current_value_cents`: current value = `quantity * current_price_cents`
- `unrealized_pnl_cents`: unrealized P&L = `current_value_cents - cost_cents`

---

### Step 3: Calculate Portfolio Totals

Compute aggregate numbers:

- **Total Invested**: sum of all `cost_cents`
- **Total Current Value**: sum of all `current_value_cents`
- **Total Unrealized P&L**: sum of all `unrealized_pnl_cents`
- **Cash Available**: from `get_balance` response (the `balance` field, in cents)
- **Portfolio Value**: from `get_balance` response (the `portfolio_value` field, in cents)

For each position, calculate its **weight** in the portfolio:

```
weight_pct = (cost_cents / total_invested_cents) * 100
```

---

### Step 4: Display Portfolio Table

Present the data using the `format_portfolio_table` logic from `lib/formatting.py`. The output should look like:

```
## Portfolio

| Ticker | Side | Qty | Avg Price | Current | Cost | Value | P&L |
|--------|------|-----|-----------|---------|------|-------|-----|
| TICKER1 | YES | 50 | $0.25 | $0.32 | $12.50 | $16.00 | $3.50 |
| TICKER2 | NO | 30 | $0.40 | $0.35 | $12.00 | $10.50 | -$1.50 |
| **Total** | | | | | **$24.50** | **$26.50** | **$2.00** |

**Cash:** $975.50
**Portfolio Value:** $1,002.00
```

If there are no open positions, display:

```
## Portfolio

No open positions.

**Cash:** $<balance>
**Portfolio Value:** $<portfolio_value>
```

After the table, add a section with portfolio-level metrics:

```
### Portfolio Metrics
- **Total Unrealized P&L**: $X.XX (±X.X%)
- **Number of Positions**: N
- **Largest Position**: TICKER ($X.XX, XX% of portfolio)
- **Total Exposure**: $X.XX
```

---

### Step 5: Update Memory Files

After displaying the portfolio, update the memory system.

#### 5.1 Update Portfolio Summary

Write to `.claudshi/cs_portfolio/summary.yaml`:

```python
import sys; sys.path.insert(0, "lib")
from memory import save_portfolio_summary, ensure_dirs
from datetime import datetime, timezone

ensure_dirs()
now_iso = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

summary = {
    "updated_at": now_iso,
    "cash_cents": <balance_cents>,
    "portfolio_value_cents": <portfolio_value_cents>,
    "total_invested_cents": <total_invested>,
    "total_current_value_cents": <total_current_value>,
    "total_unrealized_pnl_cents": <total_pnl>,
    "num_positions": <count>,
    "positions": {
        "<ticker>": {
            "side": "<YES/NO>",
            "quantity": <qty>,
            "avg_price_cents": <avg>,
            "current_price_cents": <current>,
            "cost_cents": <cost>,
            "current_value_cents": <value>,
            "unrealized_pnl_cents": <pnl>,
            "event_slug": "<slug>",
        },
        # ... for each position
    },
}
save_portfolio_summary(summary)
```

#### 5.2 Append Balance Log

Append a snapshot to `.claudshi/cs_portfolio/balance_log.csv`:

```python
from memory import append_balance_log

append_balance_log(now_iso, <balance_cents>, <portfolio_value_cents>)
```

---

### Step 6: Cross-Reference Local Memory

After updating the portfolio from Kalshi data, check if there are positions tracked in the local `.claudshi/events/` memory that are **not** present in Kalshi's `get_positions` response. These may be:

- Positions that settled (resolved)
- Positions that were closed outside of Claudshi

If any local positions are missing from Kalshi:

```
### Stale Local Positions

The following positions are tracked locally but not found on Kalshi. They may have settled or been closed externally:

| Ticker | Side | Qty | Status |
|--------|------|-----|--------|
| TICKER | YES | 50 | Not found on Kalshi |

Run `/cs_monitor` to update these, or manually remove them from `.claudshi/`.
```

To find local positions, scan `.claudshi/events/*/markets/*/position.yaml` for files where `quantity > 0`.

---

## Output Format

The full output should follow this structure:

```
## Portfolio

<position table or "No open positions.">

**Cash:** $X.XX
**Portfolio Value:** $X.XX

### Portfolio Metrics
- **Total Unrealized P&L**: $X.XX (±X.X%)
- **Number of Positions**: N
- **Largest Position**: TICKER ($X.XX, XX% of portfolio)
- **Total Exposure**: $X.XX

### Stale Local Positions (if any)
<table of stale positions>

---
*Portfolio updated at YYYY-MM-DD HH:MM UTC*
```

## Important Notes

- **Always fetch live data.** Do not rely solely on local memory — Kalshi is the source of truth for balances and positions.
- **Handle empty portfolios gracefully.** If the user has no positions, still show the cash balance and portfolio value.
- **All monetary values in memory are in USD cents (integers).** Display values use `$X.XX` format.
- **Update memory on every invocation.** The portfolio snapshot is useful for tracking P&L over time via `balance_log.csv`.
- **Identify stale data.** Cross-referencing local and remote state helps keep the memory system accurate.
