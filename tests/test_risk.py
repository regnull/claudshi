"""Tests for lib/risk.py — risk checking and position sizing."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from lib.risk import (
    DEFAULT_RISK_CONFIG,
    calculate_edge,
    calculate_position_size,
    check_bet,
    check_concentration,
    check_market_expiry,
    format_risk_report,
    load_risk_config,
)


# ---------------------------------------------------------------------------
# load_risk_config
# ---------------------------------------------------------------------------


def test_load_risk_config_returns_defaults(tmp_path):
    """Config loader fills in default risk values when config is absent."""
    from lib import memory

    original_root = memory._DEFAULT_ROOT
    memory._DEFAULT_ROOT = tmp_path
    try:
        config = load_risk_config()
        for key, default in DEFAULT_RISK_CONFIG.items():
            assert config[key] == default
    finally:
        memory._DEFAULT_ROOT = original_root


# ---------------------------------------------------------------------------
# check_bet — pass cases
# ---------------------------------------------------------------------------


def test_check_bet_passes_within_limits():
    """A small bet against an empty portfolio should pass."""
    portfolio = {"total_exposure_usd": 0, "positions": {}}
    config = dict(DEFAULT_RISK_CONFIG)
    allowed, reasons = check_bet(25, "TICKER-1", portfolio, config)
    assert allowed is True
    assert reasons == []


def test_check_bet_passes_at_exact_limits():
    """Bets exactly at the limit should pass."""
    portfolio = {"total_exposure_usd": 950, "positions": {"TICKER-1": {"exposure_usd": 150}}}
    config = {**DEFAULT_RISK_CONFIG, "max_single_bet_usd": 50, "max_position_usd": 200, "max_portfolio_exposure_usd": 1000}
    allowed, reasons = check_bet(50, "TICKER-1", portfolio, config)
    assert allowed is True
    assert reasons == []


# ---------------------------------------------------------------------------
# check_bet — fail cases
# ---------------------------------------------------------------------------


def test_check_bet_fails_exceeds_single_bet():
    """A bet exceeding max_single_bet_usd should fail."""
    portfolio = {"total_exposure_usd": 0, "positions": {}}
    config = {**DEFAULT_RISK_CONFIG, "max_single_bet_usd": 50}
    allowed, reasons = check_bet(75, "TICKER-1", portfolio, config)
    assert allowed is False
    assert any("max single bet" in r.lower() for r in reasons)


def test_check_bet_fails_exceeds_position():
    """A bet that would push a position over the limit should fail."""
    portfolio = {"total_exposure_usd": 100, "positions": {"TICKER-1": {"exposure_usd": 180}}}
    config = {**DEFAULT_RISK_CONFIG, "max_position_usd": 200}
    allowed, reasons = check_bet(30, "TICKER-1", portfolio, config)
    assert allowed is False
    assert any("max position" in r.lower() for r in reasons)


def test_check_bet_fails_exceeds_exposure():
    """A bet that would push total exposure over the limit should fail."""
    portfolio = {"total_exposure_usd": 980, "positions": {}}
    config = {**DEFAULT_RISK_CONFIG, "max_portfolio_exposure_usd": 1000}
    allowed, reasons = check_bet(30, "TICKER-1", portfolio, config)
    assert allowed is False
    assert any("max of" in r.lower() for r in reasons)


def test_check_bet_multiple_failures():
    """Multiple limit violations should all be reported."""
    portfolio = {"total_exposure_usd": 990, "positions": {"T": {"exposure_usd": 195}}}
    config = {**DEFAULT_RISK_CONFIG, "max_single_bet_usd": 50, "max_position_usd": 200, "max_portfolio_exposure_usd": 1000}
    allowed, reasons = check_bet(60, "T", portfolio, config)
    assert allowed is False
    assert len(reasons) >= 2


# ---------------------------------------------------------------------------
# check_market_expiry
# ---------------------------------------------------------------------------


def test_expiry_allowed_when_far_away():
    """A market expiring in 24 hours should be allowed."""
    future = (datetime.now(timezone.utc) + timedelta(hours=24)).isoformat()
    allowed, reason = check_market_expiry(future)
    assert allowed is True
    assert reason == ""


def test_expiry_rejected_when_too_close():
    """A market expiring in 30 minutes should be rejected."""
    near = (datetime.now(timezone.utc) + timedelta(minutes=30)).isoformat()
    allowed, reason = check_market_expiry(near)
    assert allowed is False
    assert "minutes" in reason


def test_expiry_rejected_when_already_expired():
    """An already-expired market should be rejected."""
    past = (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat()
    allowed, reason = check_market_expiry(past)
    assert allowed is False


def test_expiry_with_z_suffix():
    """ISO timestamps with 'Z' suffix should be parsed correctly."""
    future = (datetime.now(timezone.utc) + timedelta(hours=2)).strftime(
        "%Y-%m-%dT%H:%M:%SZ"
    )
    allowed, _ = check_market_expiry(future)
    assert allowed is True


# ---------------------------------------------------------------------------
# check_concentration
# ---------------------------------------------------------------------------


def test_concentration_passes_when_low():
    """A well-diversified portfolio should pass."""
    portfolio = {"total_exposure_usd": 100, "events": {"event-a": 20}}
    config = dict(DEFAULT_RISK_CONFIG)
    allowed, reason = check_concentration("event-a", 10, portfolio, config)
    # (20 + 10) / (100 + 10) = 27.3% < 40%
    assert allowed is True
    assert reason == ""


def test_concentration_fails_when_too_high():
    """A concentrated bet should fail."""
    portfolio = {"total_exposure_usd": 100, "events": {"event-a": 50}}
    config = {**DEFAULT_RISK_CONFIG, "max_concentration_pct": 40}
    allowed, reason = check_concentration("event-a", 40, portfolio, config)
    # (50 + 40) / (100 + 40) = 64.3% > 40%
    assert allowed is False
    assert "concentration" in reason.lower()


def test_concentration_empty_portfolio():
    """First bet into an empty portfolio fails because 100% concentration exceeds 40% threshold."""
    portfolio = {"total_exposure_usd": 0, "events": {}}
    config = {**DEFAULT_RISK_CONFIG, "max_concentration_pct": 40}
    allowed, reason = check_concentration("event-a", 50, portfolio, config)
    # 50/50 = 100% > 40% — fails
    assert allowed is False


def test_concentration_zero_amount():
    """Zero new amount should always pass."""
    portfolio = {"total_exposure_usd": 100, "events": {"event-a": 50}}
    config = dict(DEFAULT_RISK_CONFIG)
    allowed, reason = check_concentration("event-a", 0, portfolio, config)
    # (50 + 0) / (100 + 0) = 50% > 40% — should still fail
    assert allowed is False


# ---------------------------------------------------------------------------
# calculate_edge
# ---------------------------------------------------------------------------


def test_edge_positive():
    """Claude thinks YES is more likely than the market."""
    edge = calculate_edge(0.45, 0.30)
    assert edge == pytest.approx(15.0)


def test_edge_negative():
    """Claude thinks YES is less likely than the market."""
    edge = calculate_edge(0.20, 0.35)
    assert edge == pytest.approx(-15.0)


def test_edge_zero():
    """No edge when probabilities match."""
    edge = calculate_edge(0.50, 0.50)
    assert edge == pytest.approx(0.0)


# ---------------------------------------------------------------------------
# calculate_position_size
# ---------------------------------------------------------------------------


def test_kelly_positive_edge():
    """Positive edge should produce a positive bet size."""
    config = {**DEFAULT_RISK_CONFIG, "max_single_bet_usd": 50}
    size = calculate_position_size(15.0, 0.30, 500, config)
    assert size > 0
    assert size <= 50  # capped by max_single_bet_usd


def test_kelly_zero_edge():
    """Zero edge should produce zero bet."""
    config = dict(DEFAULT_RISK_CONFIG)
    size = calculate_position_size(0.0, 0.30, 500, config)
    assert size == 0.0


def test_kelly_negative_edge():
    """Negative edge should produce zero bet."""
    config = dict(DEFAULT_RISK_CONFIG)
    size = calculate_position_size(-10.0, 0.30, 500, config)
    assert size == 0.0


def test_kelly_large_edge_capped():
    """Very large edge should be capped by max_single_bet_usd."""
    config = {**DEFAULT_RISK_CONFIG, "max_single_bet_usd": 50}
    size = calculate_position_size(50.0, 0.30, 10000, config)
    assert size == 50.0


def test_kelly_small_bankroll():
    """Small bankroll should produce small bet."""
    config = {**DEFAULT_RISK_CONFIG, "max_single_bet_usd": 50}
    size = calculate_position_size(10.0, 0.50, 20, config)
    assert size <= 20


def test_kelly_edge_at_100_pct():
    """Edge at 100% (certain winner) should still be capped."""
    config = {**DEFAULT_RISK_CONFIG, "max_single_bet_usd": 50}
    size = calculate_position_size(100.0, 0.50, 1000, config)
    assert size == 50.0


# ---------------------------------------------------------------------------
# format_risk_report
# ---------------------------------------------------------------------------


def test_format_risk_report_all_pass():
    """All-pass report should include 'All risk checks passed'."""
    checks = [
        ("Max single bet", True, "Under limit"),
        ("Max position", True, "Under limit"),
    ]
    report = format_risk_report(checks)
    assert "All risk checks passed" in report
    assert "[PASS]" in report
    assert "[FAIL]" not in report


def test_format_risk_report_with_failure():
    """Report with failures should show FAIL and warning."""
    checks = [
        ("Max single bet", True, "Under limit"),
        ("Max position", False, "Exceeds $200 limit"),
    ]
    report = format_risk_report(checks)
    assert "[FAIL]" in report
    assert "[PASS]" in report
    assert "not recommended" in report.lower()


def test_format_risk_report_empty_detail():
    """Check with empty detail should still render cleanly."""
    checks = [("Some check", True, "")]
    report = format_risk_report(checks)
    assert "[PASS]" in report
