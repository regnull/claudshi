---
name: cs_exit
description: Close or reduce a position on a political prediction market. Calculates realized P&L, requires user confirmation, and updates all memory files.
disable-model-invocation: true
argument-hint: "<ticker> [amount]"
allowed-tools: Read Write Bash Glob Grep mcp__kalshi-mcp__get_market mcp__kalshi-mcp__get_market_orderbook mcp__kalshi-mcp__get_balance mcp__kalshi-mcp__get_positions mcp__kalshi-mcp__create_order mcp__kalshi-mcp__get_fills mcp__kalshi-mcp__get_orders
---

# /cs_exit — Close or Reduce a Position

## Usage

```
/cs_exit <ticker> [amount]
```

- `ticker`: Market ticker (e.g., `KXUSAIRANAGREEMENT-27`)
- `amount`: Optional. USD amount to exit. If omitted, closes the entire position.

Examples:
```
/cs_exit KXUSAIRANAGREEMENT-27
/cs_exit KXUSAIRANAGREEMENT-27 10
```

## Instructions

The user's arguments: $ARGUMENTS

When the user invokes `/cs_exit`, follow **every** step below in order. Do not skip steps.

---

### Step 1: Parse and Validate Inputs

Parse the arguments: `<ticker> [amount]`

1. **Ticker**: Required. Must be a non-empty string.
2. **Amount**: Optional. If provided, must be a positive number (USD). This is the dollar amount of the position to exit. If omitted, close the entire position.

If the ticker is missing, show usage help and stop.

---

### Step 2: Load Current Position

Find the position in the `.claudshi/` memory tree. Run:

```python
import sys; sys.path.insert(0, "lib")
from memory import read_yaml
from pathlib import Path

ticker = "<TICKER>"
claudshi_root = Path(".claudshi")
event_slug = None
market_dir = None
position_data = None

if claudshi_root.exists() and (claudshi_root / "events").exists():
    for event_dir in (claudshi_root / "events").iterdir():
        if event_dir.is_dir():
            candidate = event_dir / "markets" / ticker
            if candidate.exists():
                pos = read_yaml(candidate / "position.yaml")
                if pos and pos.get("quantity", 0) > 0:
                    event_slug = event_dir.name
                    market_dir = candidate
                    position_data = pos
                    break

if position_data is None:
    # ERROR: No open position found
    pass
```

If no position file exists, or the position quantity is 0:
- Display an error: "No open position found for `<ticker>`. Nothing to exit."
- **Stop here.**

If a position exists, extract:
- `side`: YES or NO
- `quantity`: number of contracts held
- `avg_price_cents`: average entry price
- `total_cost_cents`: total cost basis
- `event_slug`: the parent event slug

---

### Step 3: Fetch Current Market Data

Call these MCP tools in parallel:

1. **`get_market`** with the ticker — current market details (last price, expiration, status).
2. **`get_market_orderbook`** with the ticker — current bid/ask depth.
3. **`get_balance`** — current account balance.

#### Kalshi API field reference

Market objects use these field names:
- `last_price_dollars` — last trade price as string, e.g. `"0.5600"` (dollar amount 0–1, NOT cents)
- `yes_bid_dollars` / `yes_ask_dollars` — best bid/ask as strings
- `no_bid_dollars` / `no_ask_dollars` — best NO bid/ask as strings
- `status` — one of: `active`, `inactive`, `finalized`

From the market data, extract:
- `current_yes_price_cents`: `int(float(last_price_dollars) * 100)` — convert to cents
- `market_status`: must be `active`

If the market is not active, report the error and stop.

---

### Step 4: Determine Exit Parameters

Calculate the exit order details.

**Full exit** (no `amount` argument):
```python
exit_quantity = position_data["quantity"]
is_partial = False
```

**Partial exit** (`amount` given):
```python
amount_cents = int(float(amount) * 100)
current_yes_price = <last_price from get_market>

if position_data["side"] == "YES":
    exit_quantity = amount_cents // current_yes_price
else:
    exit_quantity = amount_cents // (100 - current_yes_price)

# Cap at total position size
exit_quantity = min(exit_quantity, position_data["quantity"])
is_partial = exit_quantity < position_data["quantity"]

if exit_quantity <= 0:
    # ERROR: Amount too small to exit any contracts
    pass
```

Determine the exit price from the orderbook:
- **YES position**: selling YES contracts — the exit price is the **best bid** for YES.
  - Use the highest bid price from the orderbook.
- **NO position**: selling NO contracts — the exit price is `100 - best_ask`.
  - The best ask for YES means the best bid for NO is `100 - best_ask`.

