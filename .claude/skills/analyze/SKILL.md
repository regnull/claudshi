---
name: analyze
description: Deep analysis of a political market — fetches data, researches the event, estimates probabilities, and recommends a trade action.
disable-model-invocation: true
argument-hint: "<market-url-or-ticker>"
allowed-tools: Read Write Bash WebSearch WebFetch mcp__kalshi-mcp__get_market mcp__kalshi-mcp__get_event mcp__kalshi-mcp__get_markets mcp__kalshi-mcp__get_market_orderbook mcp__kalshi-mcp__get_trades mcp__kalshi-mcp__get_market_candlesticks mcp__kalshi-mcp__lookup_event mcp__kalshi-mcp__get_series
---

# /analyze — Deep Political Event Analysis

## Usage

```
/analyze <market-url-or-ticker>
```

Examples:
```
/analyze KXUSAIRANAGREEMENT-27
/analyze https://kalshi.com/markets/kxusairanagreement/us-iran-agreement
```

## Instructions

The user's arguments: $ARGUMENTS

When the user invokes `/analyze`, follow **every** step below in order. Do not skip steps.

---

### Step 1: Parse Input

Extract the market ticker from the input:
- If the input looks like a Kalshi URL (contains `kalshi.com`), extract the ticker from the URL path. Kalshi URLs have the form `https://kalshi.com/markets/<series-ticker>/<event-slug>`. You may need to call `get_markets` with a search to find the exact ticker.
- If the input is already a ticker (e.g. `KXUSAIRANAGREEMENT-27`), use it directly.

Store the ticker for all subsequent steps.

---

### Step 2: Fetch Market Data

Call these MCP tools to gather all market data. Make calls in parallel where possible.

1. **`get_market`** with the ticker — gets market details (title, expiration, last price, volume, status, etc.).
2. **`get_event`** using the `event_ticker` from the market response — gets the parent event (title, category, nested markets).
3. **`lookup_event`** with the event ticker — gets settlement criteria and resolution sources.
4. **`get_market_orderbook`** with the ticker — gets current bid/ask depth.
5. **`get_trades`** with the ticker (limit 50) — gets recent trade history.
6. **`get_market_candlesticks`** with the ticker — gets OHLCV price history.

If any call fails, note the failure and continue with available data.

From the market data, extract:
- `event_slug`: derive from the event ticker (lowercase, hyphenated). Use the event ticker as-is if it looks like a slug, otherwise convert to lowercase with hyphens.
- `market_probability`: the market-implied YES probability = `last_price / 100` (Kalshi prices are in cents 0–99).

---

### Step 3: Research the Event

Use **WebSearch** to research the political event. Perform 2–3 searches:

1. Search for the event title + "latest news" to find recent developments.
2. Search for the event title + "prediction" or "odds" to find expert opinions.
3. If relevant, search for historical precedents (e.g., "how often has Congress passed [type of bill]").

Read the top results to gather:
- Latest news and developments.
- Expert opinions and forecasts.
- Historical base rates for similar events.
- Geopolitical context.

---

### Step 4: Perform Analysis Framework

Now perform the structured analysis. Think through each section carefully and write your analysis in full.

#### 4.1 Event Decomposition
- What exactly needs to happen for YES to resolve?
- What is the time window?
- Are there intermediate milestones we can track?

#### 4.2 Base Rate Analysis
- How often do events of this type resolve YES historically?
- What is the prior probability before considering current circumstances?

#### 4.3 Factor Analysis
Rate each factor on a -5 to +5 scale (negative = favors NO, positive = favors YES):

| Factor | Score (-5 to +5) | Reasoning |
|--------|-------------------|-----------|
| **Political will** | ? | Do key decision-makers want this outcome? |
| **Institutional feasibility** | ? | Can the mechanism deliver this outcome in time? |
| **Public pressure** | ? | Is public opinion pushing toward this outcome? |
| **External forces** | ? | Are international/economic/military factors at play? |
| **Precedent** | ? | How does this compare to historical analogs? |
| **Momentum** | ? | Is the situation trending toward or away from this outcome? |

