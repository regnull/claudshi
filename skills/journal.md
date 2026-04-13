# /journal — View or Generate Daily Journal Entry

## Usage

```
/journal
/journal <YYYY-MM-DD>
```

- No arguments: generate today's journal entry summarizing positions, actions, and observations.
- With a date: display that day's existing journal entry.

## Instructions

When the user invokes `/journal`, follow **every** step below in order.

---

### Step 1: Parse Arguments

Determine the mode:

- **If a date argument is provided** (e.g., `2026-04-12`): go to **Step 2 (Read Mode)**.
- **If no arguments**: go to **Step 3 (Generate Mode)**.

Validate any date argument is in `YYYY-MM-DD` format. If invalid, display:

```
Invalid date format. Use `/journal YYYY-MM-DD` (e.g., `/journal 2026-04-12`).
```

And stop.

---

### Step 2: Read Mode — Display Existing Journal

Read the journal file from `.claudshi/journal/<YYYY-MM-DD>.md`:

```python
import sys; sys.path.insert(0, "lib")
from memory import read_md
from pathlib import Path

date_str = "<DATE_ARG>"
journal_path = Path(".claudshi/journal") / f"{date_str}.md"
content = read_md(journal_path)
```

If the file exists and has content, display it directly to the user.

If the file does not exist or is empty, display:

```
## Journal — <YYYY-MM-DD>

No journal entry found for this date.

Use `/journal` (no date) to generate today's entry.
```

**Stop here.** Do not proceed to Step 3.

---

### Step 3: Generate Mode — Build Today's Journal

Generate a comprehensive journal entry for today. This requires gathering data from multiple sources.

#### 3.1 Get Current Date

```python
from datetime import datetime, timezone

now = datetime.now(timezone.utc)
today = now.strftime("%Y-%m-%d")
now_iso = now.strftime("%Y-%m-%dT%H:%M:%SZ")
```

#### 3.2 Fetch Live Portfolio Data

Call these MCP tools in parallel:

1. **`get_balance`** — current account balance and portfolio value.
2. **`get_positions`** — all open positions on Kalshi.

For each open position, call **`get_market`** to get the current market price.

Calculate per-position:
- `cost_cents`: total cost basis
- `current_value_cents`: current value at market price
- `unrealized_pnl_cents`: current value minus cost

Calculate totals:
- Total invested, total current value, total unrealized P&L
- Cash available, portfolio value

#### 3.3 Gather Today's Actions from Memory

Scan all `actions_log.yaml` files in `.claudshi/events/*/markets/*/` for actions with today's date:

```python
from memory import read_yaml
from pathlib import Path

root = Path(".claudshi/events")
todays_actions = []
if root.exists():
    for log_file in root.glob("*/markets/*/actions_log.yaml"):
        data = read_yaml(log_file)
        for action in data.get("actions", []):
            ts = action.get("timestamp", "")
            if ts.startswith(today):
                ticker = log_file.parent.name
                event_slug = log_file.parent.parent.parent.name
                todays_actions.append({
                    "ticker": ticker,
                    "event_slug": event_slug,
                    **action,
                })
```

Sort actions by timestamp.

#### 3.4 Load Current Positions from Memory

Scan `.claudshi/events/*/markets/*/position.yaml` for files where `quantity > 0`. For each, load:

- `position.yaml` — position details
- `market.yaml` — market metadata
- `probability.yaml` — our probability estimate

```python
from memory import read_yaml
from pathlib import Path

root = Path(".claudshi/events")
local_positions = []
if root.exists():
    for pos_file in root.glob("*/markets/*/position.yaml"):
        pos = read_yaml(pos_file)
        if pos.get("quantity", 0) > 0:
            market_dir = pos_file.parent
            event_dir = market_dir.parent.parent
            local_positions.append({
                "ticker": market_dir.name,
                "event_slug": event_dir.name,
                "position": pos,
                "market": read_yaml(market_dir / "market.yaml"),
                "probability": read_yaml(market_dir / "probability.yaml"),
            })
```

#### 3.5 Load Watchlist

```python
from memory import load_watchlist
watchlist = load_watchlist()
```

#### 3.6 Check for Market Movements

For each positioned market, compare the current live price (from Step 3.2) to the last recorded price in `market.yaml`. Flag significant moves (>5 cents).

#### 3.7 Search for News

