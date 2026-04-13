"""Tests for lib/memory.py — the .claudshi/ memory system helpers."""

from __future__ import annotations

import csv
from pathlib import Path

import pytest
import yaml

from lib.memory import (
    DEFAULT_CONFIG,
    append_balance_log,
    append_yaml_list,
    ensure_dirs,
    get_analysis_path,
    get_event_dir,
    get_market_dir,
    get_next_update_num,
    load_config,
    load_portfolio_summary,
    load_watchlist,
    read_md,
    read_yaml,
    save_config,
    save_portfolio_summary,
    save_watchlist,
    write_md,
    write_yaml,
)


@pytest.fixture
def mem_root(tmp_path: Path) -> Path:
    """Return a temporary directory to use as the memory root."""
    root = tmp_path / ".claudshi"
    return root


# ---------------------------------------------------------------------------
# ensure_dirs
# ---------------------------------------------------------------------------

class TestEnsureDirs:
    def test_creates_subdirectories(self, mem_root: Path) -> None:
        ensure_dirs(mem_root)
        assert (mem_root / "portfolio").is_dir()
        assert (mem_root / "events").is_dir()
        assert (mem_root / "journal").is_dir()

    def test_idempotent(self, mem_root: Path) -> None:
        ensure_dirs(mem_root)
        ensure_dirs(mem_root)  # should not raise
        assert (mem_root / "portfolio").is_dir()


# ---------------------------------------------------------------------------
# YAML round-trip
# ---------------------------------------------------------------------------

class TestYaml:
    def test_read_missing_file(self, tmp_path: Path) -> None:
        assert read_yaml(tmp_path / "missing.yaml") == {}

    def test_read_empty_file(self, tmp_path: Path) -> None:
        path = tmp_path / "empty.yaml"
        path.write_text("")
        assert read_yaml(path) == {}

    def test_round_trip(self, tmp_path: Path) -> None:
        path = tmp_path / "data.yaml"
        data = {"ticker": "FOO-1", "price": 42, "tags": ["a", "b"]}
        write_yaml(path, data)
        assert read_yaml(path) == data

    def test_write_creates_parent_dirs(self, tmp_path: Path) -> None:
        path = tmp_path / "a" / "b" / "c.yaml"
        write_yaml(path, {"key": "value"})
        assert read_yaml(path) == {"key": "value"}

    def test_read_non_dict_returns_empty(self, tmp_path: Path) -> None:
        path = tmp_path / "list.yaml"
        path.write_text("- a\n- b\n")
        assert read_yaml(path) == {}


# ---------------------------------------------------------------------------
# append_yaml_list
# ---------------------------------------------------------------------------

class TestAppendYamlList:
    def test_append_to_new_file(self, tmp_path: Path) -> None:
        path = tmp_path / "log.yaml"
        append_yaml_list(path, "actions", {"type": "analyze"})
        data = read_yaml(path)
        assert data["actions"] == [{"type": "analyze"}]

    def test_append_to_existing_list(self, tmp_path: Path) -> None:
        path = tmp_path / "log.yaml"
        write_yaml(path, {"actions": [{"type": "analyze"}]})
        append_yaml_list(path, "actions", {"type": "bet"})
        data = read_yaml(path)
        assert len(data["actions"]) == 2
        assert data["actions"][1]["type"] == "bet"

    def test_append_creates_list_if_key_missing(self, tmp_path: Path) -> None:
        path = tmp_path / "log.yaml"
        write_yaml(path, {"ticker": "FOO"})
        append_yaml_list(path, "actions", {"type": "analyze"})
        data = read_yaml(path)
        assert data["ticker"] == "FOO"
        assert data["actions"] == [{"type": "analyze"}]


# ---------------------------------------------------------------------------
# Markdown helpers
# ---------------------------------------------------------------------------

class TestMarkdown:
    def test_read_missing(self, tmp_path: Path) -> None:
        assert read_md(tmp_path / "missing.md") == ""

    def test_round_trip(self, tmp_path: Path) -> None:
        path = tmp_path / "analysis.md"
        content = "# Analysis\n\nSome reasoning here.\n"
        write_md(path, content)
        assert read_md(path) == content

    def test_write_creates_parents(self, tmp_path: Path) -> None:
        path = tmp_path / "deep" / "nested" / "file.md"
        write_md(path, "hello")
        assert read_md(path) == "hello"


# ---------------------------------------------------------------------------
# Path generation
# ---------------------------------------------------------------------------

