# /monitor — Check All Tracked Markets for Updates

## Usage

```
/monitor
```

No arguments. Scans all tracked markets (positions first, then watchlist) for changes, performs incremental analysis updates, and recommends actions.

## Instructions

When the user invokes `/monitor`, follow **every** step below in order. Do not skip steps.

---

### Step 1: Load Tracked Markets from Memory

Gather all markets that Claudshi is tracking.

#### 1.1 Positioned Markets

Scan `.claudshi/events/*/markets/*/position.yaml` for files where `quantity > 0`. For each, load:

- `position.yaml` — current position details (side, quantity, avg price).
- `market.yaml` — market metadata (ticker, title, expiration, event slug).
- `probability.yaml` — our last probability estimate and history.
- The most recent analysis file from `analysis/` directory.

```python
import sys; sys.path.insert(0, "lib")
from memory import read_yaml, ensure_dirs
from pathlib import Path

ensure_dirs()

root = Path(".claudshi/events")
positioned_markets = []
if root.exists():
    for pos_file in root.glob("*/markets/*/position.yaml"):
        pos = read_yaml(pos_file)
        if pos.get("quantity", 0) > 0:
            market_dir = pos_file.parent
            event_dir = market_dir.parent.parent
            positioned_markets.append({
                "market_dir": market_dir,
                "event_slug": event_dir.name,
                "position": pos,
                "market": read_yaml(market_dir / "market.yaml"),
                "probability": read_yaml(market_dir / "probability.yaml"),
            })
```

#### 1.2 Watchlist Markets

Load `.claudshi/watchlist.yaml`:

```python
from memory import load_watchlist
watchlist = load_watchlist()
```

For each watchlist entry, load its memory files if they exist:
- `market.yaml` and `probability.yaml` from `.claudshi/events/<event_slug>/markets/<ticker>/`.

If no tracked markets exist (no positions and empty watchlist), report:

```
## Monitor

No tracked markets found. Use `/analyze` to analyze a market or `/scan` to find opportunities.
```

And stop.

---

### Step 2: Fetch Latest Market Data

For each tracked market (positions first, then watchlist), call MCP tools to get current state.

Make calls in parallel where possible:

1. **`get_market`** with the ticker — current price, volume, status.
2. **`get_market_orderbook`** with the ticker — current bid/ask depth.
3. **`get_trades`** with the ticker (limit 20) — recent trade activity.

From the market response, extract:
- `current_price_cents`: the `last_price` field.
- `market_probability`: `last_price / 100`.
- `status`: whether the market is still active.
- `volume`: current volume.

Compare to the stored `market.yaml` data to detect price movements.

---

### Step 3: Research Latest News

For each tracked market, search for the latest news:

```
WebSearch: "<event title> latest news <current year>"
```

Focus searches on positioned markets first (they carry financial risk). For watchlist markets, do lighter searches.

Gather any material developments since the last analysis.

---

### Step 4: Assess Changes and Update Analysis

For each market, determine if anything material has changed since the last analysis. Consider:

- **Price movement**: Has the market price moved more than 5 cents since last check?
- **News developments**: Are there new events that affect the probability?
- **Time decay**: Is the market significantly closer to expiration?
- **Volume changes**: Has trading activity increased or decreased significantly?

#### 4.1 Markets With Material Changes

For each market where something material changed, perform an **incremental analysis update** (lighter than a full `/analyze`):

1. Note what changed since the last analysis.
2. Re-assess the relevant factors from the Analysis Framework (only the ones affected by the change).
3. Update the probability estimate if warranted.
4. Calculate the new edge vs. market price.

Save the update:

