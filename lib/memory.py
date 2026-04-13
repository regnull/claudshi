"""Helpers for reading and writing the .claudshi/ memory tree.

All persistent state for the Claudshi plugin lives in a local directory
tree (default: `.claudshi/` in the project root). This module provides
convenience functions for creating, reading, and updating those files.
"""

from __future__ import annotations

import csv
import io
from pathlib import Path
from typing import Any

import yaml

# Default root directory for memory storage.
_DEFAULT_ROOT = Path(__file__).resolve().parent.parent / ".claudshi"

# Default configuration values.
DEFAULT_CONFIG: dict[str, Any] = {
    "max_single_bet_usd": 50,
    "max_position_usd": 200,
    "max_portfolio_exposure_usd": 1000,
    "min_edge_pct": 10,
    "confidence_threshold": 0.6,
    "monitor_interval_hours": 12,
    "categories": ["politics", "geopolitics", "elections", "legislation"],
}


def _root(root: Path | None = None) -> Path:
    """Return the resolved memory root directory."""
    return root if root is not None else _DEFAULT_ROOT


# ---------------------------------------------------------------------------
# Directory helpers
# ---------------------------------------------------------------------------

def ensure_dirs(root: Path | None = None) -> None:
    """Create the `.claudshi/` directory tree if it doesn't exist.

    Creates the top-level directory and the standard subdirectories:
    portfolio/, events/, journal/.
    """
    base = _root(root)
    for subdir in ("portfolio", "events", "journal"):
        (base / subdir).mkdir(parents=True, exist_ok=True)


# ---------------------------------------------------------------------------
# YAML helpers
# ---------------------------------------------------------------------------

def read_yaml(path: Path) -> dict:
    """Read a YAML file and return its contents as a dict.

    Returns an empty dict if the file does not exist or is empty.
    """
    if not path.exists():
        return {}
    text = path.read_text(encoding="utf-8").strip()
    if not text:
        return {}
    data = yaml.safe_load(text)
    return data if isinstance(data, dict) else {}


def write_yaml(path: Path, data: dict) -> None:
    """Write a dict to a YAML file, creating parent dirs as needed."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        yaml.dump(data, default_flow_style=False, sort_keys=False, allow_unicode=True),
        encoding="utf-8",
    )


def append_yaml_list(path: Path, key: str, item: Any) -> None:
    """Append an item to a list within a YAML file.

    If the file doesn't exist or the key is missing, the list is created.
    Useful for actions logs, probability history, etc.
    """
    data = read_yaml(path)
    if key not in data or not isinstance(data[key], list):
        data[key] = []
    data[key].append(item)
    write_yaml(path, data)


# ---------------------------------------------------------------------------
# Markdown helpers
# ---------------------------------------------------------------------------

def read_md(path: Path) -> str:
    """Read a markdown file and return its contents as a string.

    Returns an empty string if the file does not exist.
    """
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8")


def write_md(path: Path, content: str) -> None:
    """Write markdown content to a file, creating parent dirs as needed."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


# ---------------------------------------------------------------------------
# Path helpers
# ---------------------------------------------------------------------------

def get_event_dir(event_slug: str, root: Path | None = None) -> Path:
    """Return the directory path for a given event.

    Example: `.claudshi/events/us-iran-agreement/`
    """
    return _root(root) / "events" / event_slug


def get_market_dir(
    event_slug: str, ticker: str, root: Path | None = None
) -> Path:
    """Return the directory path for a given market within an event.

    Example: `.claudshi/events/us-iran-agreement/markets/KXUSAIRANAGREEMENT-27/`
    """
    return get_event_dir(event_slug, root) / "markets" / ticker


