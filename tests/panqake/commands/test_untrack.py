"""Tests for untrack.py command module using dependency injection pattern."""

import pytest

from panqake.commands.untrack import untrack_branch_core
from panqake.ports import BranchNotFoundError
from panqake.testing.fakes import FakeConfig, FakeGit, FakeUI


class TestUntrackBranchCore:
    """Tests for untrack_branch_core."""

    def test_untracks_current_branch(self):
        git = FakeGit(branches=["main", "feature"], current_branch="feature")
        config = FakeConfig(stack={"feature": {"parent": "main"}})
        ui = FakeUI(strict=False)

        result = untrack_branch_core(git=git, config=config, ui=ui)

        assert result.branch_name == "feature"
        assert result.was_tracked is True
        assert "feature" not in config.stack

    def test_untracks_specified_branch(self):
        git = FakeGit(branches=["main", "feature"], current_branch="main")
        config = FakeConfig(stack={"feature": {"parent": "main"}})
        ui = FakeUI(strict=False)

        result = untrack_branch_core(
            git=git, config=config, ui=ui, branch_name="feature"
        )

        assert result.branch_name == "feature"
        assert result.was_tracked is True
        assert "feature" not in config.stack

    def test_raises_when_no_current_branch(self):
        git = FakeGit(branches=["main"], current_branch=None)
        config = FakeConfig()
        ui = FakeUI(strict=False)

        with pytest.raises(BranchNotFoundError, match="Could not determine"):
            untrack_branch_core(git=git, config=config, ui=ui)

    def test_returns_false_when_not_tracked(self):
        git = FakeGit(branches=["main", "feature"], current_branch="feature")
        config = FakeConfig(stack={})  # Empty stack
        ui = FakeUI(strict=False)

        result = untrack_branch_core(git=git, config=config, ui=ui)

        assert result.branch_name == "feature"
        assert result.was_tracked is False

    def test_prints_info_messages(self):
        git = FakeGit(branches=["main", "feature"], current_branch="feature")
        config = FakeConfig(stack={"feature": {"parent": "main"}})
        ui = FakeUI(strict=False)

        untrack_branch_core(git=git, config=config, ui=ui)

        assert any("feature" in msg for msg in ui.info_messages)
