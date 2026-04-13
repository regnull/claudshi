---
name: bet
description: Place a trade on a political prediction market. Validates risk limits, requires prior analysis, and waits for user confirmation before executing.
disable-model-invocation: true
argument-hint: "<ticker> <side> <amount> [price]"
allowed-tools: Read Write Bash mcp__kalshi-mcp__get_market mcp__kalshi-mcp__get_market_orderbook mcp__kalshi-mcp__get_positions mcp__kalshi-mcp__get_balance mcp__kalshi-mcp__create_order mcp__kalshi-mcp__get_fills mcp__kalshi-mcp__get_orders
---

# /bet — Place a Trade

## Usage

```
/bet <ticker> <side> <amount> [price]
```

- `ticker`: Market ticker (e.g., `KXUSAIRANAGREEMENT-27`)
- `side`: `YES` or `NO`
- `amount`: Amount to risk in USD (e.g., `25`)
- `price`: Optional limit price in cents (1-99). If omitted, uses a market order.

Examples:
```
/bet KXUSAIRANAGREEMENT-27 YES 25
/bet KXUSAIRANAGREEMENT-27 NO 10 35
```

## Instructions

The user's arguments: $ARGUMENTS

When the user invokes `/bet`, follow **every** step below in order. Do not skip steps.

---

### Step 1: Parse and Validate Inputs

Parse the arguments: `<ticker> <side> <amount> [price]`

1. **Ticker**: Required. Must be a non-empty string.
2. **Side**: Required. Must be `YES` or `NO` (case-insensitive). Normalize to uppercase.
3. **Amount**: Required. Must be a positive number (USD). Convert to cents internally: `amount_cents = int(amount * 100)`.
4. **Price**: Optional. If provided, must be an integer between 1 and 99 (cents). This is the limit price. If omitted, this is a market order.

If any input is invalid or missing, show usage help and stop.

---

### Step 2: Load Existing Analysis

Check that an analysis exists for this market. Run:

```python
import sys; sys.path.insert(0, "lib")
from memory import read_yaml, get_market_dir
from pathlib import Path
import glob as glob_mod

# Find the event slug for this ticker by scanning the events directory
ticker = "<TICKER>"
claudshi_root = Path(".claudshi")
event_slug = None
market_dir = None

if claudshi_root.exists() and (claudshi_root / "events").exists():
    for event_dir in (claudshi_root / "events").iterdir():
        if event_dir.is_dir():
            candidate = event_dir / "markets" / ticker
            if candidate.exists():
                event_slug = event_dir.name
                market_dir = candidate
                break

if event_slug is None:
    # ERROR: No analysis found
    pass
```

If no analysis exists for this ticker:
- Display an error: "No analysis found for `<ticker>`. Run `/analyze <ticker>` first to generate a probability estimate before placing a bet."
- **Stop here.** Do not proceed.

If analysis exists, load the probability estimate:
```python
probability_data = read_yaml(market_dir / "probability.yaml")
```

If `probability.yaml` is empty or missing `current_estimate`, tell the user to run `/analyze` first and stop.

Extract:
- `claude_probability`: from `probability_data["current_estimate"]["yes_probability"]`
- `confidence`: from `probability_data["current_estimate"]["confidence"]`

---

### Step 3: Fetch Current Market Data

Call these MCP tools in parallel:

1. **`get_market`** with the ticker — gets current market details (last price, expiration, status, etc.).
2. **`get_market_orderbook`** with the ticker — gets current bid/ask depth.
3. **`get_balance`** — gets current account balance.
4. **`get_positions`** — gets all current open positions.

From the market data, extract:
- `market_probability`: `last_price / 100`
- `expiration_time`: the market's expiration timestamp
- `market_status`: must be `open` or `active`

If the market is not open/active, report the error and stop.

---

### Step 4: Run Risk Checks

Perform all risk checks. Use the logic from `lib/risk.py`:

```python
from memory import load_config, load_portfolio_summary
from risk import (
    load_risk_config, check_bet, check_market_expiry,
    check_concentration, calculate_edge, calculate_position_size,
    format_risk_report
)

config = load_risk_config()
portfolio_summary = load_portfolio_summary()

# 1. Check market expiry (must be > 1 hour away)
expiry_ok, expiry_reason = check_market_expiry("<expiration_time>")

# 2. Check bet size against limits
bet_ok, bet_reasons = check_bet(<amount_usd>, ticker, portfolio_summary, config)

# 3. Check concentration
conc_ok, conc_reason = check_concentration(event_slug, <amount_usd>, portfolio_summary, config)

# 4. Calculate edge
edge = calculate_edge(claude_probability, market_probability)
edge_ok = abs(edge) >= config.get("min_edge_pct", 10)

# Collect all checks
checks = []
checks.append(("Market expiry", expiry_ok, expiry_reason))
for reason in bet_reasons:
    checks.append(("Bet limit", False, reason))
if not bet_reasons:
    checks.append(("Bet limits", bet_ok, "All bet limits passed"))
checks.append(("Concentration", conc_ok, conc_reason))
checks.append(("Edge threshold", edge_ok, f"Edge: {edge:+.1f}% (min: {config.get('min_edge_pct', 10)}%)"))
```