```python
from memory import (
    write_md, write_yaml, append_yaml_list,
    get_market_dir, get_analysis_path, get_next_update_num
)
from datetime import datetime, timezone

today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
now_iso = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

event_slug = "<EVENT_SLUG>"
ticker = "<TICKER>"

# Save analysis update
update_num = get_next_update_num(event_slug, ticker, today)
update_path = get_analysis_path(event_slug, ticker, today, update_num)
update_content = """# Analysis Update: <Market Title>
**Ticker:** <ticker>
**Date:** <date>
**Update #:** <update_num>

## What Changed
<describe what triggered this update>

## Updated Assessment
<re-assess affected factors only>

## Updated Probability
- Previous estimate: <old_prob>%
- New estimate: <new_prob>%
- Confidence: <low/medium/high>
- Reasoning: <why the change>

## Market Price Comparison
- Market price: <current_price>%
- Our estimate: <new_prob>%
- Edge: <edge>%

## Recommended Action
<Hold / Add / Reduce / Exit / Enter>
"""
write_md(update_path, update_content)

# Update probability.yaml
market_dir = get_market_dir(event_slug, ticker)
prob_data = read_yaml(market_dir / "probability.yaml")
prob_data["current_estimate"] = {
    "yes_probability": <NEW_ESTIMATE>,
    "confidence": "<low/medium/high>",
    "updated_at": now_iso,
    "reasoning": "<one-sentence summary of change>",
}
if "history" not in prob_data:
    prob_data["history"] = []
prob_data["history"].append({
    "timestamp": now_iso,
    "yes_probability": <NEW_ESTIMATE>,
    "market_price": <market_price_decimal>,
    "trigger": "<what triggered the update>",
})
write_yaml(market_dir / "probability.yaml", prob_data)

# Log the action
append_yaml_list(
    market_dir / "actions_log.yaml",
    "actions",
    {
        "timestamp": now_iso,
        "type": "update",
        "summary": f"Probability adjusted from <old> to <new> — <reason>",
        "details": f"See analysis/{today}-update-{update_num:02d}.md",
    },
)
```

#### 4.2 Markets With No Material Changes

For markets where nothing significant changed, simply note:
- Current price and our estimate are consistent.
- No relevant news.
- No action needed.

---

### Step 5: Save Orderbook Snapshots

For each market (positioned and watchlist), save an orderbook snapshot for trend tracking:

```python
from memory import write_yaml, get_market_dir
from datetime import datetime, timezone

now_ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
market_dir = get_market_dir(event_slug, ticker)
snapshot_dir = market_dir / "orderbook_snapshots"
snapshot_dir.mkdir(parents=True, exist_ok=True)

snapshot = {
    "timestamp": now_iso,
    "ticker": ticker,
    "best_bid": <best_bid_cents>,
    "best_ask": <best_ask_cents>,
    "spread": <spread_cents>,
    "bid_depth": <total_bid_volume>,
    "ask_depth": <total_ask_volume>,
    "last_price": <last_price_cents>,
}
write_yaml(snapshot_dir / f"{now_ts}.yaml", snapshot)
```

---

### Step 6: Determine Recommended Actions

For each market, determine the recommended action based on the updated analysis.

**For positioned markets:**

| Condition | Action | Details |
|-----------|--------|---------|
| Edge increased, confidence medium+ | **Add** | Suggest additional buy with Kelly sizing |
| Edge stable, no material changes | **Hold** | No action needed |
| Edge decreased but still positive | **Hold** | Monitor closely |
| Edge gone or reversed | **Reduce** / **Exit** | Suggest partial or full exit |
| Market near expiration (<24h) | **Review** | Flag for attention, may need to exit |
| Market settled/closed | **Closed** | Update position records |

**For watchlist markets:**

| Condition | Action | Details |
|-----------|--------|---------|
| Edge materialized (>= min_edge_pct) | **Enter** | Suggest initial position with Kelly sizing |
| Edge growing but below threshold | **Watch** | Keep monitoring |
| No edge, market uninteresting | **Remove** | Suggest removing from watchlist |

For **Add** and **Enter** recommendations, calculate suggested position size using quarter-Kelly:

```python
from risk import calculate_position_size, calculate_edge, load_risk_config
from memory import load_portfolio_summary, load_config

config = load_config()
risk_config = load_risk_config()
portfolio = load_portfolio_summary()

edge = calculate_edge(claude_probability, market_probability)
bankroll = portfolio.get("cash_cents", 0) / 100  # convert to USD

suggested_size = calculate_position_size(
    edge, market_probability, bankroll, risk_config
)
```

