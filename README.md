# Claudshi

A [Claude Code](https://docs.anthropic.com/en/docs/claude-code) plugin that predicts political events using [Kalshi](https://kalshi.com/) prediction markets.

Claudshi connects to Kalshi via the [kalshi-mcp](https://github.com/regnull/kalshi-mcp) MCP server to scan markets, analyze political events, estimate probabilities, place bets on mispriced markets, and monitor open positions.

## Requirements

- [Claude Code](https://docs.anthropic.com/en/docs/claude-code) CLI
- [kalshi-mcp](https://github.com/regnull/kalshi-mcp) MCP server
- A [Kalshi](https://kalshi.com/) account with API credentials
- Python 3.11+

## Setup

1. **Install kalshi-mcp:**

   ```bash
   pip install git+https://github.com/regnull/kalshi-mcp.git
   ```

2. **Configure API credentials** in `.mcp.json`:

   ```json
   {
     "mcpServers": {
       "kalshi-mcp": {
         "command": "kalshi-mcp",
         "args": [],
         "env": {
           "KALSHI_API_KEY": "<your-kalshi-api-key>",
           "KALSHI_PRIVATE_KEY_PATH": "<path-to-your-private-key>"
         }
       }
     }
   }
   ```

3. **Install Python dependencies:**

   ```bash
   pip install -e ".[dev]"
   ```

4. **Verify setup:**

   ```
   /config
   ```

## Commands

| Command | Description |
|---------|-------------|
| `/config [key value \| reset]` | View or update plugin settings |
| `/analyze <market-url-or-ticker>` | Deep analysis of a political market |
| `/scan [category]` | Scan for mispriced political markets |
| `/bet <ticker> <side> <amount> [price]` | Place a trade (requires prior analysis) |
| `/portfolio` | View current portfolio and P&L |
| `/monitor` | Check all tracked markets for updates |
| `/exit <ticker> [amount]` | Close or reduce a position |
| `/journal [date]` | View or generate daily journal entry |

## Typical Workflow

```
/scan                          # Find mispriced markets
/analyze KXSOMEMARKET-25       # Deep-dive a candidate
/bet KXSOMEMARKET-25 YES 25    # Place a trade (with confirmation)
/monitor                       # Check positions periodically
/exit KXSOMEMARKET-25          # Close when done
/journal                       # Record the day's activity
```

## How It Works

### Analysis Framework

When analyzing a market, Claudshi follows a structured reasoning process:

1. **Event decomposition** — What exactly needs to happen for YES to resolve?
2. **Base rate analysis** — How often do events like this happen historically?
3. **Factor analysis** — Score six factors from -5 to +5: political will, institutional feasibility, public pressure, external forces, precedent, momentum.
4. **Probability synthesis** — Combine base rate with factor adjustments.
5. **Edge calculation** — Compare Claude's estimate to the market price.
6. **Position sizing** — Quarter-Kelly criterion, capped by risk limits.

### Risk Management

Every trade is checked against configurable risk rules:

- **Max single bet:** $50 (default)
- **Max position per market:** $200 (default)
- **Max portfolio exposure:** $1,000 (default)
- **Minimum edge:** 10% (default)
- **No trading within 1 hour of expiration**
- **Concentration warning** at 40% of portfolio in one event
- **User confirmation required** before every order

### Persistent Memory

All state is stored in the `.claudshi/` directory so Claude can resume work across sessions:

```
.claudshi/
  config.yaml              # Settings
  portfolio/
    summary.yaml           # Aggregate portfolio data
    balance_log.csv        # Balance history
  events/
    <event-slug>/
      event.yaml           # Event metadata
      markets/
        <ticker>/
          market.yaml      # Market details
          analysis/        # Timestamped analysis files
          probability.yaml # Current probability estimate
          trades.yaml      # Executed trades
          position.yaml    # Current position
          actions_log.yaml # Action history
  watchlist.yaml           # Tracked markets
  journal/
    <YYYY-MM-DD>.md        # Daily journal entries
```

## Configuration

Default settings (adjust with `/config`):

| Setting | Default | Description |
|---------|---------|-------------|
| `max_single_bet_usd` | 50 | Maximum single bet in USD |
| `max_position_usd` | 200 | Maximum position per market |
| `max_portfolio_exposure_usd` | 1000 | Maximum total exposure |
| `min_edge_pct` | 10 | Minimum edge to trade (%) |
| `confidence_threshold` | 0.6 | Minimum confidence to trade |
| `monitor_interval_hours` | 12 | Suggested monitoring frequency |
| `categories` | politics, geopolitics, elections, legislation | Market categories to scan |

## Running Tests

```bash
pytest
```

## License

MIT
