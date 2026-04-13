# Claudshi

A [Claude Code](https://docs.anthropic.com/en/docs/claude-code) plugin that predicts political events using [Kalshi](https://kalshi.com/) prediction markets.

Claudshi connects to Kalshi via the [kalshi-mcp](https://github.com/regnull/kalshi-mcp) MCP server to scan markets, analyze political events, estimate probabilities, place bets on mispriced markets, and monitor open positions.

## Requirements

- [Claude Code](https://docs.anthropic.com/en/docs/claude-code) CLI
- [kalshi-mcp](https://github.com/regnull/kalshi-mcp) MCP server
- A [Kalshi](https://kalshi.com/) account with API credentials
- Python 3.11+

## Installation

### Option 1: Claude Code CLI

1. **Clone the repo:**

   ```bash
   git clone https://github.com/regnull/claudshi.git
   cd claudshi
   ```

2. **Install kalshi-mcp:**

   ```bash
   pip install git+https://github.com/regnull/kalshi-mcp.git
   ```

3. **Configure API credentials** in `.mcp.json`:

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

4. **Install Python dependencies:**

   ```bash
   pip install -e ".[dev]"
   ```

5. **Run Claude Code from the project directory:**

   ```bash
   claude
   ```

6. **Verify setup:**

   ```
   /cs_config
   ```

### Option 2: Claude Desktop

To use Claudshi inside [Claude Desktop](https://claude.ai/download), you need to configure the MCP server and point Claude Desktop at the project.

1. **Clone the repo and install dependencies** (same as steps 1–4 above).

2. **Install kalshi-mcp globally** so Claude Desktop can find it:

   ```bash
   pip install git+https://github.com/regnull/kalshi-mcp.git
   ```

   Make sure `kalshi-mcp` is on your system PATH. Verify with:

   ```bash
   which kalshi-mcp
   ```

3. **Add the MCP server to Claude Desktop.** Open Claude Desktop settings (gear icon > Developer > Edit Config), and add the `kalshi-mcp` server to `claude_desktop_config.json`:

   ```json
   {
     "mcpServers": {
       "kalshi-mcp": {
         "command": "kalshi-mcp",
         "args": [],
         "env": {
           "KALSHI_API_KEY": "<your-kalshi-api-key>",
           "KALSHI_PRIVATE_KEY_PATH": "<absolute-path-to-your-private-key>"
         }
       }
     }
   }
   ```

   **Important:** Use the absolute path to your private key file (e.g., `/Users/yourname/secret/kalshi_private_key.pem`).

4. **Restart Claude Desktop** for the MCP server to load. You should see a hammer icon in the chat input indicating MCP tools are available.

5. **Use the Kalshi tools directly.** In Claude Desktop, you can ask Claude to use the Kalshi MCP tools (e.g., "get my Kalshi balance", "show me political markets on Kalshi"). Note that the `/cs_*` slash commands are only available in Claude Code — in Claude Desktop, describe what you want in plain language and Claude will use the MCP tools directly.

### Kalshi API Credentials

You need a Kalshi account with API access:

1. Log in to [Kalshi](https://kalshi.com/) and go to **Settings > API Keys**.
2. Create a new API key and download the private key file.
3. Use the API key ID and the path to the private key file in the configuration above.

## Commands

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

## Typical Workflow

```
/cs_scan                          # Find mispriced markets
/cs_analyze KXSOMEMARKET-25       # Deep-dive a candidate
/cs_bet KXSOMEMARKET-25 YES 25    # Place a trade (with confirmation)
/cs_monitor                       # Check positions periodically
/cs_exit KXSOMEMARKET-25          # Close when done
/cs_journal                       # Record the day's activity
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

Default settings (adjust with `/cs_config`):

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
