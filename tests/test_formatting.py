"""Tests for lib/formatting.py."""

from lib.formatting import (
    format_analysis_summary,
    format_edge_display,
    format_market_detail,
    format_market_summary,
    format_portfolio_table,
    format_probability,
    format_scan_results,
    format_trade_confirmation,
    format_watchlist,
    usd_cents_to_display,
)


# ---------------------------------------------------------------------------
# usd_cents_to_display
# ---------------------------------------------------------------------------

class TestUsdCentsToDisplay:
    def test_zero(self):
        assert usd_cents_to_display(0) == "$0.00"

    def test_positive(self):
        assert usd_cents_to_display(1250) == "$12.50"

    def test_negative(self):
        assert usd_cents_to_display(-500) == "-$5.00"

    def test_large_amount(self):
        assert usd_cents_to_display(123456) == "$1,234.56"

    def test_single_cent(self):
        assert usd_cents_to_display(1) == "$0.01"


# ---------------------------------------------------------------------------
# format_probability
# ---------------------------------------------------------------------------

class TestFormatProbability:
    def test_mid_range(self):
        assert format_probability(0.35) == "35.0%"

    def test_zero(self):
        assert format_probability(0.0) == "0%"

    def test_one(self):
        assert format_probability(1.0) == "100%"

    def test_small(self):
        assert format_probability(0.05) == "5.0%"

    def test_near_one(self):
        assert format_probability(0.999) == "99.9%"

    def test_half(self):
        assert format_probability(0.5) == "50.0%"


# ---------------------------------------------------------------------------
# format_edge_display
# ---------------------------------------------------------------------------

class TestFormatEdgeDisplay:
    def test_positive_edge(self):
        result = format_edge_display(0.45, 0.30)
        assert "+15.0%" in result
        assert "YES" in result

    def test_negative_edge(self):
        result = format_edge_display(0.25, 0.40)
        assert "-15.0%" in result
        assert "NO" in result

    def test_no_edge(self):
        result = format_edge_display(0.50, 0.50)
        assert result == "No edge"

    def test_tiny_edge_rounds_to_zero(self):
        result = format_edge_display(0.5001, 0.5001)
        assert result == "No edge"


# ---------------------------------------------------------------------------
# format_market_summary
# ---------------------------------------------------------------------------

class TestFormatMarketSummary:
    def test_basic(self):
        data = {
            "ticker": "KXTEST-1",
            "title": "Will X happen?",
            "last_price": 3500,
            "volume": 1234,
        }
        result = format_market_summary(data)
        assert "KXTEST-1" in result
        assert "Will X happen?" in result
        assert "$35.00" in result
        assert "1,234" in result

    def test_missing_fields(self):
        result = format_market_summary({})
        assert "???" in result
        assert "Unknown market" in result


# ---------------------------------------------------------------------------
# format_market_detail
# ---------------------------------------------------------------------------

class TestFormatMarketDetail:
    def test_full_detail(self):
        market = {
            "ticker": "KXTEST-1",
            "title": "Test Market",
            "last_price": 3500,
            "volume": 500,
            "yes_bid": 3400,
            "yes_ask": 3600,
            "open_interest": 200,
            "expiration_time": "2026-12-31T23:59:00Z",
        }
        orderbook = {
            "yes_bids": [[3400, 10], [3300, 20]],
            "yes_asks": [[3600, 15], [3700, 25]],
        }
        probability = {
            "yes_probability": 0.40,
            "confidence": "medium",
            "reasoning": "Based on current polls",
        }
        result = format_market_detail(market, orderbook, probability)
        assert "Test Market" in result
        assert "KXTEST-1" in result
        assert "$35.00" in result
        assert "Orderbook Depth" in result
        assert "Probability Estimate" in result
        assert "40.0%" in result
        assert "medium" in result

    def test_empty_orderbook(self):
        result = format_market_detail(
            {"ticker": "T", "title": "T", "last_price": 0, "yes_bid": 0, "yes_ask": 0},
            {},
            {},
        )
        assert "Orderbook Depth" not in result

    def test_no_probability(self):
        result = format_market_detail(
            {"ticker": "T", "title": "T", "last_price": 50, "yes_bid": 0, "yes_ask": 0},
            {},
            {},
        )
        assert "Probability Estimate" not in result


# ---------------------------------------------------------------------------
# format_portfolio_table
# ---------------------------------------------------------------------------

