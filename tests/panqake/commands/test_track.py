"""Tests for track.py command module using dependency injection pattern."""

import json

import pytest

from panqake.commands.track import track, track_branch_core
from panqake.ports import BranchNotFoundError, UserCancelledError
from panqake.testing.fakes import FakeConfig, FakeGit, FakeUI


class TestTrackBranchCore:
    """Tests for track_branch_core."""

    def test_tracks_current_branch(self):
        git = FakeGit(
            branches=["main", "feature"],
            current_branch="feature",
            potential_parents={"feature": ["main", "develop"]},
        )
        config = FakeConfig()
        ui = FakeUI(select_branch_responses=["main"])

        result = track_branch_core(git=git, config=config, ui=ui)

        assert result.branch_name == "feature"
        assert result.parent_branch == "main"
        assert config.stack["feature"]["parent"] == "main"

    def test_tracks_specified_branch(self):
        git = FakeGit(
            branches=["main", "feature", "other"],
            current_branch="main",
            potential_parents={"other": ["main", "feature"]},
        )
        config = FakeConfig()
        ui = FakeUI(select_branch_responses=["feature"])

        result = track_branch_core(git=git, config=config, ui=ui, branch_name="other")

        assert result.branch_name == "other"
        assert result.parent_branch == "feature"
        assert config.stack["other"]["parent"] == "feature"

    def test_raises_when_no_current_branch(self):
        git = FakeGit(branches=["main"], current_branch=None)
        config = FakeConfig()
        ui = FakeUI(strict=False)

        with pytest.raises(BranchNotFoundError, match="Could not determine"):
            track_branch_core(git=git, config=config, ui=ui)

    def test_raises_when_no_potential_parents(self):
        git = FakeGit(
            branches=["main", "feature"],
            current_branch="feature",
            potential_parents={},  # No parents for feature
        )
        config = FakeConfig()
        ui = FakeUI(strict=False)

        with pytest.raises(BranchNotFoundError, match="No potential parent"):
            track_branch_core(git=git, config=config, ui=ui)

    def test_raises_when_user_cancels_selection(self):
        git = FakeGit(
            branches=["main", "feature"],
            current_branch="feature",
            potential_parents={"feature": ["main"]},
        )
        config = FakeConfig()
        ui = FakeUI(cancel_on_select_branch=True)

        with pytest.raises(UserCancelledError):
            track_branch_core(git=git, config=config, ui=ui)

        assert "feature" not in config.stack

    def test_raises_when_no_parent_selected(self):
        git = FakeGit(
            branches=["main", "feature"],
            current_branch="feature",
            potential_parents={"feature": ["main"]},
        )
        config = FakeConfig()
        ui = FakeUI(select_branch_responses=[None], strict=False)

        with pytest.raises(UserCancelledError):
            track_branch_core(git=git, config=config, ui=ui)

    def test_prints_info_messages(self):
        git = FakeGit(
            branches=["main", "feature"],
            current_branch="feature",
            potential_parents={"feature": ["main"]},
        )
        config = FakeConfig()
        ui = FakeUI(select_branch_responses=["main"])

        track_branch_core(git=git, config=config, ui=ui)

        assert any("feature" in msg for msg in ui.info_messages)


def test_track_json_auto_selects_single_parent(monkeypatch, capsys):
    """JSON mode should auto-select the only available parent branch."""
    state: dict[str, tuple[str, str] | None] = {"tracked": None}

    class NoisyGit:
        def get_current_branch(self):
            return "feature-x"

        def get_potential_parents(self, branch):
            return ["main"]

    class RecordingConfig:
        def add_to_stack(self, branch_name, parent_branch, worktree_path=None):
            state["tracked"] = (branch_name, parent_branch)

    monkeypatch.setattr("panqake.commands.track.RealGit", NoisyGit)
    monkeypatch.setattr("panqake.commands.track.RealConfig", RecordingConfig)

    track(branch_name="feature-x", json_output=True)

    stdout_lines = [
        line for line in capsys.readouterr().out.strip().splitlines() if line
    ]
    assert len(stdout_lines) == 1

    payload = json.loads(stdout_lines[0])
    assert payload["ok"] is True
    assert payload["command"] == "track"
    assert payload["result"]["branch_name"] == "feature-x"
    assert payload["result"]["parent_branch"] == "main"
    assert state["tracked"] == ("feature-x", "main")


def test_track_json_fails_when_parent_selection_is_ambiguous(monkeypatch, capsys):
    """JSON mode should fail clearly when multiple parent branches exist."""

    class NoisyGit:
        def get_current_branch(self):
            return "feature-x"

        def get_potential_parents(self, branch):
            return ["main", "develop"]

    class NoopConfig:
        def add_to_stack(self, branch_name, parent_branch, worktree_path=None):
            return None

    monkeypatch.setattr("panqake.commands.track.RealGit", NoisyGit)
    monkeypatch.setattr("panqake.commands.track.RealConfig", NoopConfig)

    with pytest.raises(SystemExit) as exc_info:
        track(branch_name="feature-x", json_output=True)

    assert exc_info.value.code == 2

    stdout_lines = [
        line for line in capsys.readouterr().out.strip().splitlines() if line
    ]
    assert len(stdout_lines) == 1
    payload = json.loads(stdout_lines[0])
    assert payload["ok"] is False
    assert payload["command"] == "track"
    assert payload["error"]["type"] == "NonInteractiveError"
    assert "multiple candidates" in payload["error"]["message"]