class TestPathHelpers:
    def test_get_event_dir(self, mem_root: Path) -> None:
        d = get_event_dir("us-iran-deal", mem_root)
        assert d == mem_root / "events" / "us-iran-deal"

    def test_get_market_dir(self, mem_root: Path) -> None:
        d = get_market_dir("us-iran-deal", "KXFOO-1", mem_root)
        assert d == mem_root / "events" / "us-iran-deal" / "markets" / "KXFOO-1"

    def test_get_analysis_path_initial(self, mem_root: Path) -> None:
        p = get_analysis_path("ev", "TK", "2025-07-01", root=mem_root)
        assert p.name == "2025-07-01-initial.md"
        assert "analysis" in str(p)

    def test_get_analysis_path_update(self, mem_root: Path) -> None:
        p = get_analysis_path("ev", "TK", "2025-07-04", update_num=3, root=mem_root)
        assert p.name == "2025-07-04-update-03.md"

    def test_get_next_update_num_no_dir(self, mem_root: Path) -> None:
        assert get_next_update_num("ev", "TK", "2025-07-01", mem_root) == 1

    def test_get_next_update_num_existing(self, mem_root: Path) -> None:
        analysis_dir = get_market_dir("ev", "TK", mem_root) / "analysis"
        analysis_dir.mkdir(parents=True)
        (analysis_dir / "2025-07-01-update-01.md").write_text("v1")
        (analysis_dir / "2025-07-01-update-02.md").write_text("v2")
        assert get_next_update_num("ev", "TK", "2025-07-01", mem_root) == 3

    def test_get_next_update_num_different_dates(self, mem_root: Path) -> None:
        analysis_dir = get_market_dir("ev", "TK", mem_root) / "analysis"
        analysis_dir.mkdir(parents=True)
        (analysis_dir / "2025-07-01-update-01.md").write_text("v1")
        (analysis_dir / "2025-07-02-update-01.md").write_text("v1")
        # Should only count updates for the requested date.
        assert get_next_update_num("ev", "TK", "2025-07-02", mem_root) == 2


# ---------------------------------------------------------------------------
# Config helpers
# ---------------------------------------------------------------------------

class TestConfig:
    def test_load_defaults_when_missing(self, mem_root: Path) -> None:
        config = load_config(mem_root)
        assert config == DEFAULT_CONFIG

    def test_save_and_load(self, mem_root: Path) -> None:
        ensure_dirs(mem_root)
        save_config({"max_single_bet_usd": 100}, mem_root)
        config = load_config(mem_root)
        assert config["max_single_bet_usd"] == 100
        # Defaults should still be filled in.
        assert config["min_edge_pct"] == DEFAULT_CONFIG["min_edge_pct"]


# ---------------------------------------------------------------------------
# Watchlist helpers
# ---------------------------------------------------------------------------

class TestWatchlist:
    def test_load_empty(self, mem_root: Path) -> None:
        assert load_watchlist(mem_root) == []

    def test_save_and_load(self, mem_root: Path) -> None:
        ensure_dirs(mem_root)
        items = [{"ticker": "FOO-1"}, {"ticker": "BAR-2"}]
        save_watchlist(items, mem_root)
        assert load_watchlist(mem_root) == items


# ---------------------------------------------------------------------------
# Portfolio helpers
# ---------------------------------------------------------------------------

class TestPortfolio:
    def test_load_empty(self, mem_root: Path) -> None:
        assert load_portfolio_summary(mem_root) == {}

    def test_save_and_load(self, mem_root: Path) -> None:
        ensure_dirs(mem_root)
        data = {"total_invested_cents": 5000, "unrealized_pnl_cents": -200}
        save_portfolio_summary(data, mem_root)
        assert load_portfolio_summary(mem_root) == data


# ---------------------------------------------------------------------------
# Balance log CSV
# ---------------------------------------------------------------------------

class TestBalanceLog:
    def test_creates_file_with_header(self, mem_root: Path) -> None:
        ensure_dirs(mem_root)
        append_balance_log("2025-07-01T10:00:00Z", 100000, 95000, mem_root)
        path = mem_root / "portfolio" / "balance_log.csv"
        assert path.exists()
        rows = list(csv.reader(path.open()))
        assert rows[0] == ["timestamp", "balance_cents", "portfolio_value_cents"]
        assert rows[1] == ["2025-07-01T10:00:00Z", "100000", "95000"]

    def test_appends_without_duplicating_header(self, mem_root: Path) -> None:
        ensure_dirs(mem_root)
        append_balance_log("2025-07-01T10:00:00Z", 100000, 95000, mem_root)
        append_balance_log("2025-07-02T10:00:00Z", 100500, 96000, mem_root)
        path = mem_root / "portfolio" / "balance_log.csv"
        rows = list(csv.reader(path.open()))
        assert len(rows) == 3  # 1 header + 2 data rows
        assert rows[0][0] == "timestamp"  # header only once
