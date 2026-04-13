---
name: cs_scan
description: Scan political prediction markets for mispriced opportunities. Fetches events, estimates probabilities, and ranks by edge.
disable-model-invocation: true
argument-hint: "[category]"
allowed-tools: Read Write Bash WebSearch WebFetch mcp__kalshi-mcp__get_events mcp__kalshi-mcp__get_event mcp__kalshi-mcp__get_markets mcp__kalshi-mcp__get_market mcp__kalshi-mcp__get_market_orderbook mcp__kalshi-mcp__get_trades
---

# /cs_scan — Scan for Mispriced Political Markets

## Usage

```
/cs_scan                  # Scan all default categories
/cs_scan <category>       # Scan a specific category (e.g. politics, elections)
```

## Instructions

The user's arguments: $ARGUMENTS

When the user invokes `/cs_scan`, follow **every** step below in order. Do not skip steps.

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

### Step 2: Fetch Events (Without Nested Markets)

**IMPORTANT: Never call `get_events` with `with_nested_markets=true`.** That returns megabytes of data and will exceed output limits.

Call **`get_events`** with:
- `status`: `open`
- `with_nested_markets`: **false** (or omit — default is false)
- `limit`: `200`

This returns lightweight event metadata only (~50KB instead of ~2.5MB).

#### Kalshi API categories

The Kalshi API uses these category names (capitalized): `Politics`, `Elections`, `Economics`, `World`. These map to our config categories as follows:
- `politics` → Kalshi `Politics`
- `elections` → Kalshi `Elections`
- `geopolitics` → Kalshi `Politics` and `World`
- `legislation` → Kalshi `Politics`

Filter the events list client-side by matching the event's `category` field against the target Kalshi categories. For the default config, keep events where `category` is `Politics`, `Elections`, or `World`.

---

### Step 3: Fetch Markets for Political Events

Now fetch markets for each political event. To stay within the ~50 market budget:

1. **Group events by interest.** Pick up to 15 of the most interesting-looking political events (use your judgment based on event titles — prefer current/timely topics over far-future ones).

2. **For each selected event**, call **`get_markets`** with `event_ticker=<ticker>`. Do NOT use `get_event` with `with_nested_markets=true` if the event has many markets (e.g. "2028 Presidential Election" has 25+ markets).

   **IMPORTANT:** The `get_markets` API does **NOT** accept `status` as a filter parameter. Passing `status=active` will return a **400 Bad Request** error. Fetch all markets for the event and filter client-side.

3. **Filter markets** client-side to keep only those that are:
   - **Active**: `status` is `active`.
   - **Liquid**: `volume_fp` (parsed as float) > 0 **and** both `yes_bid_dollars` and `yes_ask_dollars` are > "0.0000".
   - **Not too cheap/expensive**: `last_price_dollars` is between "0.03" and "0.97" (markets at extreme prices have little edge opportunity).

4. **Cap at 50 candidates total** sorted by volume (highest first). For multi-market events (like "2028 Presidential Election"), pick only the top 3–5 markets by volume to avoid flooding the list with one event.

#### Kalshi API field reference

Market objects use these field names:
- `ticker` — market ticker string
- `title` — market title
- `event_ticker` — parent event ticker
- `status` — one of: `active`, `inactive`, `finalized`
- `last_price_dollars` — last trade price as string, e.g. `"0.2700"` (this is a dollar amount, not cents)
- `yes_bid_dollars` — best YES bid as string, e.g. `"0.2600"`
- `yes_ask_dollars` — best YES ask as string, e.g. `"0.2700"`
- `no_bid_dollars` / `no_ask_dollars` — best NO bid/ask
- `volume_fp` — total volume as string, e.g. `"352983.55"`
- `volume_24h_fp` — 24h volume as string
- `open_interest_fp` — open interest as string
- `expiration_time` — ISO 8601 timestamp
- `rules_primary` — resolution rules text
- `yes_sub_title` — short label for the YES side

**Price conversion:** Market-implied YES probability = `float(last_price_dollars)` (already 0–1 scale). To convert to cents for the formatting helpers, use `int(float(last_price_dollars) * 100)`.