If **any critical check fails** (expiry, bet limits), display the risk report and stop. Do NOT proceed with the trade.

If the edge check fails (edge below threshold), display a **warning** but allow the user to proceed if they explicitly confirm (they may have reasons beyond the model's estimate).

If the concentration check fails, display a **warning** (not a hard block).

---

### Step 5: Present Trade Confirmation

Build and display a trade confirmation prompt. Use the formatting helper logic:

```python
from formatting import format_trade_confirmation, usd_cents_to_display, format_probability, format_edge_display
```

Display a confirmation that includes:

```
## Trade Confirmation

### Market
- **Title**: <market title>
- **Ticker**: <ticker>
- **Expiration**: <expiration time>
- **Current Price**: <last_price> cents (YES)

### Our Analysis
- **Claude Probability**: <XX.X%>
- **Market Probability**: <YY.Y%>
- **Edge**: <+/-ZZ.Z%> (<YES/NO> side)
- **Confidence**: <low/medium/high>

### Order Details
- **Side**: <YES/NO>
- **Type**: <Market / Limit @ XX cents>
- **Amount**: $<XX.XX>
- **Quantity**: <calculated contracts> contracts
- **Estimated Cost**: $<XX.XX>

### Risk Checks
<risk report — each check with pass/fail/warn status>

### Portfolio Impact
- **Current Exposure**: $<XX.XX>
- **After This Trade**: $<XX.XX>
- **Event Concentration**: <XX%>

---
**Do you want to proceed with this trade? (yes/no)**
```

Calculate quantity (number of contracts):
- For YES side: `quantity = amount_cents / price_cents` (rounded down)
- For NO side: `quantity = amount_cents / (100 - price_cents)` (rounded down)
- If no price specified (market order), use the best ask (for YES) or best bid complement (for NO) from the orderbook.

**CRITICAL: Wait for the user to explicitly type "yes" or confirm.** Do NOT auto-execute. Do NOT proceed without confirmation.

---

### Step 6: Execute the Trade

Only after the user confirms, place the order:

```python
# Use create_order MCP tool with:
# - ticker: <ticker>
# - side: "yes" or "no"
# - action: "buy"
# - type: "market" or "limit"
# - count: <quantity>  (number of contracts)
# - yes_price or no_price: <price in cents> (for limit orders)
```

Call **`create_order`** with the appropriate parameters:
- `ticker`: the market ticker
- `action`: `buy`
- `side`: `yes` or `no` (lowercase)
- `type`: `market` if no price given, `limit` if price specified
- `count`: number of contracts (quantity calculated in Step 5)
- For limit orders on YES side: set `yes_price` to the limit price in cents
- For limit orders on NO side: set `no_price` to the limit price in cents

If the order fails, display the error and stop.

---

### Step 7: Confirm Execution

After placing the order, poll for fills:

1. Call **`get_orders`** to check the order status.
2. If the order is a limit order and status is `resting`, inform the user it's pending: "Limit order placed and resting on the book. It will fill when the price reaches your limit."
3. If the order is filled (or for market orders), call **`get_fills`** with the ticker to confirm execution details.

Extract from the fill/order:
- `order_id`
- `fill_price` (average price)
- `fill_quantity`
- `fill_status` (filled, partial, resting)

---

### Step 8: Update Memory Files

After successful execution, update all memory files:

```python
import sys; sys.path.insert(0, "lib")
from memory import (
    read_yaml, write_yaml, append_yaml_list,
    get_market_dir, load_portfolio_summary, save_portfolio_summary, ensure_dirs
)
from datetime import datetime, timezone

now_iso = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
event_slug = "<EVENT_SLUG>"
ticker = "<TICKER>"
market_dir = get_market_dir(event_slug, ticker)
ensure_dirs()
```

#### 8.1 Update Trades Log

Append to `.claudshi/events/<slug>/markets/<ticker>/trades.yaml`:

```python
trade_entry = {
    "timestamp": now_iso,
    "order_id": "<order_id>",
    "side": "<YES/NO>",
    "action": "buy",
    "quantity": <fill_quantity>,
    "price_cents": <fill_price>,
    "cost_cents": <fill_quantity * fill_price>,  # for YES; (100 - fill_price) * qty for NO
    "order_type": "<market/limit>",
    "status": "<filled/resting/partial>",
}
append_yaml_list(market_dir / "trades.yaml", "trades", trade_entry)

# Ensure ticker is set at top level
trades_data = read_yaml(market_dir / "trades.yaml")
trades_data["ticker"] = ticker
write_yaml(market_dir / "trades.yaml", trades_data)
```

#### 8.2 Update Position

Write or update `.claudshi/events/<slug>/markets/<ticker>/position.yaml`:

```python
existing_position = read_yaml(market_dir / "position.yaml")

if existing_position and existing_position.get("quantity", 0) > 0:
    # Update existing position — recalculate average price
    old_qty = existing_position["quantity"]
    old_avg = existing_position["avg_price_cents"]
    new_qty = old_qty + <fill_quantity>
    new_avg = ((old_qty * old_avg) + (<fill_quantity> * <fill_price>)) / new_qty
    position_data = {
        "ticker": ticker,
        "event_slug": event_slug,
        "side": "<YES/NO>",
        "quantity": new_qty,
        "avg_price_cents": round(new_avg),
        "total_cost_cents": round(new_qty * new_avg),
        "opened_at": existing_position.get("opened_at", now_iso),
        "updated_at": now_iso,
    }
else:
    # New position
    position_data = {
        "ticker": ticker,
        "event_slug": event_slug,
        "side": "<YES/NO>",
        "quantity": <fill_quantity>,
        "avg_price_cents": <fill_price>,
        "total_cost_cents": <fill_quantity> * <fill_price>,
        "opened_at": now_iso,
        "updated_at": now_iso,
    }

write_yaml(market_dir / "position.yaml", position_data)
```

#### 8.3 Log the Action

Append to `.claudshi/events/<slug>/markets/<ticker>/actions_log.yaml`:

```python
action = {
    "timestamp": now_iso,
    "type": "bet",
    "side": "<YES/NO>",
    "quantity": <fill_quantity>,
    "price": <fill_price>,
    "order_type": "<market/limit>",
    "order_id": "<order_id>",
    "status": "<filled/resting/partial>",
}
append_yaml_list(market_dir / "actions_log.yaml", "actions", action)

# Ensure ticker at top level
log_data = read_yaml(market_dir / "actions_log.yaml")
log_data["ticker"] = ticker
write_yaml(market_dir / "actions_log.yaml", log_data)
```

#### 8.4 Update Portfolio Summary

Update `.claudshi/portfolio/summary.yaml`:

```python
summary = load_portfolio_summary()
positions = summary.get("positions", {})
positions[ticker] = {
    "side": "<YES/NO>",
    "quantity": position_data["quantity"],
    "avg_price_cents": position_data["avg_price_cents"],
    "total_cost_cents": position_data["total_cost_cents"],
    "event_slug": event_slug,
}
summary["positions"] = positions
summary["total_invested_cents"] = sum(
    p["total_cost_cents"] for p in positions.values()
)
summary["updated_at"] = now_iso
save_portfolio_summary(summary)
```

---

### Step 9: Present Execution Summary

After all memory files are updated, display:

```
## Trade Executed

- **Ticker**: <ticker>
- **Side**: <YES/NO>
- **Quantity**: <N> contracts
- **Price**: <XX> cents
- **Cost**: $<XX.XX>
- **Order ID**: <order_id>
- **Status**: <filled/resting>

### Updated Position
- **Total Quantity**: <N> contracts
- **Average Price**: <XX> cents
- **Total Cost**: $<XX.XX>

### Next Steps
- Run `/portfolio` to see your full portfolio
- Run `/monitor` to track this market
```

---

## Important Notes

- **NEVER auto-execute trades.** Always wait for explicit user confirmation before calling `create_order`.
- **Require prior analysis.** If no `probability.yaml` exists for the market, block the trade and tell the user to run `/analyze` first.
- **Enforce all risk rules.** Hard-block on expiry and bet limit violations. Warn on concentration and edge threshold.
- **Log everything.** Every trade must be recorded in trades.yaml, position.yaml, actions_log.yaml, and portfolio summary.
- **Handle errors gracefully.** If the order fails, display the error clearly and do not update memory files.
- **Idempotent memory updates.** If re-running after a partial failure, check existing state before writing.