Do a brief web search for each positioned market to note any relevant developments:

```
WebSearch: "<event/market title> latest news <current year>"
```

Keep this lightweight — one search per positioned market. Skip watchlist markets unless there are few positions.

---

### Step 4: Compose the Journal Entry

Build the journal markdown using this template:

```markdown
# Daily Journal — <YYYY-MM-DD>

## Portfolio Snapshot

- **Cash:** $<balance>
- **Portfolio Value:** $<portfolio_value>
- **Total Invested:** $<total_invested>
- **Unrealized P&L:** $<total_pnl> (<+/- X.X%>)
- **Number of Positions:** <N>

## Current Positions

### <Ticker>: <Market Title>
- **Position:** <YES/NO> x<quantity> @ $<avg_price>
- **Current Price:** $<current_price>
- **Unrealized P&L:** $<pnl>
- **Our Estimate:** <probability>% (confidence: <level>)
- **Edge:** <edge>%
- **Notes:** <any market-specific observations>

### <Ticker 2>: ...
(repeat for each position)

## Actions Taken Today

- **<HH:MM UTC>** — <type> on <ticker>: <summary>
- **<HH:MM UTC>** — <type> on <ticker>: <summary>
(list all actions from Step 3.3, or "No actions taken today." if none)

## Market Movements

- **<Ticker>**: moved from $<old_price> to $<new_price> (<+/- N> cents)
(list significant moves, or "No significant market movements today." if none)

## News & Developments

- **<Ticker>**: <brief news summary>
(list relevant news, or "No notable developments today." if none)

## Watchlist Summary

<N> markets on watchlist. Notable:
- **<Ticker>**: <title> — current price $<price>
(brief watchlist overview, or "Watchlist is empty." if none)

## Observations & Lessons

- <any patterns noticed, calibration notes, strategy reflections>
- <what went well, what could improve>
(thoughtful observations based on the day's activity; if quiet day, note that)

---
*Generated by Claudshi /journal at <timestamp>*
```

**Guidelines for composing the journal:**

- **Be concise but complete.** Each section should have enough detail to be useful when reviewed later.
- **Focus on what matters.** Highlight significant moves, new positions, and noteworthy news.
- **Be honest.** If nothing happened, say so. Don't fabricate activity.
- **Add genuine observations.** The "Observations & Lessons" section should contain actual reflections, not boilerplate. Consider: Are our probability estimates tracking well? Any systematic biases? Market behavior patterns?
- **If it's a quiet day**, the journal can be short. That's fine.

---

### Step 5: Save the Journal Entry

Save to `.claudshi/journal/<YYYY-MM-DD>.md`:

```python
from memory import write_md, ensure_dirs
from pathlib import Path

ensure_dirs()
journal_dir = Path(".claudshi/journal")
journal_dir.mkdir(parents=True, exist_ok=True)
journal_path = journal_dir / f"{today}.md"

# If a journal entry already exists for today (e.g., from /monitor), append
existing = ""
if journal_path.exists():
    existing = journal_path.read_text()
if existing.strip():
    # Append a separator and the new entry
    full_content = existing + "\n\n---\n\n" + journal_content
else:
    full_content = journal_content

write_md(journal_path, full_content)
```

---

### Step 6: Display the Journal

Display the full journal entry to the user.

After the journal, add a footer:

```
---
*Journal saved to `.claudshi/journal/<YYYY-MM-DD>.md`*
```

---

## Output Format

The full output should follow this structure:

**For Read Mode (date argument):**
```
<contents of the journal file>

---
*Showing journal entry for <YYYY-MM-DD>*
```

**For Generate Mode (no arguments):**
```
<generated journal content>

---
*Journal saved to `.claudshi/journal/<YYYY-MM-DD>.md`*
```

## Important Notes

- **Always fetch live data when generating.** Use Kalshi MCP tools for current balances and prices, not just local memory.
- **Handle empty state gracefully.** If there are no positions, no actions, and no watchlist, still generate a minimal journal noting the portfolio state.
- **Append, don't overwrite.** If a journal entry already exists for today (e.g., from `/monitor`), append the new content below a separator.
- **All monetary values in memory are in USD cents (integers).** Display values use `$X.XX` format.
- **Timestamps in ISO 8601.** Use UTC throughout.
- **The journal is for future reference.** Write it so that re-reading it weeks later provides full context about what happened that day.
