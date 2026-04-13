# /cs_bet — Place a Trade

## Usage

```
/cs_bet <ticker> <side> <amount> [price]
```

- `ticker`: Market ticker (e.g., `KXUSAIRANAGREEMENT-27`)
- `side`: `YES` or `NO`
- `amount`: Amount to risk in USD (e.g., `25`)
- `price`: Optional limit price in cents (1-99). If omitted, uses a market order.

Examples:
```
/cs_bet KXUSAIRANAGREEMENT-27 YES 25
/cs_bet KXUSAIRANAGREEMENT-27 NO 10 35
```

## Instructions

When the user invokes `/cs_bet`, follow **every** step below in order. Do not skip steps.

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

Check that an analysis and probability estimate exist for this market in the `.claudshi/` memory tree.

- Scan `.claudshi/events/*/markets/<ticker>/probability.yaml` to find the market.
- If no analysis exists, display an error telling the user to run `/cs_analyze <ticker>` first.
- If analysis exists, load the probability estimate (current `yes_probability` and `confidence`).

---

### Step 3: Fetch Current Market Data

Call these MCP tools in parallel:

1. **`get_market`** with the ticker — current market details.
2. **`get_market_orderbook`** with the ticker — current bid/ask depth.
3. **`get_balance`** — current account balance.
4. **`get_positions`** — all current open positions.

Verify the market is open/active. If not, report the error and stop.

---

### Step 4: Run Risk Checks

Perform all risk checks using `lib/risk.py` logic:

1. **Market expiry**: Must be more than 1 hour away.
2. **Bet size limits**: Max single bet, max position, max portfolio exposure.
3. **Concentration**: Warn if >40% of portfolio in one event.
4. **Edge threshold**: Warn if edge < `min_edge_pct` (default 10%).

Hard-block on expiry and bet limit violations. Warn (but allow) on concentration and edge.

---

### Step 5: Present Trade Confirmation

Display a detailed confirmation prompt including:
- Market title, ticker, current price, expiration.
- Our probability estimate vs. market probability.
- Edge calculation.
- Order details (side, type, quantity, estimated cost).
- Risk check results (pass/fail/warn for each).
- Portfolio impact (exposure before and after).

**Wait for explicit user confirmation.** Do NOT auto-execute.

---

### Step 6: Execute the Trade

On user confirmation, call `create_order` with the appropriate parameters.

---

### Step 7: Confirm Execution

Check order status and fills:
- For market orders: confirm fill immediately.
- For limit orders: report if resting or filled.

---

### Step 8: Update Memory Files

After successful execution, update:
- `trades.yaml` — append the trade entry.
- `position.yaml` — update or create the position.
- `actions_log.yaml` — log the bet action.
- `portfolio/summary.yaml` — update aggregate portfolio data.

---

### Step 9: Present Execution Summary

Display the trade result: ticker, side, quantity, price, cost, order ID, and updated position. Suggest next steps (`/cs_portfolio`, `/cs_monitor`).

---

## Important Notes

- **NEVER auto-execute trades.** Always wait for explicit user confirmation.
- **Require prior analysis.** No `probability.yaml` = no trade. User must run `/cs_analyze` first.
- **Enforce all risk rules.** Hard-block on critical violations, warn on soft violations.
- **Log everything.** Every trade must be recorded in memory.
- **Handle errors gracefully.** If the order fails, do not update memory files.
