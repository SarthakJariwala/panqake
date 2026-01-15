"""Tests for up.py command module using dependency injection."""

import pytest

from panqake.commands.up import up_core
from panqake.ports import BranchNotFoundError, UpResult
from panqake.testing import FakeConfig, FakeGit, FakeUI


class TestUpCore:
    """Tests for up_core function."""

    def test_moves_to_parent_branch(self):
        """Test navigating up to parent branch."""
        git = FakeGit(branches=["main", "feature"], current_branch="feature")
        config = FakeConfig(stack={"feature": {"parent": "main"}})
        ui = FakeUI(strict=False)

        result = up_core(git=git, config=config, ui=ui)

        assert result == UpResult(
            target_branch="main",
            previous_branch="feature",
            switched=True,
        )
        assert git.current_branch == "main"
        assert git.checkout_calls == ["main"]

    def test_handles_worktree_branch(self):
        """Test handling when parent is in a worktree."""
        git = FakeGit(branches=["main", "feature"], current_branch="feature")
        git.worktrees["main"] = "/path/to/main-worktree"
        config = FakeConfig(stack={"feature": {"parent": "main"}})
        ui = FakeUI(strict=False)

        result = up_core(git=git, config=config, ui=ui)

        assert result == UpResult(
            target_branch="main",
            previous_branch="feature",
            switched=False,
            worktree_path="/path/to/main-worktree",
        )
        assert git.current_branch == "feature"  # Not switched
        assert git.checkout_calls == []
        assert any("worktree" in msg for msg in ui.info_messages)
        assert any("/path/to/main-worktree" in msg for msg in ui.info_messages)

    def test_raises_when_no_current_branch(self):
        """Test error when current branch cannot be determined."""
        git = FakeGit(branches=["main"], current_branch=None)
        config = FakeConfig()
        ui = FakeUI(strict=False)

        with pytest.raises(BranchNotFoundError) as exc_info:
            up_core(git=git, config=config, ui=ui)

        assert "Could not determine current branch" in str(exc_info.value)

    def test_raises_when_no_parent(self):
        """Test error when current branch has no parent."""
        git = FakeGit(branches=["main"], current_branch="main")
        config = FakeConfig()  # No stack entries
        ui = FakeUI(strict=False)

        with pytest.raises(BranchNotFoundError) as exc_info:
            up_core(git=git, config=config, ui=ui)

        assert "has no parent branch" in str(exc_info.value)

    def test_navigates_through_stack(self):
        """Test navigating up through a multi-level stack."""
        git = FakeGit(
            branches=["main", "feature", "sub-feature"],
            current_branch="sub-feature",
        )
        config = FakeConfig(
            stack={
                "feature": {"parent": "main"},
                "sub-feature": {"parent": "feature"},
            }
        )
        ui = FakeUI(strict=False)

        result = up_core(git=git, config=config, ui=ui)

        assert result.target_branch == "feature"
        assert result.previous_branch == "sub-feature"
        assert result.switched is True
        assert git.current_branch == "feature"
