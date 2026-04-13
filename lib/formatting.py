"""Output formatting helpers for Claudshi.

Formats tables, summaries, and reports as markdown for Claude's output.
All monetary values in the memory system are stored as USD cents (integers),
so conversion helpers are provided.
"""

from __future__ import annotations


def usd_cents_to_display(cents: int) -> str:
    """Convert USD cents (integer) to a display string like '$X.XX'.

    Args:
        cents: Amount in USD cents.

    Returns:
        Formatted dollar string, e.g. '$12.50'.
    """
    if cents < 0:
        return f"-${-cents / 100:,.2f}"
    return f"${cents / 100:,.2f}"


def format_probability(prob: float) -> str:
    """Format a probability (0–1) as a percentage string.

    Uses one decimal place for most values, but zero decimals for
    values very close to 0% or 100%.

    Args:
        prob: Probability between 0 and 1.

    Returns:
        Formatted string like '35.0%' or '100%'.
    """
    pct = prob * 100
    if pct <= 0.05:
        return "0%"
    if pct >= 99.95:
        return "100%"
    return f"{pct:.1f}%"


def format_edge_display(claude_prob: float, market_prob: float) -> str:
    """Format the edge between Claude's estimate and the market price.

    Positive edge means Claude thinks YES is more likely than the market.

    Args:
        claude_prob: Claude's estimated YES probability (0–1).
        market_prob: Market-implied YES probability (0–1).

    Returns:
        Formatted string like '+12.0% edge (YES)' or '-5.0% edge (NO)'.
    """
    edge_pct = (claude_prob - market_prob) * 100
    if abs(edge_pct) < 0.05:
        return "No edge"
    side = "YES" if edge_pct > 0 else "NO"
    return f"{edge_pct:+.1f}% edge ({side})"


def format_market_summary(market_data: dict) -> str:
    """One-line summary of a market.

    Args:
        market_data: Dict with keys: ticker, title, last_price (cents),
            volume (int).

    Returns:
        Formatted string like 'TICKER | Title here | Last: $0.35 | Vol: 1,234'.
    """
    ticker = market_data.get("ticker", "???")
    title = market_data.get("title", "Unknown market")
    last_price = market_data.get("last_price", 0)
    volume = market_data.get("volume", 0)
    return (
        f"**{ticker}** | {title} | "
        f"Last: {usd_cents_to_display(last_price)} | "
        f"Vol: {volume:,}"
    )


def format_market_detail(
    market_data: dict, orderbook: dict, probability: dict
) -> str:
    """Detailed market view with orderbook depth and probability estimate.

    Args:
        market_data: Dict with keys: ticker, title, last_price, volume,
            yes_bid, yes_ask, open_interest, expiration_time.
        orderbook: Dict with keys: yes_bids (list of [price, qty]),
            yes_asks (list of [price, qty]).
        probability: Dict with keys: yes_probability, confidence, reasoning.

    Returns:
        Multi-line markdown string with full market detail.
    """
    ticker = market_data.get("ticker", "???")
    title = market_data.get("title", "Unknown market")
    last_price = market_data.get("last_price", 0)
    volume = market_data.get("volume", 0)
    yes_bid = market_data.get("yes_bid", 0)
    yes_ask = market_data.get("yes_ask", 0)
    open_interest = market_data.get("open_interest", 0)
    expiration = market_data.get("expiration_time", "N/A")

    lines = [
        f"## {title}",
        f"**Ticker:** {ticker}",
        f"**Expiration:** {expiration}",
        "",
        "### Price",
        f"| Metric | Value |",
        f"|--------|-------|",
        f"| Last Price | {usd_cents_to_display(last_price)} |",
        f"| Best Bid | {usd_cents_to_display(yes_bid)} |",
        f"| Best Ask | {usd_cents_to_display(yes_ask)} |",
        f"| Spread | {usd_cents_to_display(yes_ask - yes_bid)} |",
        f"| Volume | {volume:,} |",
        f"| Open Interest | {open_interest:,} |",
        "",
    ]

    # Orderbook depth
    bids = orderbook.get("yes_bids", [])
    asks = orderbook.get("yes_asks", [])

    if bids or asks:
        lines.append("### Orderbook Depth (Top 5)")
        lines.append("| Bid Price | Bid Qty | Ask Price | Ask Qty |")
        lines.append("|-----------|---------|-----------|---------|")
        max_rows = max(len(bids), len(asks))
        for i in range(min(max_rows, 5)):
            bid_p = usd_cents_to_display(bids[i][0]) if i < len(bids) else ""
            bid_q = f"{bids[i][1]:,}" if i < len(bids) else ""
            ask_p = usd_cents_to_display(asks[i][0]) if i < len(asks) else ""
            ask_q = f"{asks[i][1]:,}" if i < len(asks) else ""
            lines.append(f"| {bid_p} | {bid_q} | {ask_p} | {ask_q} |")
        lines.append("")

    # Probability estimate
    yes_prob = probability.get("yes_probability")
    confidence = probability.get("confidence", "N/A")
    reasoning = probability.get("reasoning", "")

    if yes_prob is not None:
        market_implied = last_price / 100 if last_price else 0
        lines.append("### Probability Estimate")
        lines.append(f"- **Claude estimate:** {format_probability(yes_prob)}")
        lines.append(f"- **Market implied:** {format_probability(market_implied)}")
        lines.append(f"- **Edge:** {format_edge_display(yes_prob, market_implied)}")
        lines.append(f"- **Confidence:** {confidence}")
        if reasoning:
            lines.append(f"- **Reasoning:** {reasoning}")
        lines.append("")

    return "\n".join(lines)