If the orderbook has no bids/asks, use the last trade price as an estimate and warn the user about low liquidity.

```python
# For YES position:
orderbook = <orderbook from get_market_orderbook>
if position_data["side"] == "YES":
    # Best bid for YES
    if orderbook.get("yes") and len(orderbook["yes"]) > 0:
        exit_price = orderbook["yes"][0][0]  # highest bid price
    else:
        exit_price = current_yes_price  # fallback
else:
    # Best bid for NO = 100 - best ask for YES
    if orderbook.get("no") and len(orderbook["no"]) > 0:
        exit_price = orderbook["no"][0][0]  # highest bid for NO
    else:
        exit_price = 100 - current_yes_price  # fallback
```

Calculate realized P&L:
```python
avg_price = position_data["avg_price_cents"]
realized_pnl_cents = exit_quantity * (exit_price - avg_price)
proceeds_cents = exit_quantity * exit_price

remaining_quantity = position_data["quantity"] - exit_quantity
```

---

### Step 5: Present Exit Confirmation

Display a detailed confirmation prompt:

```
## Exit Confirmation

### Current Position
- **Ticker**: <ticker>
- **Side**: <YES/NO>
- **Quantity**: <N> contracts
- **Average Price**: <XX> cents
- **Total Cost**: $<XX.XX>

### Exit Order
- **Action**: Sell <N> contracts (<full/partial> exit)
- **Estimated Exit Price**: <XX> cents (best bid)
- **Estimated Proceeds**: $<XX.XX>

### Realized P&L
- **Entry Price**: <XX> cents (avg)
- **Exit Price**: ~<XX> cents
- **P&L per Contract**: <+/-><XX> cents
- **Total Realized P&L**: <+/->$<XX.XX>

### Remaining Position
- **Contracts**: <N> (or "None — position fully closed")
- **Value**: $<XX.XX>

---
**Do you want to proceed with this exit? (yes/no)**
```

Use formatting helpers for dollar amounts:
```python
from formatting import usd_cents_to_display
```

**CRITICAL: Wait for the user to explicitly type "yes" or confirm.** Do NOT auto-execute. Do NOT proceed without confirmation.

---

### Step 6: Execute the Exit

Only after the user confirms, place the exit order.

**IMPORTANT: Always use `order_type: "limit"`.** The Kalshi API returns 400 Bad Request for `order_type: "market"`. Use the orderbook-derived exit price from Step 4 as the limit price.

Call **`create_order`** with:
- `ticker`: the market ticker (string)
- `action`: `"sell"` (string)
- `side`: same side as the position (`"yes"` or `"no"`, lowercase)
- `order_type`: `"limit"` (ALWAYS — never use `"market"`)
- `count`: `exit_quantity` (integer, number of contracts to sell)
- `yes_price`: exit price in cents (integer) — use for **YES side** positions
- `no_price`: exit price in cents (integer) — use for **NO side** positions

**Only set the price field matching the side.** For YES positions, set `yes_price`. For NO positions, set `no_price`.

Example for selling a NO position at 56 cents:
```
create_order(
    ticker="KXABRAHAMSA-29-JAN20",
    action="sell",
    side="no",
    order_type="limit",
    count=6,
    no_price=56
)
```

If the order fails, display the error and stop. Do NOT update memory files.

---

### Step 7: Confirm Execution

After placing the order:

1. Call **`get_orders`** to check order status.
2. Call **`get_fills`** with the ticker to confirm fill details.

Extract from the fill/order:
- `order_id`
- `fill_price` (actual exit price in cents)
- `fill_quantity`
- `fill_status` (filled, partial)

Recalculate actual realized P&L using the real fill price:
```python
actual_pnl_cents = fill_quantity * (fill_price - avg_price_cents)
actual_proceeds_cents = fill_quantity * fill_price
```

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
    "action": "sell",
    "quantity": <fill_quantity>,
    "price_cents": <fill_price>,
    "proceeds_cents": <fill_quantity> * <fill_price>,
    "order_type": "market",
    "status": "<filled>",
}
append_yaml_list(market_dir / "trades.yaml", "trades", trade_entry)

# Ensure ticker is set at top level
trades_data = read_yaml(market_dir / "trades.yaml")
trades_data["ticker"] = ticker
write_yaml(market_dir / "trades.yaml", trades_data)
```

#### 8.2 Update Position

Update `.claudshi/events/<slug>/markets/<ticker>/position.yaml`:

```python
if remaining_quantity == 0:
    # Full exit — mark position as closed
    position_data = {
        "ticker": ticker,
        "event_slug": event_slug,
        "side": "<YES/NO>",
        "quantity": 0,
        "avg_price_cents": <original_avg_price>,
        "total_cost_cents": 0,
        "opened_at": existing_position.get("opened_at"),
        "closed_at": now_iso,
        "updated_at": now_iso,
        "realized_pnl_cents": <actual_pnl_cents>,
    }