---

### Step 4: Rapid Assessment

For each candidate market, perform a lightweight assessment. This is intentionally faster and less thorough than a full `/cs_analyze` — the goal is to quickly identify markets worth a deeper look.

#### 4.1 Extract Market Data

From the market objects collected in Step 3, extract:
- `ticker`
- `title`
- `last_price_dollars` — parse as float, this IS the market-implied YES probability (0–1)
- `volume_fp` — parse as float
- `rules_primary` — helps understand exactly what resolves the market
- `expiration_time`

#### 4.2 Quick Web Search

Group candidate markets by topic and run **batched web searches** — one search per distinct topic, not per market. For example:
- "Trump Greenland acquisition 2026 latest" covers multiple Greenland markets
- "2028 presidential election polls frontrunners" covers all 2028 presidential markets
- "Trump impeachment removal 2026" covers both impeachment and resignation markets

Limit to **4–6 web searches total**. Scan the search result snippets — you do NOT need to read full articles.

#### 4.3 Fast Probability Estimate

For each candidate, make a quick probability estimate based on:
1. **Base rate**: What is the typical probability for this type of event? (e.g., "Will X happen by date Y" — consider how often similar events resolve YES.)
2. **Resolution rules**: Read `rules_primary` carefully — the exact resolution criteria matter. "Purchase" vs "acquire any part" vs "take control" are very different bars.
3. **Headline adjustment**: Based on the news snippets, does the situation look more or less likely than the base rate?
4. **Assign a rough probability** — this does not need the full factor analysis. It is a fast estimate.

#### 4.4 Calculate Edge

```
market_probability = float(last_price_dollars)  # already 0-1
edge = claude_probability - market_probability
```

Flag markets where `abs(edge) >= min_edge_pct / 100` (from config, default 10% = 0.10).

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
    "event_slug": "<event_ticker>",
    "last_price_cents": int(float(last_price_dollars) * 100),  # convert to cents for formatter
    "volume": int(float(volume_fp)),
    "claude_probability": <your_estimate>,        # float 0-1
    "market_probability": float(last_price_dollars),  # float 0-1
    "edge_pct": <edge * 100>,                     # percentage points
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

Tell the user how many markets were added to the watchlist, and suggest using `/cs_analyze <ticker>` for a deep dive on the most promising ones.

---

### Step 7: Next Steps

After presenting results, suggest next actions:
- **For top opportunities**: "Run `/cs_analyze <ticker>` for a full analysis before trading."
- **For monitoring**: "Run `/cs_monitor` to track watchlisted markets."
- **For different categories**: "Run `/cs_scan <category>` to scan a specific category."

---

## Important Notes

- **Never use `with_nested_markets=true` on `get_events`.** It returns megabytes of data. Always fetch events without markets first, then fetch markets per-event using `get_markets(event_ticker=...)`.
- **Prices are in dollars, not cents.** Fields like `last_price_dollars`, `yes_bid_dollars` are dollar strings (e.g. `"0.27"` = 27%). Convert to cents (`* 100`) only when passing to formatting helpers.
- **Volume is a float string.** Parse `volume_fp` with `float()`, e.g. `"352983.55"` → `352983.55`.
- **Market status is `active`, not `open`.** Filter on `status == "active"` **client-side** — do NOT pass `status` as a parameter to `get_markets` (it causes a 400 error).
- **Cap at ~50 candidate markets.** Kalshi has ~500 active political markets, but most are low-volume or extreme-priced. The top 50 by volume cover the interesting ones.
- **This is a scan, not a full analysis.** Probability estimates here are rough. Always run `/cs_analyze` before trading.
- **Never place trades from this skill.** Only identify opportunities.
- **Be calibrated.** Even in quick estimates, use base rates and avoid overconfidence.
- **Save to watchlist.** Every flagged market gets added for tracking.
- **Keep it fast.** Limit to 4–6 web searches total and avoid deep research — that's what `/cs_analyze` is for.
- **Handle API errors gracefully.** If an event or market fetch fails, skip it and continue.
