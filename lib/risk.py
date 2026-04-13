"""Risk checking and position sizing logic for Claudshi.

Enforces risk management rules that protect against oversized bets,
excessive concentration, and trading in illiquid near-expiry markets.
All monetary values are in USD (not cents) unless otherwise noted.
"""

from __future__ import annotations

from datetime import datetime, timezone

from lib.memory import load_config

# Default risk parameters (used when config values are missing).
DEFAULT_RISK_CONFIG: dict[str, float | int] = {
    "max_single_bet_usd": 50,
    "max_position_usd": 200,
    "max_portfolio_exposure_usd": 1000,
    "min_edge_pct": 10,
    "confidence_threshold": 0.6,
    "max_concentration_pct": 40,
}

# Minimum time before expiry to allow trading (seconds).
_MIN_EXPIRY_BUFFER_SECS = 3600  # 1 hour


def load_risk_config() -> dict:
    """Load risk parameters from config, falling back to defaults.

    Reads the global config via `load_config()` and overlays risk-specific
    defaults for any missing keys.
    """
    config = load_config()
    for key, default in DEFAULT_RISK_CONFIG.items():
        if key not in config:
            config[key] = default
    return config


def check_bet(
    amount_usd: float,
    ticker: str,
    portfolio_summary: dict,
    config: dict,
) -> tuple[bool, list[str]]:
    """Validate a proposed bet against all risk rules.

    Args:
        amount_usd: Proposed bet size in USD.
        ticker: Market ticker for the bet.
        portfolio_summary: Current portfolio state with keys like
            ``total_exposure_usd``, ``positions`` (dict of ticker → position).
        config: Risk configuration (from ``load_risk_config``).

    Returns:
        A tuple of (allowed, reasons). ``allowed`` is True only if all
        checks pass. ``reasons`` contains human-readable explanations
        for every failed check.
    """
    reasons: list[str] = []

    max_single = config.get("max_single_bet_usd", DEFAULT_RISK_CONFIG["max_single_bet_usd"])
    if amount_usd > max_single:
        reasons.append(
            f"Bet ${amount_usd:.2f} exceeds max single bet of ${max_single:.2f}."
        )

    max_position = config.get("max_position_usd", DEFAULT_RISK_CONFIG["max_position_usd"])
    positions = portfolio_summary.get("positions", {})
    existing = positions.get(ticker, {}).get("exposure_usd", 0)
    if existing + amount_usd > max_position:
        reasons.append(
            f"Position would be ${existing + amount_usd:.2f}, "
            f"exceeding max position of ${max_position:.2f}."
        )

    max_exposure = config.get(
        "max_portfolio_exposure_usd",
        DEFAULT_RISK_CONFIG["max_portfolio_exposure_usd"],
    )
    total_exposure = portfolio_summary.get("total_exposure_usd", 0)
    if total_exposure + amount_usd > max_exposure:
        reasons.append(
            f"Portfolio exposure would be ${total_exposure + amount_usd:.2f}, "
            f"exceeding max of ${max_exposure:.2f}."
        )

    allowed = len(reasons) == 0
    return allowed, reasons


def check_market_expiry(expiration_time: str) -> tuple[bool, str]:
    """Reject if the market expires within 1 hour.

    Args:
        expiration_time: ISO 8601 timestamp of market expiry.

    Returns:
        A tuple of (allowed, reason). ``allowed`` is False if the market
        expires within the safety buffer.
    """
    expiry = datetime.fromisoformat(expiration_time.replace("Z", "+00:00"))
    now = datetime.now(timezone.utc)
    remaining = (expiry - now).total_seconds()

    if remaining < _MIN_EXPIRY_BUFFER_SECS:
        return False, (
            f"Market expires in {remaining / 60:.0f} minutes — "
            f"minimum buffer is {_MIN_EXPIRY_BUFFER_SECS // 60} minutes."
        )
    return True, ""