def format_portfolio_table(positions: list[dict], balances: dict) -> str:
    """Markdown table of all positions with P&L.

    Args:
        positions: List of dicts, each with keys: ticker, title, side,
            quantity, avg_price_cents, current_price_cents, cost_cents,
            current_value_cents, unrealized_pnl_cents.
        balances: Dict with keys: cash_cents, portfolio_value_cents.

    Returns:
        Multi-line markdown string with position table and totals.
    """
    lines = ["## Portfolio"]

    if not positions:
        lines.append("No open positions.")
    else:
        lines.append("")
        lines.append(
            "| Ticker | Side | Qty | Avg Price | Current | "
            "Cost | Value | P&L |"
        )
        lines.append(
            "|--------|------|-----|-----------|---------|"
            "------|-------|-----|"
        )
        total_cost = 0
        total_value = 0
        total_pnl = 0
        for pos in positions:
            ticker = pos.get("ticker", "???")
            side = pos.get("side", "?")
            qty = pos.get("quantity", 0)
            avg_price = pos.get("avg_price_cents", 0)
            cur_price = pos.get("current_price_cents", 0)
            cost = pos.get("cost_cents", 0)
            value = pos.get("current_value_cents", 0)
            pnl = pos.get("unrealized_pnl_cents", 0)
            total_cost += cost
            total_value += value
            total_pnl += pnl
            lines.append(
                f"| {ticker} | {side} | {qty} | "
                f"{usd_cents_to_display(avg_price)} | "
                f"{usd_cents_to_display(cur_price)} | "
                f"{usd_cents_to_display(cost)} | "
                f"{usd_cents_to_display(value)} | "
                f"{usd_cents_to_display(pnl)} |"
            )
        lines.append(
            f"| **Total** | | | | | "
            f"**{usd_cents_to_display(total_cost)}** | "
            f"**{usd_cents_to_display(total_value)}** | "
            f"**{usd_cents_to_display(total_pnl)}** |"
        )

    cash = balances.get("cash_cents", 0)
    portfolio_value = balances.get("portfolio_value_cents", 0)
    lines.append("")
    lines.append(f"**Cash:** {usd_cents_to_display(cash)}")
    lines.append(f"**Portfolio Value:** {usd_cents_to_display(portfolio_value)}")

    return "\n".join(lines)


def format_trade_confirmation(
    order_details: dict, risk_checks: str, portfolio_impact: dict
) -> str:
    """Pre-trade confirmation prompt showing all details.

    Args:
        order_details: Dict with keys: ticker, title, side, quantity,
            price_cents, order_type, estimated_cost_cents,
            claude_probability, market_probability.
        risk_checks: Pre-formatted risk check report string
            (from ``risk.format_risk_report``).
        portfolio_impact: Dict with keys: new_exposure_cents,
            new_concentration_pct.

    Returns:
        Multi-line markdown confirmation prompt.
    """
    ticker = order_details.get("ticker", "???")
    title = order_details.get("title", "Unknown")
    side = order_details.get("side", "?")
    qty = order_details.get("quantity", 0)
    price = order_details.get("price_cents", 0)
    order_type = order_details.get("order_type", "limit")
    est_cost = order_details.get("estimated_cost_cents", 0)
    claude_prob = order_details.get("claude_probability")
    market_prob = order_details.get("market_probability")

    lines = [
        "## Trade Confirmation",
        "",
        f"**Market:** {title} ({ticker})",
        f"**Side:** {side}",
        f"**Quantity:** {qty}",
        f"**Price:** {usd_cents_to_display(price)}",
        f"**Order Type:** {order_type}",
        f"**Estimated Cost:** {usd_cents_to_display(est_cost)}",
        "",
    ]

    if claude_prob is not None and market_prob is not None:
        lines.append(f"**Claude Estimate:** {format_probability(claude_prob)}")
        lines.append(f"**Market Price:** {format_probability(market_prob)}")
        lines.append(f"**Edge:** {format_edge_display(claude_prob, market_prob)}")
        lines.append("")

    lines.append(risk_checks)
    lines.append("")

    new_exposure = portfolio_impact.get("new_exposure_cents", 0)
    new_conc = portfolio_impact.get("new_concentration_pct", 0)
    lines.append("### Portfolio Impact")
    lines.append(f"- New total exposure: {usd_cents_to_display(new_exposure)}")
    lines.append(f"- Event concentration: {new_conc:.1f}%")
    lines.append("")
    lines.append("**Confirm this trade? (yes/no)**")

    return "\n".join(lines)


