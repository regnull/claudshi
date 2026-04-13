# Claudshi — Political Event Prediction Plugin for Claude

## Overview

Build a Claude Code plugin (slash-command skill set) that predicts political events using Kalshi prediction markets. The plugin connects to Kalshi via the [kalshi-mcp](https://github.com/regnull/kalshi-mcp) MCP server to read market data, analyze political events, generate probability estimates, place bets on mispriced markets, and perform ongoing monitoring and maintenance of open contracts.

The plugin's name is **Claudshi** (Claude + Kalshi).

## How to Use This Prompt

This project is built **one task at a time**. Each task is a self-contained unit of work with clear inputs, outputs, and acceptance criteria.

### Task Status File

All task progress is tracked in `docs/TASKS.yaml`. Before starting any work, read this file to find the next pending task. After completing a task, update its status. The file format:

```yaml
# docs/TASKS.yaml
project: claudshi
last_updated: "2025-07-04T14:30:00Z"
current_task: 3  # ID of the task currently in progress (null if none)

tasks:
  - id: 1
    name: "Project scaffolding"
    status: completed        # pending | in_progress | completed | blocked
    completed_at: "2025-07-03T10:00:00Z"
    notes: ""
  - id: 2
    name: "Memory system"
    status: in_progress
    started_at: "2025-07-04T09:00:00Z"
    notes: ""
  - id: 3
    name: "Config skill"
    status: pending
    depends_on: [2]          # Cannot start until these tasks are completed
    notes: ""
```

### Workflow

1. Read `docs/TASKS.yaml`.
2. Find the next task: the lowest-ID task with `status: pending` whose `depends_on` are all `completed`.
3. Read the task's full specification in this document (search by task ID).
4. Set the task to `in_progress` in `TASKS.yaml`, set `current_task`.
5. Implement the task according to its specification and acceptance criteria.
6. Verify all acceptance criteria are met.
7. Set the task to `completed` in `TASKS.yaml`, set `completed_at`, clear `current_task`.
8. Stop. Wait for the next invocation to pick up the next task.

**Important:** Do exactly one task per invocation. Do not skip ahead or combine tasks.

---

## Reference: Architecture

These sections define the architecture of the complete system. Individual tasks reference these sections — read them as needed.

### MCP Server Dependency

The plugin relies on the `kalshi-mcp` MCP server, which exposes the following tools:

**Market Data:**
- `get_events` — list events with filtering and pagination
- `get_event` — detailed event info with nested markets
- `get_markets` / `get_market` — market listing and details
- `get_market_orderbook` — live order book (bid/ask depth)
- `get_trades` — recent trade history
- `get_market_candlesticks` — OHLCV price history
- `get_series` — series metadata
- `lookup_event` — event sources and settlement criteria
- `get_exchange_status` / `get_exchange_schedule` — exchange availability

**Portfolio & Trading:**
- `get_balance` — account balance and portfolio value
- `get_positions` — open positions
- `get_orders` — order history
- `create_order` — place limit or market orders (YES/NO, buy/sell)
- `cancel_order` — cancel a pending order
- `get_fills` — trade execution history
- `get_settlements` — settlement history

### File-Based Memory System

All state lives in a local directory tree (default: `.claudshi/` in the project root). This is the plugin's persistent memory — it stores everything about tracked events, analyses, contracts, and actions taken. The memory system must be designed so that Claude can read past context and resume work across sessions.

```
.claudshi/
  config.yaml                    # Global settings (risk limits, default stake, etc.)
  portfolio/
    summary.yaml                 # Aggregate portfolio: total invested, P&L, exposure
    balance_log.csv              # Timestamped balance snapshots
  events/
    <event-slug>/
      event.yaml                 # Event metadata (title, category, expiration, resolution criteria)
      markets/
        <market-ticker>/
          market.yaml            # Market details (ticker, title, outcomes, expiration, settlement source)
          analysis/
            <YYYY-MM-DD>-initial.md    # First deep analysis
            <YYYY-MM-DD>-update-NN.md  # Subsequent analysis updates
          probability.yaml       # Current model probability + history of adjustments
          orderbook_snapshots/
            <timestamp>.yaml     # Periodic orderbook captures for trend analysis
          trades.yaml            # Our executed trades (fills) for this market
          position.yaml          # Current position (side, quantity, avg price, P&L)
          actions_log.yaml       # Chronological log of every action taken (analyze, bet, adjust, exit)
  watchlist.yaml                 # Markets being monitored but not yet traded
  journal/
    <YYYY-MM-DD>.md              # Daily journal: what happened, decisions made, lessons learned
```

**File format conventions:**
- `.yaml` for structured data (machine-read/write, human-readable)
- `.md` for free-form analysis and reasoning (Claude-native format)
- Timestamps in ISO 8601 (`2025-07-04T14:30:00Z`)
- All monetary values in USD cents (integers) to avoid floating-point issues

### Analysis Framework

When Claude analyzes a political event, it must follow this structured reasoning framework:

**1. Event Decomposition**
- What exactly needs to happen for YES to resolve?
- What is the time window?
- Are there intermediate milestones we can track?

**2. Base Rate Analysis**
- How often do events of this type resolve YES historically?
- What is the prior probability before considering current circumstances?

**3. Factor Analysis**
Rate each factor on a -5 to +5 scale (negative = favors NO, positive = favors YES):
- **Political will**: Do key decision-makers want this outcome?
- **Institutional feasibility**: Can the mechanism deliver this outcome in time?
- **Public pressure**: Is public opinion pushing toward this outcome?
- **External forces**: Are international/economic/military factors at play?
- **Precedent**: How does this compare to historical analogs?
- **Momentum**: Is the situation trending toward or away from this outcome?

**4. Probability Synthesis**
- Start from base rate.
- Adjust for each factor.
- Apply calibration: avoid extreme probabilities (rarely below 5% or above 95%) unless resolution is near-certain.
- Assign a confidence level (low/medium/high) based on information quality.

**5. Edge Calculation**
```
edge = claude_probability - market_probability
if abs(edge) >= min_edge_pct:
    recommend trade on the side where claude_probability > market_probability
```

**6. Kelly Criterion (Modified)**
For position sizing, use a fractional Kelly criterion:
```
kelly_fraction = (edge * (1 - market_probability)) / (1 - edge)
bet_size = kelly_fraction * bankroll * 0.25  # quarter-Kelly for safety
bet_size = min(bet_size, max_single_bet_usd)
```

### Risk Management Rules

These rules are enforced by the plugin and cannot be overridden without changing `config.yaml`:

1. **No single bet exceeds `max_single_bet_usd`.**
2. **No single market position exceeds `max_position_usd`.**
3. **Total portfolio exposure never exceeds `max_portfolio_exposure_usd`.**
4. **Never trade on markets expiring within 1 hour** (liquidity risk).
5. **Always require user confirmation before placing any order.**
6. **Log every action** — no silent trades or unrecorded decisions.
7. **Quarter-Kelly sizing** — never full Kelly, to protect against estimation error.
8. **Diversification**: warn if more than 40% of portfolio is in a single event.

### Key Design Principles

1. **Memory is everything.** Every analysis, decision, and trade must be recorded. Claude should be able to pick up any market from cold start by reading the memory files.
2. **Human in the loop.** Claude recommends, the user decides. No order is placed without explicit user confirmation.
3. **Show your work.** Every probability estimate comes with structured reasoning. Every recommendation explains the edge and the risks.
4. **Calibration over conviction.** Use base rates, factor analysis, and historical data. Avoid overconfidence. Assign confidence levels honestly.
5. **Incremental updates.** Don't redo full analysis every time. Build on previous analysis, note what changed, and adjust accordingly.
6. **Risk-first.** Check risk limits before every trade. Warn about concentration. Size positions conservatively.

### Data Format Reference

**Probability file (`probability.yaml`):**
```yaml
ticker: "KXUSAIRANAGREEMENT-27"
current_estimate:
  yes_probability: 0.35
  confidence: "medium"
  updated_at: "2025-07-04T14:30:00Z"
  reasoning: "Brief summary of why this probability"
history:
  - timestamp: "2025-07-01T10:00:00Z"
    yes_probability: 0.30
    market_price: 0.25
    trigger: "initial analysis"
  - timestamp: "2025-07-04T14:30:00Z"
    yes_probability: 0.35
    market_price: 0.28
    trigger: "news update — diplomatic talks resumed"
```

**Actions log (`actions_log.yaml`):**
```yaml
ticker: "KXUSAIRANAGREEMENT-27"
actions:
  - timestamp: "2025-07-01T10:00:00Z"
    type: "analyze"
    summary: "Initial deep analysis performed"
    details: "See analysis/2025-07-01-initial.md"
  - timestamp: "2025-07-01T10:15:00Z"
    type: "bet"
    side: "YES"
    quantity: 50
    price: 25
    order_type: "limit"
    order_id: "abc-123"
    status: "filled"
  - timestamp: "2025-07-04T14:30:00Z"
    type: "update"
    summary: "Probability adjusted from 0.30 to 0.35 after diplomatic talks resumed"
  - timestamp: "2025-07-04T14:45:00Z"
    type: "bet"
    side: "YES"
    quantity: 25
    price: 28
    order_type: "market"
    order_id: "def-456"
    status: "filled"
```

---

## Tasks

### Task 1: Project Scaffolding

**Depends on:** (none)

**Goal:** Create the project directory structure, CLAUDE.md, MCP configuration, and the initial TASKS.yaml file.

**Work:**
1. Create the project directory layout:
   ```
   claudshi/
     skills/           # (empty, skills added in later tasks)
     lib/              # (empty, code added in later tasks)
     .claudshi/        # Memory root (empty, populated at runtime)
     docs/
       PROMPT.md       # This file (already exists)
       TASKS.yaml      # Task tracker
     CLAUDE.md         # Project-level Claude instructions
     .mcp.json         # MCP server configuration for kalshi-mcp
   ```
2. Write `CLAUDE.md` with:
   - Project description (one paragraph).
   - Pointer to `docs/PROMPT.md` for full specification.
   - Instructions for Claude to read `docs/TASKS.yaml` before starting any work.
   - List of available slash commands (to be populated as skills are built — start with a placeholder list).
   - Description of the `.claudshi/` memory system and how to read/write it.
3. Write `.mcp.json` with the kalshi-mcp server configuration (use placeholder values for API key and private key path).
4. Create `docs/TASKS.yaml` with all tasks from this document, all set to `pending` except Task 1 which should be `completed`.

**Acceptance criteria:**
- All directories exist.
- `CLAUDE.md` is present and contains the information above.
- `.mcp.json` is valid JSON with kalshi-mcp configuration.
- `docs/TASKS.yaml` exists and lists all tasks with correct dependencies.

---

### Task 2: Memory System Helpers

**Depends on:** [1]

**Goal:** Build Python utility functions for reading and writing the `.claudshi/` memory tree.

**Work:**
1. Create `lib/memory.py` with functions for:
   - `ensure_dirs()` — create the `.claudshi/` directory tree if it doesn't exist.
   - `read_yaml(path)` → dict — read a YAML file, return empty dict if missing.
   - `write_yaml(path, data)` — write a dict to a YAML file, creating parent dirs as needed.
   - `append_yaml_list(path, key, item)` — append an item to a list within a YAML file (for actions log, history, etc.).
   - `read_md(path)` → str — read a markdown file, return empty string if missing.
   - `write_md(path, content)` — write markdown, creating parent dirs.
   - `get_event_dir(event_slug)` → Path — return the path for an event directory.
   - `get_market_dir(event_slug, ticker)` → Path — return the path for a market directory.
   - `get_analysis_path(event_slug, ticker, date, update_num=None)` → Path — return the path for an analysis file.
   - `get_next_update_num(event_slug, ticker, date)` → int — scan existing updates and return the next number.
   - `load_config()` → dict — load `.claudshi/config.yaml`, returning defaults if missing.
   - `save_config(data)` — write config.
   - `load_watchlist()` → list — load `.claudshi/watchlist.yaml`.
   - `save_watchlist(data)` — write watchlist.
   - `load_portfolio_summary()` → dict — load portfolio summary.
   - `save_portfolio_summary(data)` — write portfolio summary.
   - `append_balance_log(timestamp, balance, portfolio_value)` — append a row to `balance_log.csv`.
2. Use `pathlib.Path` throughout. The root directory (`.claudshi/`) should be configurable but default to `.claudshi/` relative to the project root.
3. Add a `pyproject.toml` with the project metadata and dependencies (`pyyaml`).

**Acceptance criteria:**
- `lib/memory.py` exists and contains all listed functions.
- Each function has a clear docstring.
- `pyproject.toml` exists with `pyyaml` dependency.
- Unit tests in `tests/test_memory.py` cover: creating dirs, round-tripping YAML, appending to lists, path generation, CSV append. All tests pass.

---

### Task 3: Risk Management Module

**Depends on:** [2]

**Goal:** Build the risk checking and position sizing logic.

**Work:**
1. Create `lib/risk.py` with:
   - `load_risk_config()` → dict — load risk parameters from config, with defaults:
     - `max_single_bet_usd`: 50
     - `max_position_usd`: 200
     - `max_portfolio_exposure_usd`: 1000
     - `min_edge_pct`: 10
     - `confidence_threshold`: 0.6
     - `max_concentration_pct`: 40
   - `check_bet(amount_usd, ticker, portfolio_summary, config)` → `(allowed: bool, reasons: list[str])` — validate a proposed bet against all risk rules.
   - `check_market_expiry(expiration_time)` → `(allowed: bool, reason: str)` — reject if market expires within 1 hour.
   - `check_concentration(event_slug, new_amount, portfolio_summary, config)` → `(allowed: bool, reason: str)` — warn if >40% in one event.
   - `calculate_position_size(edge, market_probability, bankroll, config)` → `float` — quarter-Kelly sizing, capped by `max_single_bet_usd`.
   - `calculate_edge(claude_probability, market_probability)` → `float` — simple edge calculation.
   - `format_risk_report(checks)` → `str` — human-readable summary of risk check results.

**Acceptance criteria:**
- `lib/risk.py` exists and contains all listed functions.
- Each function has a clear docstring.
- Unit tests in `tests/test_risk.py` cover: bet validation (pass and fail cases), expiry check, concentration check, Kelly sizing edge cases (zero edge, negative edge, large edge), edge calculation. All tests pass.

---

### Task 4: Output Formatting Module

**Depends on:** [2]

**Goal:** Build helpers for formatting tables, summaries, and reports as markdown (for Claude's output).

**Work:**
1. Create `lib/formatting.py` with:
   - `format_market_summary(market_data)` → `str` — one-line summary of a market (ticker, title, last price, volume).
   - `format_market_detail(market_data, orderbook, probability)` → `str` — detailed market view with orderbook depth, price history context, and our probability estimate.
   - `format_portfolio_table(positions, balances)` → `str` — markdown table of all positions with P&L.
   - `format_trade_confirmation(order_details, risk_checks, portfolio_impact)` → `str` — pre-trade confirmation prompt showing all details.
   - `format_analysis_summary(analysis)` → `str` — condensed version of a full analysis for quick display.
   - `format_watchlist(watchlist)` → `str` — markdown table of watched markets.
   - `format_scan_results(results)` → `str` — ranked table of scan findings with estimated edge.
   - `format_edge_display(claude_prob, market_prob)` → `str` — colored/formatted edge indicator.
   - `usd_cents_to_display(cents)` → `str` — convert cents to "$X.XX" string.
   - `format_probability(prob)` → `str` — format as percentage with appropriate precision.

**Acceptance criteria:**
- `lib/formatting.py` exists and contains all listed functions.
- Each function has a clear docstring.
- Unit tests in `tests/test_formatting.py` cover representative inputs. All tests pass.

---

### Task 5: `/config` Skill

**Depends on:** [2]

**Goal:** Implement the `/config` slash command skill.

**Work:**
1. Create `skills/config.md` — the skill prompt that Claude follows when the user invokes `/config`.
2. The skill must:
   - If invoked with no arguments: display all current settings from `.claudshi/config.yaml` (or defaults if file doesn't exist).
   - If invoked with `<key> <value>`: update that setting and save.
   - If invoked with `reset`: restore all defaults and save.
   - Show defaults alongside current values so the user can see what changed.
3. The supported settings are:
   - `max_single_bet_usd` (default: 50)
   - `max_position_usd` (default: 200)
   - `max_portfolio_exposure_usd` (default: 1000)
   - `min_edge_pct` (default: 10)
   - `confidence_threshold` (default: 0.6)
   - `monitor_interval_hours` (default: 12)
   - `categories` (default: `[politics, geopolitics, elections, legislation]`)
4. Register the skill in `CLAUDE.md` (add it to the slash command list).

**Acceptance criteria:**
- `skills/config.md` exists and contains clear instructions.
- Invoking `/config` shows settings. Invoking `/config max_single_bet_usd 100` updates the value. Invoking `/config reset` restores defaults.
- `CLAUDE.md` lists `/config` as an available command.

---

### Task 6: `/analyze` Skill

**Depends on:** [2, 3, 4]

**Goal:** Implement the `/analyze` slash command for deep political event analysis.

**Work:**
1. Create `skills/analyze.md` — the skill prompt for `/analyze <market-url-or-ticker>`.
2. The skill must instruct Claude to:
   - Parse the input (accept a full Kalshi URL or just a ticker).
   - Call `get_market` to fetch market data.
   - Call `get_event` to fetch parent event data.
   - Call `lookup_event` to get settlement/source info.
   - Call `get_market_orderbook` for current depth.
   - Call `get_trades` for recent trade history.
   - Call `get_market_candlesticks` for price history.
   - Use web search to research the political event (latest news, expert opinions, historical precedents, geopolitical context).
   - Perform the full Analysis Framework (see Reference section): event decomposition, base rate, factor analysis, probability synthesis, edge calculation, Kelly sizing.
   - Save the full analysis as `.claudshi/events/<slug>/markets/<ticker>/analysis/<date>-initial.md`.
   - Save market metadata to `market.yaml` and event metadata to `event.yaml`.
   - Save probability estimate to `probability.yaml`.
   - Log the action in `actions_log.yaml`.
   - Present a summary with recommendation: **Trade** (with suggested size), **Watch** (add to watchlist), or **Pass** (no edge).
3. Register in `CLAUDE.md`.

**Acceptance criteria:**
- `skills/analyze.md` exists with complete instructions covering all steps above.
- The skill references the Analysis Framework from the Reference section.
- The skill specifies exact file paths and formats for all saved output.
- `CLAUDE.md` lists `/analyze`.

---

### Task 7: `/scan` Skill

**Depends on:** [2, 4]

**Goal:** Implement the `/scan` skill for finding mispriced political markets.

**Work:**
1. Create `skills/scan.md` — the skill prompt for `/scan [category]`.
2. The skill must instruct Claude to:
   - Call `get_events` with appropriate filters (category if provided, or default categories from config).
   - For each event, call `get_markets` to get market details.
   - Filter to active, liquid-enough markets.
   - For each candidate, do a rapid assessment:
     - Fetch basic market data (last price, volume, spread).
     - Do a quick web search for the event's latest news.
     - Make a fast probability estimate (lighter than full analysis — just base rate + headlines).
     - Calculate estimated edge.
   - Rank results by absolute edge (largest mispricing first).
   - Present a formatted table using `format_scan_results`.
   - Save flagged markets to `watchlist.yaml`.
3. Register in `CLAUDE.md`.

**Acceptance criteria:**
- `skills/scan.md` exists with complete instructions.
- The skill handles both category-filtered and unfiltered scans.
- Output is a ranked table. Watchlist is updated.
- `CLAUDE.md` lists `/scan`.

---

### Task 8: `/bet` Skill

**Depends on:** [2, 3, 4]

**Goal:** Implement the `/bet` skill for placing trades.

**Work:**
1. Create `skills/bet.md` — the skill prompt for `/bet <market-ticker> <side> <amount> [price]`.
2. The skill must instruct Claude to:
   - Parse and validate inputs (`side` = YES/NO, `amount` in USD, `price` optional).
   - Fetch current market data and orderbook.
   - Load our existing probability estimate for this market (error if no analysis exists — tell user to run `/analyze` first).
   - Run all risk checks (from `lib/risk.py` logic): max bet, max position, max exposure, expiry, concentration.
   - Present a trade confirmation using `format_trade_confirmation`:
     - Market title and current price.
     - Our probability estimate and edge.
     - Order details (type, side, quantity, estimated cost).
     - Risk check results.
     - Portfolio impact (new total exposure, concentration).
   - **Wait for explicit user confirmation** (this is critical — never auto-execute).
   - On confirmation, call `create_order`.
   - Poll `get_fills` to confirm execution.
   - Update: `trades.yaml`, `position.yaml`, `actions_log.yaml`, `portfolio/summary.yaml`.
3. Register in `CLAUDE.md`.

**Acceptance criteria:**
- `skills/bet.md` exists with complete instructions.
- The skill requires an existing analysis before allowing a bet.
- The skill enforces all risk rules and requires user confirmation.
- All memory files are updated on execution.
- `CLAUDE.md` lists `/bet`.

---

### Task 9: `/portfolio` Skill

**Depends on:** [2, 4]

**Goal:** Implement the `/portfolio` skill for viewing portfolio state.

**Work:**
1. Create `skills/portfolio.md` — the skill prompt for `/portfolio`.
2. The skill must instruct Claude to:
   - Call `get_balance` to get current account balance.
   - Call `get_positions` to get all open positions.
   - For each position, call `get_market` to get current market price.
   - Calculate for each position: cost basis, current value, unrealized P&L, weight in portfolio.
   - Calculate totals: total invested, total current value, total unrealized P&L, cash available.
   - Present using `format_portfolio_table`.
   - Update `portfolio/summary.yaml` and append to `balance_log.csv`.
3. Register in `CLAUDE.md`.

**Acceptance criteria:**
- `skills/portfolio.md` exists with complete instructions.
- Output shows per-position and aggregate data.
- Memory files are updated.
- `CLAUDE.md` lists `/portfolio`.

---

### Task 10: `/monitor` Skill

**Depends on:** [6, 9]

**Goal:** Implement the `/monitor` skill for ongoing contract maintenance.

**Work:**
1. Create `skills/monitor.md` — the skill prompt for `/monitor`.
2. The skill must instruct Claude to:
   - Scan `.claudshi/events/` for all tracked markets.
   - Load `watchlist.yaml` for watched-but-not-traded markets.
   - For each market (positions first, then watchlist):
     a. Fetch latest market data (price, orderbook, recent trades).
     b. Load our last probability estimate from `probability.yaml`.
     c. Search for latest news about the event.
     d. Assess if anything material has changed since last analysis.
   - For markets where something changed:
     a. Perform an updated analysis (lighter than full — focus on what changed).
     b. Write analysis update to `<date>-update-NN.md`.
     c. Update `probability.yaml` with new estimate and reasoning.
     d. Determine recommended action: **Hold**, **Add** (increase position), **Reduce** (partial exit), **Exit** (close position), **Enter** (new position from watchlist).
     e. Present recommendations to the user.
   - For markets where nothing changed, report "No change" briefly.
   - Write a daily journal entry summarizing all findings.
   - Save orderbook snapshots for trend tracking.
3. Register in `CLAUDE.md`.

**Acceptance criteria:**
- `skills/monitor.md` exists with complete instructions.
- The skill handles both positioned and watched markets.
- Analysis updates are incremental, not full re-analyses.
- Recommendations are actionable (with suggested order details for Add/Enter).
- Journal entry is generated.
- `CLAUDE.md` lists `/monitor`.

---

### Task 11: `/exit` Skill

**Depends on:** [8]

**Goal:** Implement the `/exit` skill for closing positions.

**Work:**
1. Create `skills/exit.md` — the skill prompt for `/exit <market-ticker> [amount]`.
2. The skill must instruct Claude to:
   - Load current position from memory (`position.yaml`).
   - Error if no position exists for this ticker.
   - Fetch current market data and orderbook.
   - Determine exit order: full close if no `amount`, partial if `amount` given.
   - Calculate realized P&L for the exit.
   - Present exit confirmation:
     - Current position details.
     - Exit order details.
     - Realized P&L.
     - Remaining position (if partial).
   - **Wait for user confirmation.**
   - On confirmation, call `create_order` (opposite side of current position).
   - Poll `get_fills` to confirm.
   - Update: `position.yaml`, `trades.yaml`, `actions_log.yaml`, `portfolio/summary.yaml`.
   - If full exit, note in `actions_log.yaml` that the position is closed.
3. Register in `CLAUDE.md`.

**Acceptance criteria:**
- `skills/exit.md` exists with complete instructions.
- Handles both full and partial exits.
- Requires user confirmation.
- All memory files are updated.
- `CLAUDE.md` lists `/exit`.

---

### Task 12: `/journal` Skill

**Depends on:** [2]

**Goal:** Implement the `/journal` skill for daily journal entries.

**Work:**
1. Create `skills/journal.md` — the skill prompt for `/journal [date]`.
2. The skill must instruct Claude to:
   - If a date is provided, read and display that day's journal from `.claudshi/journal/<YYYY-MM-DD>.md`.
   - If no date is provided, generate today's journal:
     - Summarize all current positions and their P&L.
     - Note any market movements since last journal.
     - List actions taken today (from `actions_log.yaml` files).
     - Note any news developments.
     - Record lessons learned or observations.
   - Save to `.claudshi/journal/<YYYY-MM-DD>.md`.
3. Register in `CLAUDE.md`.

**Acceptance criteria:**
- `skills/journal.md` exists with complete instructions.
- Reading existing journals works.
- Generated journals contain position summary, actions, and observations.
- `CLAUDE.md` lists `/journal`.

---

### Task 13: Integration Testing & Polish

**Depends on:** [5, 6, 7, 8, 9, 10, 11, 12]

**Goal:** End-to-end validation that all skills work together and the memory system stays consistent.

**Work:**
1. Review all skill `.md` files for consistency:
   - Do they all use the same file paths and formats?
   - Do they all reference the correct memory locations?
   - Are the instructions unambiguous?
2. Review `CLAUDE.md`:
   - Does it list all 8 skills with correct syntax?
   - Does it explain the memory system clearly?
   - Does it mention the MCP server dependency?
3. Create a `docs/USAGE.md` with:
   - Quick start guide (install kalshi-mcp, configure API keys, run first `/scan`).
   - Example workflow: scan → analyze → bet → monitor → exit.
   - Explanation of the memory directory and how to inspect it.
4. Verify all Python tests pass.
5. Verify `pyproject.toml` has all dependencies.

**Acceptance criteria:**
- All skill files are consistent in format and file path references.
- `CLAUDE.md` is complete and accurate.
- `docs/USAGE.md` exists with a clear getting-started guide.
- All tests pass.
- No orphaned references (every file path mentioned in skills exists in the memory system spec).

---

## Initial TASKS.yaml Content

When creating `docs/TASKS.yaml` in Task 1, use this content:

```yaml
project: claudshi
last_updated: null
current_task: null

tasks:
  - id: 1
    name: "Project scaffolding"
    status: pending
    depends_on: []
    started_at: null
    completed_at: null
    notes: ""
  - id: 2
    name: "Memory system helpers"
    status: pending
    depends_on: [1]
    started_at: null
    completed_at: null
    notes: ""
  - id: 3
    name: "Risk management module"
    status: pending
    depends_on: [2]
    started_at: null
    completed_at: null
    notes: ""
  - id: 4
    name: "Output formatting module"
    status: pending
    depends_on: [2]
    started_at: null
    completed_at: null
    notes: ""
  - id: 5
    name: "/config skill"
    status: pending
    depends_on: [2]
    started_at: null
    completed_at: null
    notes: ""
  - id: 6
    name: "/analyze skill"
    status: pending
    depends_on: [2, 3, 4]
    started_at: null
    completed_at: null
    notes: ""
  - id: 7
    name: "/scan skill"
    status: pending
    depends_on: [2, 4]
    started_at: null
    completed_at: null
    notes: ""
  - id: 8
    name: "/bet skill"
    status: pending
    depends_on: [2, 3, 4]
    started_at: null
    completed_at: null
    notes: ""
  - id: 9
    name: "/portfolio skill"
    status: pending
    depends_on: [2, 4]
    started_at: null
    completed_at: null
    notes: ""
  - id: 10
    name: "/monitor skill"
    status: pending
    depends_on: [6, 9]
    started_at: null
    completed_at: null
    notes: ""
  - id: 11
    name: "/exit skill"
    status: pending
    depends_on: [8]
    started_at: null
    completed_at: null
    notes: ""
  - id: 12
    name: "/journal skill"
    status: pending
    depends_on: [2]
    started_at: null
    completed_at: null
    notes: ""
  - id: 13
    name: "Integration testing & polish"
    status: pending
    depends_on: [5, 6, 7, 8, 9, 10, 11, 12]
    started_at: null
    completed_at: null
    notes: ""
```

## Dependency Graph

```
Task 1: Project scaffolding
  └─► Task 2: Memory system helpers
        ├─► Task 3: Risk management module
        │     ├─► Task 6: /analyze skill ◄─── Task 4
        │     └─► Task 8: /bet skill ◄─────── Task 4
        ├─► Task 4: Output formatting module
        │     ├─► Task 6: /analyze skill ◄─── Task 3
        │     ├─► Task 7: /scan skill
        │     ├─► Task 8: /bet skill ◄─────── Task 3
        │     └─► Task 9: /portfolio skill
        ├─► Task 5: /config skill
        └─► Task 12: /journal skill

Task 6 + Task 9 ─► Task 10: /monitor skill
Task 8 ──────────► Task 11: /exit skill

Tasks 5-12 ──────► Task 13: Integration testing & polish
```

Tasks 3, 4, 5, and 12 can run in parallel once Task 2 is complete.
Tasks 6, 7, 8, and 9 can run in parallel once their dependencies are met.