def check_concentration(
    event_slug: str,
    new_amount: float,
    portfolio_summary: dict,
    config: dict,
) -> tuple[bool, str]:
    """Warn if more than max_concentration_pct of portfolio is in one event.

    Args:
        event_slug: The event to check concentration for.
        new_amount: Additional USD being added to this event.
        portfolio_summary: Current portfolio state with keys like
            ``total_exposure_usd`` and ``events`` (dict of slug → exposure).
        config: Risk configuration.

    Returns:
        A tuple of (allowed, reason). ``allowed`` is False if the event
        concentration exceeds the threshold.
    """
    max_pct = config.get("max_concentration_pct", DEFAULT_RISK_CONFIG["max_concentration_pct"])
    total_exposure = portfolio_summary.get("total_exposure_usd", 0)
    event_exposures = portfolio_summary.get("events", {})
    event_current = event_exposures.get(event_slug, 0)

    new_total = total_exposure + new_amount
    new_event = event_current + new_amount

    if new_total <= 0:
        return True, ""

    concentration_pct = (new_event / new_total) * 100

    if concentration_pct > max_pct:
        return False, (
            f"Event '{event_slug}' would be {concentration_pct:.1f}% of portfolio, "
            f"exceeding max concentration of {max_pct:.0f}%."
        )
    return True, ""


def calculate_edge(claude_probability: float, market_probability: float) -> float:
    """Calculate the edge between Claude's estimate and the market price.

    Args:
        claude_probability: Claude's estimated YES probability (0–1).
        market_probability: Market-implied YES probability (0–1).

    Returns:
        Edge as a percentage (e.g., 15.0 means 15% edge). Positive means
        Claude thinks YES is more likely than the market does.
    """
    return (claude_probability - market_probability) * 100


def calculate_position_size(
    edge: float,
    market_probability: float,
    bankroll: float,
    config: dict,
) -> float:
    """Calculate position size using quarter-Kelly criterion.

    Uses a fractional (quarter) Kelly to protect against estimation error.

    Args:
        edge: Edge as a percentage (from ``calculate_edge``).
        market_probability: Market-implied YES probability (0–1).
        bankroll: Available bankroll in USD.
        config: Risk configuration.

    Returns:
        Recommended bet size in USD, capped by ``max_single_bet_usd``.
        Returns 0 if the edge is zero or negative.
    """
    if edge <= 0:
        return 0.0

    edge_frac = edge / 100  # convert percentage to fraction

    # Kelly fraction: (edge * (1 - market_prob)) / (1 - edge)
    # Guard against division by zero when edge_frac >= 1.
    denominator = 1 - edge_frac
    if denominator <= 0:
        kelly_fraction = 1.0
    else:
        kelly_fraction = (edge_frac * (1 - market_probability)) / denominator

    kelly_fraction = max(kelly_fraction, 0.0)

    # Quarter-Kelly for safety.
    bet_size = kelly_fraction * bankroll * 0.25

    max_bet = config.get("max_single_bet_usd", DEFAULT_RISK_CONFIG["max_single_bet_usd"])
    bet_size = min(bet_size, max_bet)

    return round(bet_size, 2)


def format_risk_report(checks: list[tuple[str, bool, str]]) -> str:
    """Format risk check results into a human-readable report.

    Args:
        checks: A list of (check_name, passed, detail) tuples.
            ``check_name`` is a short label (e.g., "Max single bet").
            ``passed`` is True if the check passed.
            ``detail`` is a description or reason string.

    Returns:
        A markdown-formatted risk report string.
    """
    lines = ["**Risk Check Results**", ""]
    all_passed = True
    for name, passed, detail in checks:
        status = "PASS" if passed else "FAIL"
        if not passed:
            all_passed = False
        line = f"- [{status}] **{name}**: {detail}" if detail else f"- [{status}] **{name}**"
        lines.append(line)

    lines.append("")
    if all_passed:
        lines.append("All risk checks passed.")
    else:
        lines.append("**One or more risk checks failed. Trade not recommended.**")

    return "\n".join(lines)