def format_analysis_summary(analysis: dict) -> str:
    """Condensed version of a full analysis for quick display.

    Args:
        analysis: Dict with keys: ticker, title, date, yes_probability,
            confidence, edge_pct, recommendation, factors (list of
            dicts with name and score), reasoning.

    Returns:
        Multi-line markdown summary.
    """
    ticker = analysis.get("ticker", "???")
    title = analysis.get("title", "Unknown")
    date = analysis.get("date", "N/A")
    yes_prob = analysis.get("yes_probability")
    confidence = analysis.get("confidence", "N/A")
    edge_pct = analysis.get("edge_pct", 0)
    recommendation = analysis.get("recommendation", "N/A")
    factors = analysis.get("factors", [])
    reasoning = analysis.get("reasoning", "")

    lines = [
        f"### {title} ({ticker})",
        f"*Analysis date: {date}*",
        "",
    ]

    if yes_prob is not None:
        lines.append(f"- **Probability:** {format_probability(yes_prob)}")
    lines.append(f"- **Confidence:** {confidence}")
    lines.append(f"- **Edge:** {edge_pct:+.1f}%")
    lines.append(f"- **Recommendation:** {recommendation}")

    if factors:
        lines.append("")
        lines.append("**Factors:**")
        for f in factors:
            name = f.get("name", "?")
            score = f.get("score", 0)
            sign = "+" if score > 0 else ""
            lines.append(f"- {name}: {sign}{score}")

    if reasoning:
        lines.append("")
        lines.append(f"**Summary:** {reasoning}")

    return "\n".join(lines)


def format_watchlist(watchlist: list[dict]) -> str:
    """Markdown table of watched markets.

    Args:
        watchlist: List of dicts, each with keys: ticker, title,
            last_price_cents, estimated_edge_pct, added_at.

    Returns:
        Multi-line markdown table.
    """
    lines = ["## Watchlist"]

    if not watchlist:
        lines.append("No markets on watchlist.")
        return "\n".join(lines)

    lines.append("")
    lines.append("| Ticker | Title | Last Price | Est. Edge | Added |")
    lines.append("|--------|-------|------------|-----------|-------|")
    for item in watchlist:
        ticker = item.get("ticker", "???")
        title = item.get("title", "Unknown")
        price = item.get("last_price_cents", 0)
        edge = item.get("estimated_edge_pct", 0)
        added = item.get("added_at", "N/A")
        lines.append(
            f"| {ticker} | {title} | "
            f"{usd_cents_to_display(price)} | "
            f"{edge:+.1f}% | {added} |"
        )

    return "\n".join(lines)


def format_scan_results(results: list[dict]) -> str:
    """Ranked table of scan findings with estimated edge.

    Results are expected to be pre-sorted by absolute edge (largest first).

    Args:
        results: List of dicts, each with keys: ticker, title,
            last_price_cents, volume, claude_probability,
            market_probability, edge_pct, recommended_side.

    Returns:
        Multi-line markdown table.
    """
    lines = ["## Scan Results"]

    if not results:
        lines.append("No mispriced markets found.")
        return "\n".join(lines)

    lines.append("")
    lines.append(
        "| # | Ticker | Title | Last | Vol | "
        "Claude | Market | Edge | Side |"
    )
    lines.append(
        "|---|--------|-------|------|-----|"
        "-------|--------|------|------|"
    )
    for i, r in enumerate(results, 1):
        ticker = r.get("ticker", "???")
        title = r.get("title", "Unknown")
        price = r.get("last_price_cents", 0)
        vol = r.get("volume", 0)
        claude_p = r.get("claude_probability", 0)
        market_p = r.get("market_probability", 0)
        edge = r.get("edge_pct", 0)
        side = r.get("recommended_side", "?")
        lines.append(
            f"| {i} | {ticker} | {title} | "
            f"{usd_cents_to_display(price)} | {vol:,} | "
            f"{format_probability(claude_p)} | "
            f"{format_probability(market_p)} | "
            f"{edge:+.1f}% | {side} |"
        )

    return "\n".join(lines)
