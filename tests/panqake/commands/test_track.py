"""Tests for track.py command module using dependency injection pattern."""

import pytest

from panqake.commands.track import track_branch_core
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
