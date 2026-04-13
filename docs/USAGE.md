# Claudshi Usage Guide

## Quick Start

### 1. Install the Kalshi MCP Server

Claudshi requires the [kalshi-mcp](https://github.com/regnull/kalshi-mcp) MCP server for market data and trading.

Install it following the instructions in the kalshi-mcp repository.

### 2. Configure API Credentials

Edit `.mcp.json` in the project root and replace the placeholder values with your Kalshi API credentials:

```json
{
  "mcpServers": {
    "kalshi-mcp": {
      "command": "kalshi-mcp",
      "env": {
        "KALSHI_API_KEY": "<your-kalshi-api-key>",
        "KALSHI_PRIVATE_KEY_PATH": "<path-to-your-private-key>"
      }
    }
  }
}
```

You can obtain API credentials from your [Kalshi account settings](https://kalshi.com/account/settings).

### 3. Verify Setup

Run `/config` to confirm the plugin loads correctly and displays default settings.

### 4. Find Your First Opportunity

Run `/scan` to scan political prediction markets for mispriced opportunities:

```
/scan              # Scan all default categories
/scan elections    # Scan a specific category
```

## Example Workflow

A typical session follows this flow: **scan** for opportunities, **analyze** promising markets, **bet** on mispriced ones, **monitor** positions over time, and **exit** when appropriate.

### Step 1: Scan for Opportunities

```
/scan
```

This fetches active political events from Kalshi, performs quick probability estimates, and ranks markets by estimated edge. Markets with sufficient edge are added to your watchlist.

### Step 2: Analyze a Promising Market

Pick a high-edge market from the scan results and run a deep analysis:

```
/analyze KXUSAIRANAGREEMENT-27
```

This performs a full structured analysis: event decomposition, base rate analysis, factor scoring, probability synthesis, and edge calculation. The result is saved to the memory system and includes a recommendation (Trade, Watch, or Pass).

### Step 3: Place a Bet

If the analysis recommends a trade, place a bet:

```
/bet KXUSAIRANAGREEMENT-27 YES 25
```

This validates the trade against risk limits, shows a confirmation prompt with full details (edge, risk checks, portfolio impact), and waits for your explicit approval before executing.

You can also specify a limit price:

```
/bet KXUSAIRANAGREEMENT-27 YES 25 28
```

### Step 4: Monitor Your Positions

Run the monitor periodically (recommended every 12 hours) to check for changes:

```
/monitor
```

This checks all your positions and watchlist markets for news, price changes, and material developments. It performs incremental analysis updates and recommends actions (Hold, Add, Reduce, Exit, Enter).

### Step 5: Exit a Position

When it's time to close a position:

```
/exit KXUSAIRANAGREEMENT-27          # Full exit
/exit KXUSAIRANAGREEMENT-27 10       # Partial exit (10 contracts)
```

### Other Useful Commands

```
/portfolio          # View all positions, P&L, and account balance
/journal            # Generate today's journal entry
/journal 2026-04-12 # Read a past journal entry
/config             # View current settings
/config max_single_bet_usd 100   # Change a setting
/config reset       # Restore all defaults
```

## Memory System

Claudshi persists all state in the `.claudshi/` directory. This allows Claude to maintain context across sessions.

```
.claudshi/
  config.yaml                    # Plugin settings (risk limits, categories, etc.)
  portfolio/
    summary.yaml                 # Aggregate portfolio data
    balance_log.csv              # Historical balance snapshots
  events/
    <event-slug>/
      event.yaml                 # Event metadata
      markets/
        <market-ticker>/
          market.yaml            # Market details
          analysis/
            <date>-initial.md    # Full analysis
            <date>-update-NN.md  # Incremental updates
          probability.yaml       # Probability estimates and history
          orderbook_snapshots/   # Periodic orderbook captures
          trades.yaml            # Trade execution log
          position.yaml          # Current position
          actions_log.yaml       # All actions taken
  watchlist.yaml                 # Markets being monitored
  journal/
    <YYYY-MM-DD>.md              # Daily journal entries
```

### Inspecting Memory Files

All memory files are human-readable. YAML files contain structured data, and Markdown files contain analysis and reasoning. You can inspect them directly:

```bash
# View current config
cat .claudshi/config.yaml

# Check your portfolio
cat .claudshi/portfolio/summary.yaml

# Read an analysis
cat .claudshi/events/kxusairanagreement/markets/KXUSAIRANAGREEMENT-27/analysis/2026-04-12-initial.md

# See probability history
cat .claudshi/events/kxusairanagreement/markets/KXUSAIRANAGREEMENT-27/probability.yaml

# View the watchlist
cat .claudshi/watchlist.yaml

# Read today's journal
cat .claudshi/journal/2026-04-12.md
```

### File Conventions

- **YAML** (`.yaml`): Structured data (configs, positions, logs)
- **Markdown** (`.md`): Free-form analysis and reasoning
- **CSV** (`.csv`): Historical time-series data (balance log)
- **Timestamps**: ISO 8601 format (`2026-04-12T14:30:00Z`)
- **Monetary values**: Stored as USD cents (integers) to avoid floating-point issues

## Risk Management

Claudshi enforces these risk rules on every trade:

1. No single bet exceeds `max_single_bet_usd` (default: $50)
2. No single market position exceeds `max_position_usd` (default: $200)
3. Total portfolio exposure never exceeds `max_portfolio_exposure_usd` (default: $1,000)
4. Never trades on markets expiring within 1 hour
5. Always requires user confirmation before placing any order
6. Uses quarter-Kelly position sizing for conservative risk management
7. Warns if more than 40% of portfolio is concentrated in a single event

All limits are configurable via `/config`.