#### 4.4 Probability Synthesis
- Start from the base rate.
- Adjust for each factor.
- Apply calibration: avoid extreme probabilities (rarely below 5% or above 95%) unless resolution is near-certain.
- Assign a confidence level: **low** (limited info, high uncertainty), **medium** (reasonable info, moderate uncertainty), or **high** (strong info, low uncertainty).
- State your final YES probability estimate.

#### 4.5 Edge Calculation
```
edge = claude_probability - market_probability
```
If `abs(edge) >= min_edge_pct` (from config, default 10%), there is a tradeable edge.

#### 4.6 Position Sizing (if edge exists)
Use quarter-Kelly criterion:
```
kelly_fraction = (edge * (1 - market_probability)) / (1 - edge)
bet_size = kelly_fraction * bankroll * 0.25
bet_size = min(bet_size, max_single_bet_usd)
```

Load the config to get `max_single_bet_usd` and `min_edge_pct`. Load the portfolio summary (or assume a starting bankroll if no portfolio exists yet).

---

### Step 5: Save Analysis to Memory

Run the following Python to determine paths and save the analysis. Use today's date.

```python
import sys; sys.path.insert(0, "lib")
from memory import (
    ensure_dirs, write_yaml, write_md, append_yaml_list,
    get_event_dir, get_market_dir, get_analysis_path, load_config
)
from datetime import datetime, timezone

# Get today's date
today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
now_iso = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

# Ensure directories exist
ensure_dirs()

event_slug = "<EVENT_SLUG>"
ticker = "<TICKER>"
```

#### 5.1 Save Event Metadata

Write `.claudshi/events/<event_slug>/event.yaml`:
```python
event_data = {
    "event_ticker": "<event_ticker from get_event>",
    "title": "<event title>",
    "category": "<category>",
    "mutually_exclusive": "<from event data>",
    "series_ticker": "<series_ticker if available>",
    "updated_at": now_iso,
}
write_yaml(get_event_dir(event_slug) / "event.yaml", event_data)
```

#### 5.2 Save Market Metadata

Write `.claudshi/events/<event_slug>/markets/<ticker>/market.yaml`:
```python
market_meta = {
    "ticker": "<ticker>",
    "title": "<market title>",
    "event_ticker": "<event_ticker>",
    "expiration_time": "<expiration>",
    "settlement_source": "<from lookup_event>",
    "last_price": <last_price_cents>,
    "volume": <volume>,
    "open_interest": <open_interest>,
    "status": "<status>",
    "updated_at": now_iso,
}
write_yaml(get_market_dir(event_slug, ticker) / "market.yaml", market_meta)
```

#### 5.3 Save Analysis Document

Write the full analysis as markdown to `.claudshi/events/<event_slug>/markets/<ticker>/analysis/<date>-initial.md`:

```python
analysis_content = """<YOUR FULL ANALYSIS HERE>

Include all sections:
- Event Decomposition
- Base Rate Analysis
- Factor Analysis (with table)
- Probability Synthesis
- Edge Calculation
- Position Sizing recommendation (if applicable)
- Sources consulted
"""
write_md(get_analysis_path(event_slug, ticker, today), analysis_content)
```

The analysis markdown should follow this template:

```markdown
# Analysis: <Market Title>
**Ticker:** <ticker>
**Date:** <date>
**Analyst:** Claude (Claudshi)

## Event Decomposition
<what needs to happen for YES, time window, milestones>

## Base Rate Analysis
<historical frequency, prior probability>

## Factor Analysis

| Factor | Score | Reasoning |
|--------|-------|-----------|
| Political will | <score> | <reasoning> |
| Institutional feasibility | <score> | <reasoning> |
| Public pressure | <score> | <reasoning> |
| External forces | <score> | <reasoning> |
| Precedent | <score> | <reasoning> |
| Momentum | <score> | <reasoning> |

## Probability Synthesis
- Base rate: <X%>
- Adjusted probability: <Y%>
- Confidence: <low/medium/high>
- Key drivers: <what moves the needle most>

## Edge Calculation
- Claude estimate: <X%>
- Market price: <Y%>
- Edge: <Z%>
- Minimum edge threshold: <from config>

## Recommendation
<Trade / Watch / Pass>
<If Trade: suggested side, size, price>
<If Watch: what to monitor for>
<If Pass: why no edge>

## Sources
- <list of sources consulted>
```

#### 5.4 Save Probability Estimate

Write `.claudshi/events/<event_slug>/markets/<ticker>/probability.yaml`:
```python
probability_data = {
    "ticker": ticker,
    "current_estimate": {
        "yes_probability": <YOUR_ESTIMATE>,
        "confidence": "<low/medium/high>",
        "updated_at": now_iso,
        "reasoning": "<one-sentence summary>",
    },
    "history": [
        {
            "timestamp": now_iso,
            "yes_probability": <YOUR_ESTIMATE>,
            "market_price": <market_price as decimal 0-1>,
            "trigger": "initial analysis",
        }
    ],
}
write_yaml(get_market_dir(event_slug, ticker) / "probability.yaml", probability_data)
```

#### 5.5 Log the Action

Append to `.claudshi/events/<event_slug>/markets/<ticker>/actions_log.yaml`:
```python
action = {
    "timestamp": now_iso,
    "type": "analyze",
    "summary": "Initial deep analysis performed",
    "details": f"See analysis/{today}-initial.md",
}
append_yaml_list(
    get_market_dir(event_slug, ticker) / "actions_log.yaml",
    "actions",
    action,
)
# Also ensure the ticker is set at the top level
import yaml
from pathlib import Path
log_path = get_market_dir(event_slug, ticker) / "actions_log.yaml"
log_data = yaml.safe_load(log_path.read_text()) or {}
log_data["ticker"] = ticker
write_yaml(log_path, log_data)
```

---

### Step 6: Present Summary

After saving all files, present a summary to the user. Use the formatting helpers:

```python
from formatting import format_analysis_summary, format_edge_display, format_probability
```

Display:
1. **Market title and ticker.**
2. **Key data:** last price, volume, expiration.
3. **Your probability estimate** and confidence level.
4. **Edge** vs. market price.
5. **Factor scores** (the table from your analysis).
6. **Recommendation** — one of:
   - **Trade**: there is sufficient edge. Show the recommended side (YES/NO), suggested bet size (from Kelly), and suggested price. Tell the user to run `/bet <ticker> <side> <amount>` to execute.
   - **Watch**: edge is close to threshold or confidence is low. Add to watchlist. Tell the user the market has been added to the watchlist and `/monitor` will track it.
   - **Pass**: no edge or market is unsuitable. Explain why.

If the recommendation is **Watch**, also add to the watchlist:
```python
from memory import load_watchlist, save_watchlist
watchlist = load_watchlist()
# Remove existing entry for this ticker if present
watchlist = [w for w in watchlist if w.get("ticker") != ticker]
watchlist.append({
    "ticker": ticker,
    "title": "<market title>",
    "event_slug": event_slug,
    "last_price_cents": <last_price>,
    "estimated_edge_pct": <edge>,
    "added_at": now_iso,
})
save_watchlist(watchlist)
```

---

## Important Notes

- **Never place trades from this skill.** Only recommend. The user must use `/bet` to execute.
- **Always save all memory files** before presenting the summary. If file writing fails, report the error.
- **Be calibrated.** Avoid overconfidence. Use base rates. Assign confidence levels honestly.
- **Show your work.** Every probability comes with structured reasoning.
- **Cite sources.** List the news articles and data you consulted.