class TestFormatPortfolioTable:
    def test_with_positions(self):
        positions = [
            {
                "ticker": "KXTEST-1",
                "side": "YES",
                "quantity": 10,
                "avg_price_cents": 3000,
                "current_price_cents": 3500,
                "cost_cents": 30000,
                "current_value_cents": 35000,
                "unrealized_pnl_cents": 5000,
            },
        ]
        balances = {"cash_cents": 50000, "portfolio_value_cents": 85000}
        result = format_portfolio_table(positions, balances)
        assert "KXTEST-1" in result
        assert "YES" in result
        assert "$50.00" in result  # pnl
        assert "Total" in result
        assert "$500.00" in result  # cash

    def test_empty_positions(self):
        result = format_portfolio_table([], {"cash_cents": 10000, "portfolio_value_cents": 10000})
        assert "No open positions" in result
        assert "$100.00" in result


# ---------------------------------------------------------------------------
# format_trade_confirmation
# ---------------------------------------------------------------------------

class TestFormatTradeConfirmation:
    def test_basic_confirmation(self):
        order = {
            "ticker": "KXTEST-1",
            "title": "Test Market",
            "side": "YES",
            "quantity": 10,
            "price_cents": 3500,
            "order_type": "limit",
            "estimated_cost_cents": 35000,
            "claude_probability": 0.45,
            "market_probability": 0.35,
        }
        risk = "**Risk Check Results**\n\n- [PASS] **Max bet**\n\nAll risk checks passed."
        impact = {"new_exposure_cents": 85000, "new_concentration_pct": 25.0}

        result = format_trade_confirmation(order, risk, impact)
        assert "Trade Confirmation" in result
        assert "KXTEST-1" in result
        assert "YES" in result
        assert "$350.00" in result  # cost
        assert "45.0%" in result  # claude prob
        assert "+10.0% edge" in result
        assert "Confirm this trade?" in result
        assert "PASS" in result


# ---------------------------------------------------------------------------
# format_analysis_summary
# ---------------------------------------------------------------------------

class TestFormatAnalysisSummary:
    def test_full_analysis(self):
        analysis = {
            "ticker": "KXTEST-1",
            "title": "Will X happen?",
            "date": "2026-04-12",
            "yes_probability": 0.40,
            "confidence": "medium",
            "edge_pct": 12.0,
            "recommendation": "Trade",
            "factors": [
                {"name": "Political will", "score": 3},
                {"name": "Public pressure", "score": -2},
            ],
            "reasoning": "Strong political momentum offset by public opposition.",
        }
        result = format_analysis_summary(analysis)
        assert "KXTEST-1" in result
        assert "40.0%" in result
        assert "+12.0%" in result
        assert "Trade" in result
        assert "Political will: +3" in result
        assert "Public pressure: -2" in result
        assert "Strong political momentum" in result

    def test_minimal_analysis(self):
        result = format_analysis_summary({"ticker": "T", "title": "Test"})
        assert "T" in result
        assert "Test" in result


# ---------------------------------------------------------------------------
# format_watchlist
# ---------------------------------------------------------------------------

class TestFormatWatchlist:
    def test_with_items(self):
        watchlist = [
            {
                "ticker": "KXTEST-1",
                "title": "Test Market",
                "last_price_cents": 3500,
                "estimated_edge_pct": 8.5,
                "added_at": "2026-04-10",
            },
        ]
        result = format_watchlist(watchlist)
        assert "KXTEST-1" in result
        assert "$35.00" in result
        assert "+8.5%" in result

    def test_empty_watchlist(self):
        result = format_watchlist([])
        assert "No markets on watchlist" in result


# ---------------------------------------------------------------------------
# format_scan_results
# ---------------------------------------------------------------------------

class TestFormatScanResults:
    def test_with_results(self):
        results = [
            {
                "ticker": "KXTEST-1",
                "title": "Market A",
                "last_price_cents": 3500,
                "volume": 2000,
                "claude_probability": 0.50,
                "market_probability": 0.35,
                "edge_pct": 15.0,
                "recommended_side": "YES",
            },
            {
                "ticker": "KXTEST-2",
                "title": "Market B",
                "last_price_cents": 7000,
                "volume": 500,
                "claude_probability": 0.60,
                "market_probability": 0.70,
                "edge_pct": -10.0,
                "recommended_side": "NO",
            },
        ]
        result = format_scan_results(results)
        assert "Scan Results" in result
        assert "KXTEST-1" in result
        assert "KXTEST-2" in result
        assert "+15.0%" in result
        assert "-10.0%" in result
        assert "YES" in result
        assert "NO" in result

    def test_empty_results(self):
        result = format_scan_results([])
        assert "No mispriced markets found" in result