else:
    # Partial exit — reduce quantity, keep avg price unchanged
    remaining_cost = remaining_quantity * existing_position["avg_price_cents"]
    position_data = {
        "ticker": ticker,
        "event_slug": event_slug,
        "side": "<YES/NO>",
        "quantity": remaining_quantity,
        "avg_price_cents": existing_position["avg_price_cents"],
        "total_cost_cents": remaining_cost,
        "opened_at": existing_position.get("opened_at"),
        "updated_at": now_iso,
    }

write_yaml(market_dir / "position.yaml", position_data)
```

#### 8.3 Log the Action

Append to `.claudshi/events/<slug>/markets/<ticker>/actions_log.yaml`:

```python
action = {
    "timestamp": now_iso,
    "type": "exit",
    "exit_type": "full" if remaining_quantity == 0 else "partial",
    "side": "<YES/NO>",
    "quantity": <fill_quantity>,
    "price": <fill_price>,
    "realized_pnl_cents": <actual_pnl_cents>,
    "order_id": "<order_id>",
    "remaining_quantity": remaining_quantity,
}
append_yaml_list(market_dir / "actions_log.yaml", "actions", action)

# Ensure ticker at top level
log_data = read_yaml(market_dir / "actions_log.yaml")
log_data["ticker"] = ticker
write_yaml(market_dir / "actions_log.yaml", log_data)
```

If this was a full exit, add a position_closed entry:

```python
if remaining_quantity == 0:
    closed_action = {
        "timestamp": now_iso,
        "type": "position_closed",
        "summary": f"Position fully closed. Total realized P&L: {usd_cents_to_display(actual_pnl_cents)}",
    }
    append_yaml_list(market_dir / "actions_log.yaml", "actions", closed_action)
```

#### 8.4 Update Portfolio Summary

Update `.claudshi/portfolio/summary.yaml` (note: `portfolio/`, NOT `cs_portfolio/`):

```python
summary = load_portfolio_summary()
positions = summary.get("positions", {})

if remaining_quantity == 0:
    # Full exit — remove from portfolio
    positions.pop(ticker, None)
else:
    # Partial exit — update quantity
    if ticker in positions:
        positions[ticker]["quantity"] = remaining_quantity
        positions[ticker]["total_cost_cents"] = remaining_quantity * existing_position["avg_price_cents"]

summary["positions"] = positions
summary["total_invested_cents"] = sum(
    p["total_cost_cents"] for p in positions.values()
) if positions else 0
summary["updated_at"] = now_iso
save_portfolio_summary(summary)
```

---

### Step 9: Present Execution Summary

After all memory files are updated, display:

```
## Exit Executed

- **Ticker**: <ticker>
- **Sold**: <N> contracts at <XX> cents
- **Proceeds**: $<XX.XX>
- **Realized P&L**: <+/->$<XX.XX>
- **Order ID**: <order_id>

### Remaining Position
<"<N> contracts at <XX> cents avg" or "Position fully closed.">

### Next Steps
- Run `/cs_portfolio` to see your updated portfolio
- Run `/cs_journal` to record this exit
```

---

## Important Notes

- **NEVER auto-execute exits.** Always wait for explicit user confirmation before calling `create_order`.
- **ALWAYS use `order_type: "limit"`.** The Kalshi API returns 400 Bad Request for `order_type: "market"`. Derive the exit price from the orderbook.
- **Require existing position.** If no position exists for this ticker, stop immediately with a clear error.
- **Handle both full and partial exits.** Default to full exit when no amount is specified.
- **Log everything.** Every exit must be recorded in trades.yaml, position.yaml, actions_log.yaml, and portfolio summary.
- **Handle errors gracefully.** If the order fails, display the error clearly and do not update memory files.
- **Mark closed positions.** When a position is fully closed, set `quantity` to 0, add `closed_at` timestamp, and log a `position_closed` action.
- **Preserve avg price on partial exit.** When partially exiting, the remaining position keeps the same average entry price.
- **Price fields are dollar strings.** `last_price_dollars`, `yes_bid_dollars`, etc. are strings in 0–1 range, NOT cents. Convert with `int(float(x) * 100)`.
- **Portfolio path is `.claudshi/portfolio/`**, not `.claudshi/cs_portfolio/`.
