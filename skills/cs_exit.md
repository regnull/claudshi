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

When the user invokes `/cs_exit`, follow **every** step below in order. Do not skip steps.

---

### Step 1: Parse and Validate Inputs

Parse the arguments: `<ticker> [amount]`

1. **Ticker**: Required. Must be a non-empty string.
2. **Amount**: Optional. If provided, must be a positive number (USD). This is the dollar amount of the position to exit. If omitted, close the entire position.

If the ticker is missing, show usage help and stop.

---

### Step 2: Load Current Position

Find the position in the `.claudshi/` memory tree.

- Scan `.claudshi/events/*/markets/<ticker>/position.yaml` to find the market.
- If no position file exists, or the position quantity is 0, display an error: "No open position found for `<ticker>`. Nothing to exit."
- **Stop here** if no position exists.

If a position exists, load the position data:
- `side` (YES or NO)
- `quantity` (number of contracts)
- `avg_price_cents` (average entry price)
- `total_cost_cents`
- `event_slug`

---

### Step 3: Fetch Current Market Data

Call these MCP tools in parallel:

1. **`get_market`** with the ticker — current market details (last price, status).
2. **`get_market_orderbook`** with the ticker — current bid/ask depth.
3. **`get_balance`** — current account balance.

Verify the market is open/active. If not, report the error and stop.

---

### Step 4: Determine Exit Parameters

Calculate the exit order:

- **Full exit** (no `amount` argument): sell the entire position.
  - `exit_quantity = position_quantity`
- **Partial exit** (`amount` given):
  - Convert amount to cents: `amount_cents = int(amount * 100)`
  - Calculate contracts to exit based on current market price:
    - For YES side: `exit_quantity = amount_cents / current_yes_price` (rounded down)
    - For NO side: `exit_quantity = amount_cents / (100 - current_yes_price)` (rounded down)
  - Cap at total position size: `exit_quantity = min(exit_quantity, position_quantity)`
  - If `exit_quantity <= 0`, display an error and stop.

Determine exit price from the orderbook:
- For YES position: selling YES contracts — use the best bid price.
- For NO position: selling NO contracts — use `100 - best_ask` (complement).

Calculate realized P&L for the exit:
- For YES side: `realized_pnl_cents = exit_quantity * (exit_price - avg_price_cents)`
- For NO side: `realized_pnl_cents = exit_quantity * (exit_price - avg_price_cents)`

Calculate remaining position after exit:
- `remaining_quantity = position_quantity - exit_quantity`

---

### Step 5: Present Exit Confirmation

Display a detailed confirmation:

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
- **P&L per Contract**: <+/-> <XX> cents
- **Total Realized P&L**: <+/->$<XX.XX>

### Remaining Position
- **Contracts**: <N> (or "None — position fully closed")
- **Value**: $<XX.XX>

---
**Do you want to proceed with this exit? (yes/no)**
```

**CRITICAL: Wait for the user to explicitly confirm.** Do NOT auto-execute.

---

### Step 6: Execute the Exit

On user confirmation, place the exit order using `create_order`:

- `ticker`: the market ticker
- `action`: `sell`
- `side`: same side as the position (`yes` or `no`, lowercase)
- `type`: `market`
- `count`: `exit_quantity` (number of contracts to sell)

If the order fails, display the error and stop. Do not update memory files.

---

### Step 7: Confirm Execution

After placing the order:

1. Call **`get_orders`** to check order status.
2. Call **`get_fills`** with the ticker to confirm fill details.

Extract:
- `order_id`
- `fill_price` (actual exit price)
- `fill_quantity`
- `fill_status`

Recalculate actual realized P&L using the real fill price instead of the estimate.

---

### Step 8: Update Memory Files

After successful execution, update all memory files.

#### 8.1 Update Trades Log

Append to `.claudshi/events/<slug>/markets/<ticker>/trades.yaml`:

```yaml
- timestamp: "<now_iso>"
  order_id: "<order_id>"
  side: "<YES/NO>"
  action: "sell"
  quantity: <fill_quantity>
  price_cents: <fill_price>
  proceeds_cents: <fill_quantity * fill_price>
  order_type: "market"
  status: "<filled>"
```

#### 8.2 Update Position

Update `.claudshi/events/<slug>/markets/<ticker>/position.yaml`:

- If full exit: set `quantity` to 0, add `closed_at` timestamp.
- If partial exit: reduce `quantity`, keep `avg_price_cents` unchanged.

#### 8.3 Log the Action

Append to `.claudshi/events/<slug>/markets/<ticker>/actions_log.yaml`:

```yaml
- timestamp: "<now_iso>"
  type: "exit"
  exit_type: "<full/partial>"
  side: "<YES/NO>"
  quantity: <fill_quantity>
  price: <fill_price>
  realized_pnl_cents: <actual_pnl>
  order_id: "<order_id>"
  remaining_quantity: <remaining>
```

If full exit, add an additional action entry:

```yaml
- timestamp: "<now_iso>"
  type: "position_closed"
  summary: "Position fully closed. Total realized P&L: $<X.XX>"
```

#### 8.4 Update Portfolio Summary

Update `.claudshi/cs_portfolio/summary.yaml`:

- If full exit: remove the ticker from positions.
- If partial exit: update the position's quantity and total cost.
- Recalculate `total_invested_cents`.

---

### Step 9: Present Execution Summary

Display the result:

```
## Exit Executed

- **Ticker**: <ticker>
- **Sold**: <N> contracts at <XX> cents
- **Proceeds**: $<XX.XX>
- **Realized P&L**: <+/->$<XX.XX>
- **Order ID**: <order_id>

### Remaining Position
<position details or "Position fully closed.">

### Next Steps
- Run `/cs_portfolio` to see your updated portfolio
- Run `/cs_journal` to record this exit
```

---

## Important Notes

- **NEVER auto-execute exits.** Always wait for explicit user confirmation.
- **Require existing position.** If no position exists, stop immediately.
- **Handle both full and partial exits.** Default to full exit when no amount is specified.
- **Log everything.** Every exit must be recorded in trades.yaml, position.yaml, actions_log.yaml, and portfolio summary.
- **Handle errors gracefully.** If the order fails, display the error clearly and do not update memory files.
- **Mark closed positions.** When a position is fully closed, add a `position_closed` entry to the actions log.