---

### Step 7: Update Market Metadata

Update `market.yaml` for each tracked market with the latest data from Kalshi:

```python
market_meta = read_yaml(market_dir / "market.yaml")
market_meta.update({
    "last_price": <current_last_price>,
    "volume": <current_volume>,
    "status": "<current_status>",
    "updated_at": now_iso,
})
write_yaml(market_dir / "market.yaml", market_meta)
```

---

### Step 8: Write Daily Journal Entry

Generate a daily journal entry summarizing all monitoring findings. Save to `.claudshi/journal/<YYYY-MM-DD>.md`:

```python
from memory import write_md
from pathlib import Path

journal_dir = Path(".claudshi/journal")
journal_dir.mkdir(parents=True, exist_ok=True)
journal_path = journal_dir / f"{today}.md"

journal_content = """# Daily Monitor Journal — <YYYY-MM-DD>

## Summary
<one-paragraph overview of the day's findings>

## Positioned Markets

### <Ticker 1>: <Market Title>
- **Position:** <side> x<quantity> @ $<avg_price>
- **Current Price:** $<current_price> (was $<last_price>)
- **Our Estimate:** <probability>% (confidence: <level>)
- **Edge:** <edge>%
- **P&L:** $<unrealized_pnl>
- **Action:** <Hold/Add/Reduce/Exit>
- **Notes:** <any relevant news or observations>

### <Ticker 2>: ...

## Watchlist Markets

### <Ticker>: <Market Title>
- **Current Price:** $<price>
- **Our Estimate:** <probability>%
- **Edge:** <edge>%
- **Action:** <Enter/Watch/Remove>

## Key Observations
- <notable market movements>
- <news developments>
- <lessons learned>

---
*Generated by Claudshi /monitor at <timestamp>*
"""

# If a journal entry already exists for today, append to it
existing = ""
if journal_path.exists():
    existing = journal_path.read_text()
    journal_content = existing + "\n\n---\n\n" + journal_content

write_md(journal_path, journal_content)
```

---

### Step 9: Present Monitor Report

Display the full monitoring report to the user. Structure:

```
## Monitor Report — <YYYY-MM-DD HH:MM UTC>

### Positioned Markets (<N> tracked)

| Ticker | Side | Qty | Entry | Current | P&L | Edge | Action |
|--------|------|-----|-------|---------|-----|------|--------|
| TICK1  | YES  | 50  | $0.25 | $0.30   | +$2.50 | +8% | Hold |
| TICK2  | NO   | 30  | $0.40 | $0.45   | -$1.50 | -3% | Exit |

#### <Ticker> — <Market Title>
<brief summary of what changed and recommended action>
<if Add/Enter: suggested order details>
<if Reduce/Exit: "Run `/exit <ticker>` to close position">

### Watchlist Markets (<N> tracked)

| Ticker | Title | Price | Our Est. | Edge | Action |
|--------|-------|-------|----------|------|--------|
| TICK3  | Will X happen? | $0.35 | 48% | +13% | Enter |
| TICK4  | Will Y happen? | $0.60 | 58% | -2% | Remove |

#### <Ticker> — <Market Title> (if action is Enter)
<brief reasoning and suggested order details>

### Markets With No Changes
- <TICKER>: No material changes. Hold / Watch.

---
*Journal entry saved to `.claudshi/journal/<date>.md`*
*Next monitor recommended in <monitor_interval_hours> hours.*
```

---

## Important Notes

- **Never place trades from this skill.** Only recommend. Tell the user to use `/bet` for new positions and `/exit` for closing.
- **Incremental updates, not full re-analyses.** Focus on what changed. Reference the previous analysis rather than redoing everything.
- **Positions take priority.** Always check positioned markets first and with more depth than watchlist markets.
- **Be honest about uncertainty.** If you're not sure whether news is material, say so.
- **Save everything.** Every update, snapshot, and journal entry must be written to memory.
- **Flag urgency.** Markets near expiration or with large adverse moves should be highlighted prominently.
- **Show the interval.** Remind the user when to run `/monitor` next (from `monitor_interval_hours` config, default 12).
