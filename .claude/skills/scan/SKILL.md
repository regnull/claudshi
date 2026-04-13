---
name: scan
description: Scan political prediction markets for mispriced opportunities. Fetches events, estimates probabilities, and ranks by edge.
disable-model-invocation: true
argument-hint: "[category]"
allowed-tools: Read Write Bash WebSearch WebFetch mcp__kalshi-mcp__get_events mcp__kalshi-mcp__get_event mcp__kalshi-mcp__get_markets mcp__kalshi-mcp__get_market mcp__kalshi-mcp__get_market_orderbook mcp__kalshi-mcp__get_trades
---

# /scan — Scan for Mispriced Political Markets

## Usage

```
/scan                  # Scan all default categories
/scan <category>       # Scan a specific category (e.g. politics, elections)
```

## Instructions

The user's arguments: $ARGUMENTS

When the user invokes `/scan`, follow **every** step below in order. Do not skip steps.

---

### Step 1: Load Configuration

Load the plugin configuration to get default categories and edge threshold:

```python
import sys; sys.path.insert(0, "lib")
from memory import load_config
config = load_config()
```

Determine the categories to scan:
- If the user provided a `<category>` argument, scan only that category.
- If no argument, scan all categories from `config["categories"]` (default: `[politics, geopolitics, elections, legislation]`).

---

### Step 2: Fetch Events

For each category, call **`get_events`** with:
- `status`: `open` (only active events)
- Appropriate filtering for the category if supported by the API, otherwise fetch broadly and filter client-side.
- Use pagination if needed — fetch up to 100 events total across all categories.

Collect all returned events into a single list, deduplicating by event ticker.

---

### Step 3: Fetch Markets for Each Event

For each event, call **`get_event`** (which returns nested markets) or **`get_markets`** filtered by event ticker.

Filter to keep only markets that are:
- **Active** (status is `open` or `active`).
- **Liquid enough**: volume > 0 and the market has both bids and asks (spread exists).
- **Not expiring too soon**: expiration is more than 1 hour away.

If there are many markets (more than 30), prioritize by volume (highest volume first) and cap at 30 candidates.

---

### Step 4: Rapid Assessment

For each candidate market, perform a lightweight assessment. This is intentionally faster and less thorough than a full `/analyze` — the goal is to quickly identify markets worth a deeper look.

#### 4.1 Fetch Market Data

For each candidate, you already have basic data from Step 3. Extract:
- `ticker`
- `title`
- `last_price` (cents) — the market-implied YES probability is `last_price / 100`
- `volume`
- `expiration_time`

#### 4.2 Quick Web Search

For each candidate (or batch of related candidates), do a **single** web search:
- Search for the event title + "latest" to get a headline-level understanding.
- You do NOT need to read full articles — just scan the search result snippets.

To keep the scan fast, you may batch-search related events or limit to the top 10–15 candidates by volume.

#### 4.3 Fast Probability Estimate

For each candidate, make a quick probability estimate based on:
1. **Base rate**: What is the typical probability for this type of event? (e.g., "Will X happen by date Y" — consider how often similar events resolve YES.)
2. **Headline adjustment**: Based on the news snippets, does the situation look more or less likely than the base rate?
3. **Assign a rough probability** — this does not need the full factor analysis. It is a fast estimate.

#### 4.4 Calculate Edge

```
market_probability = last_price / 100
edge = claude_probability - market_probability
```

Flag markets where `abs(edge) >= min_edge_pct` (from config, default 10%).

For flagged markets, determine the `recommended_side`:
- If `edge > 0`: recommend YES (Claude thinks it's more likely than the market).
- If `edge < 0`: recommend NO (Claude thinks it's less likely than the market).

---

### Step 5: Rank and Format Results

Sort flagged markets by `abs(edge)` descending (largest mispricing first).

Build the results list with these fields per market:
```python
{
    "ticker": "<ticker>",
    "title": "<market title>",
    "event_slug": "<event_slug>",
    "last_price_cents": <last_price>,
    "volume": <volume>,
    "claude_probability": <your_estimate>,
    "market_probability": <market_implied>,
    "edge_pct": <edge * 100>,
    "recommended_side": "<YES or NO>",
}
```

Present the results using the formatting helper:

```python
from formatting import format_scan_results
output = format_scan_results(results)
```

If no markets have sufficient edge, report: "No mispriced markets found in the scanned categories."

Also report scan metadata:
- Categories scanned
- Number of events checked
- Number of markets evaluated
- Number of opportunities found

---

### Step 6: Update Watchlist

Add all flagged markets to the watchlist (markets with `abs(edge) >= min_edge_pct`).

```python
from memory import load_watchlist, save_watchlist
from datetime import datetime, timezone

now_iso = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

watchlist = load_watchlist()

for result in flagged_results:
    # Remove existing entry for this ticker if present
    watchlist = [w for w in watchlist if w.get("ticker") != result["ticker"]]
    watchlist.append({
        "ticker": result["ticker"],
        "title": result["title"],
        "event_slug": result["event_slug"],
        "last_price_cents": result["last_price_cents"],
        "estimated_edge_pct": result["edge_pct"],
        "recommended_side": result["recommended_side"],
        "claude_probability": result["claude_probability"],
        "added_at": now_iso,
    })

save_watchlist(watchlist)
```

Tell the user how many markets were added to the watchlist, and suggest using `/analyze <ticker>` for a deep dive on the most promising ones.

---

### Step 7: Next Steps

After presenting results, suggest next actions:
- **For top opportunities**: "Run `/analyze <ticker>` for a full analysis before trading."
- **For monitoring**: "Run `/monitor` to track watchlisted markets."
- **For different categories**: "Run `/scan <category>` to scan a specific category."

---

## Important Notes

- **This is a scan, not a full analysis.** Probability estimates here are rough. Always run `/analyze` before trading.
- **Never place trades from this skill.** Only identify opportunities.
- **Be calibrated.** Even in quick estimates, use base rates and avoid overconfidence.
- **Save to watchlist.** Every flagged market gets added for tracking.
- **Keep it fast.** Limit web searches and avoid deep research — that's what `/analyze` is for.
- **Handle API errors gracefully.** If an event or market fetch fails, skip it and continue.
