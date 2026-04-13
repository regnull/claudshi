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
- `event_slug`: derive from the event ticker (lowercase, hyphenated).
- `market_probability`: the market-implied YES probability = `last_price / 100` (Kalshi prices are in cents 0–99).

---

### Step 3: Research the Event

Use **WebSearch** to research the political event. Perform 2–3 searches:

1. Search for the event title + "latest news" to find recent developments.
2. Search for the event title + "prediction" or "odds" to find expert opinions.
3. If relevant, search for historical precedents.

Gather: latest news, expert opinions, historical base rates, geopolitical context.

---

### Step 4: Perform Analysis Framework

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
- Apply calibration: avoid extreme probabilities (rarely below 5% or above 95%).
- Assign confidence: **low**, **medium**, or **high**.

#### 4.5 Edge Calculation
```
edge = claude_probability - market_probability
```
Tradeable edge exists if `abs(edge) >= min_edge_pct` (default 10%).

#### 4.6 Position Sizing (if edge exists)
Quarter-Kelly criterion, capped by `max_single_bet_usd`.

---

### Step 5: Save Analysis to Memory

Save the following files using `lib/memory.py` helpers:

| File | Path | Content |
|------|------|---------|
| Event metadata | `.claudshi/events/<slug>/event.yaml` | Event title, category, series, etc. |
| Market metadata | `.claudshi/events/<slug>/markets/<ticker>/market.yaml` | Ticker, title, expiration, last price, volume, etc. |
| Full analysis | `.claudshi/events/<slug>/markets/<ticker>/analysis/<date>-initial.md` | Complete analysis with all framework sections |
| Probability | `.claudshi/events/<slug>/markets/<ticker>/probability.yaml` | Current estimate + history |
| Action log | `.claudshi/events/<slug>/markets/<ticker>/actions_log.yaml` | "analyze" action entry |

---

### Step 6: Present Summary

Display:
1. Market title and ticker.
2. Key data: last price, volume, expiration.
3. Probability estimate and confidence.
4. Edge vs. market.
5. Factor scores.
6. **Recommendation**: Trade (with details), Watch (add to watchlist), or Pass (explain why).

---

## Important Notes

- **Never place trades from this skill.** Only recommend. User must use `/bet` to execute.
- **Always save all memory files** before presenting the summary.
- **Be calibrated.** Use base rates. Avoid overconfidence.
- **Show your work.** Structured reasoning for every estimate.
- **Cite sources.** List news articles and data consulted.
