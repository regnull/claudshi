# Claudshi — Political Event Prediction Plugin for Claude

Claudshi is a Claude Code plugin that predicts political events using Kalshi prediction markets. It connects to Kalshi via the `kalshi-mcp` MCP server to read market data, analyze political events, generate probability estimates, place bets on mispriced markets, and perform ongoing monitoring of open contracts.

See `docs/PROMPT.md` for the full specification, architecture, and task definitions.

## Before Starting Any Work

**Always read `docs/TASKS.yaml` first.** Find the next pending task whose dependencies are all completed, and work on that task only. Update `TASKS.yaml` as you go.

## Available Slash Commands

| Command | Description |
|---------|-------------|
| `/cs_config [key value \| reset]` | View or update plugin settings |
| `/cs_analyze <market-url-or-ticker>` | Deep analysis of a political market |
| `/cs_scan [category]` | Scan for mispriced political markets |
| `/cs_bet <ticker> <side> <amount> [price]` | Place a trade (requires prior analysis) |
| `/cs_portfolio` | View current portfolio and P&L |
| `/cs_monitor` | Check all tracked markets for updates |
| `/cs_exit <ticker> [amount]` | Close or reduce a position |
| `/cs_journal [date]` | View or generate daily journal entry |

## Memory System (`.claudshi/`)

All persistent state lives in the `.claudshi/` directory. This is how Claude maintains context across sessions.

```
.claudshi/
  config.yaml                    # Global settings (risk limits, default stake, etc.)
  portfolio/
    summary.yaml                 # Aggregate portfolio: total invested, P&L, exposure
    balance_log.csv              # Timestamped balance snapshots
  events/
    <event-slug>/
      event.yaml                 # Event metadata
      markets/
        <market-ticker>/
          market.yaml            # Market details
          analysis/
            <YYYY-MM-DD>-initial.md    # First deep analysis
            <YYYY-MM-DD>-update-NN.md  # Subsequent updates
          probability.yaml       # Current model probability + history
          orderbook_snapshots/
            <timestamp>.yaml     # Periodic orderbook captures
          trades.yaml            # Our executed trades
          position.yaml          # Current position
          actions_log.yaml       # Chronological action log
  watchlist.yaml                 # Markets being monitored but not yet traded
  journal/
    <YYYY-MM-DD>.md              # Daily journal entries
```

**File conventions:**
- `.yaml` for structured data (machine-read/write, human-readable)
- `.md` for free-form analysis and reasoning
- Timestamps in ISO 8601 (`2025-07-04T14:30:00Z`)
- All monetary values in USD cents (integers)

## MCP Server Dependency

This plugin requires the `kalshi-mcp` MCP server to be configured and running. See `.mcp.json` for configuration. The server provides market data, portfolio, and trading tools. See `docs/PROMPT.md` for the full list of available MCP tools.

## Python Utilities

- `lib/memory.py` — helpers for reading/writing the `.claudshi/` memory tree
- `lib/risk.py` — risk checking and position sizing logic
- `lib/formatting.py` — output formatting for tables, summaries, reports