def get_analysis_path(
    event_slug: str,
    ticker: str,
    date: str,
    update_num: int | None = None,
    root: Path | None = None,
) -> Path:
    """Return the file path for an analysis document.

    Args:
        event_slug: The event directory name.
        ticker: The market ticker.
        date: Date string in YYYY-MM-DD format.
        update_num: If None, returns the initial analysis path.
                    Otherwise returns the update path with the given number.
        root: Optional memory root override.

    Returns:
        Path like `.claudshi/events/.../analysis/2025-07-01-initial.md`
        or `.claudshi/events/.../analysis/2025-07-04-update-02.md`.
    """
    market_dir = get_market_dir(event_slug, ticker, root)
    if update_num is None:
        filename = f"{date}-initial.md"
    else:
        filename = f"{date}-update-{update_num:02d}.md"
    return market_dir / "analysis" / filename


def get_next_update_num(
    event_slug: str,
    ticker: str,
    date: str,
    root: Path | None = None,
) -> int:
    """Scan existing analysis updates for the given date and return the next number.

    If no updates exist for that date, returns 1.
    """
    analysis_dir = get_market_dir(event_slug, ticker, root) / "analysis"
    if not analysis_dir.exists():
        return 1
    prefix = f"{date}-update-"
    existing = []
    for f in analysis_dir.iterdir():
        if f.name.startswith(prefix) and f.suffix == ".md":
            try:
                num = int(f.stem.split("-update-")[1])
                existing.append(num)
            except (IndexError, ValueError):
                continue
    return max(existing, default=0) + 1


# ---------------------------------------------------------------------------
# Config helpers
# ---------------------------------------------------------------------------

def load_config(root: Path | None = None) -> dict:
    """Load `.claudshi/config.yaml`, returning defaults if missing.

    Missing keys are filled in from DEFAULT_CONFIG.
    """
    config = read_yaml(_root(root) / "config.yaml")
    merged = {**DEFAULT_CONFIG, **config}
    return merged


def save_config(data: dict, root: Path | None = None) -> None:
    """Write config to `.claudshi/config.yaml`."""
    write_yaml(_root(root) / "config.yaml", data)


# ---------------------------------------------------------------------------
# Watchlist helpers
# ---------------------------------------------------------------------------

def load_watchlist(root: Path | None = None) -> list:
    """Load `.claudshi/watchlist.yaml` and return the watchlist entries.

    Returns an empty list if the file doesn't exist.
    """
    path = _root(root) / "watchlist.yaml"
    if not path.exists():
        return []
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if isinstance(data, list):
        return data
    if isinstance(data, dict) and "markets" in data:
        return data["markets"]
    return []


def save_watchlist(data: list, root: Path | None = None) -> None:
    """Write watchlist to `.claudshi/watchlist.yaml`."""
    write_yaml(_root(root) / "watchlist.yaml", {"markets": data})


# ---------------------------------------------------------------------------
# Portfolio helpers
# ---------------------------------------------------------------------------

def load_portfolio_summary(root: Path | None = None) -> dict:
    """Load the aggregate portfolio summary from `.claudshi/portfolio/summary.yaml`.

    Returns an empty dict if the file doesn't exist.
    """
    return read_yaml(_root(root) / "portfolio" / "summary.yaml")


def save_portfolio_summary(data: dict, root: Path | None = None) -> None:
    """Write portfolio summary to `.claudshi/portfolio/summary.yaml`."""
    write_yaml(_root(root) / "portfolio" / "summary.yaml", data)


def append_balance_log(
    timestamp: str,
    balance: int,
    portfolio_value: int,
    root: Path | None = None,
) -> None:
    """Append a row to `portfolio/balance_log.csv`.

    Creates the file with headers if it doesn't exist.
    All monetary values are in USD cents.
    """
    path = _root(root) / "portfolio" / "balance_log.csv"
    path.parent.mkdir(parents=True, exist_ok=True)
    write_header = not path.exists() or path.stat().st_size == 0
    with path.open("a", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        if write_header:
            writer.writerow(["timestamp", "balance_cents", "portfolio_value_cents"])
        writer.writerow([timestamp, balance, portfolio_value])
