"""Tests for down.py command module using dependency injection."""

import pytest

from panqake.commands.down import down_core
from panqake.ports import BranchNotFoundError, DownResult, UserCancelledError
from panqake.testing import FakeConfig, FakeGit, FakeUI


class TestDownCore:
    """Tests for down_core function."""

    def test_moves_to_single_child(self):
        """Test navigating down to single child branch."""
        git = FakeGit(branches=["main", "feature"], current_branch="main")
        config = FakeConfig(stack={"feature": {"parent": "main"}})
        ui = FakeUI(strict=False)

        result = down_core(git=git, config=config, ui=ui)

        assert result == DownResult(
            target_branch="feature",
            previous_branch="main",
            switched=True,
        )
        assert git.current_branch == "feature"
        assert git.checkout_calls == ["feature"]

    def test_prompts_for_multiple_children(self):
        """Test selection prompt when multiple children exist."""
        git = FakeGit(
            branches=["main", "feature-a", "feature-b", "feature-c"],
            current_branch="main",
        )
        config = FakeConfig(
            stack={
                "feature-a": {"parent": "main"},
                "feature-b": {"parent": "main"},
                "feature-c": {"parent": "main"},
            }
        )
        ui = FakeUI(select_branch_responses=["feature-b"])

        result = down_core(git=git, config=config, ui=ui)

        assert result == DownResult(
            target_branch="feature-b",
            previous_branch="main",
            switched=True,
        )
        assert git.current_branch == "feature-b"
        assert len(ui.select_branch_calls) == 1
        assert "Select a child branch" in ui.select_branch_calls[0][1]

    def test_handles_worktree_branch(self):
        """Test handling when child is in a worktree."""
        git = FakeGit(branches=["main", "feature"], current_branch="main")
        git.worktrees["feature"] = "/path/to/feature-worktree"
        config = FakeConfig(stack={"feature": {"parent": "main"}})
        ui = FakeUI(strict=False)

        result = down_core(git=git, config=config, ui=ui)

        assert result == DownResult(
            target_branch="feature",
            previous_branch="main",
            switched=False,
            worktree_path="/path/to/feature-worktree",
        )
        assert git.current_branch == "main"  # Not switched
        assert git.checkout_calls == []
        assert any("worktree" in msg for msg in ui.info_messages)
        assert any("/path/to/feature-worktree" in msg for msg in ui.info_messages)

    def test_raises_when_no_current_branch(self):
        """Test error when current branch cannot be determined."""
        git = FakeGit(branches=["main"], current_branch=None)
        config = FakeConfig()
        ui = FakeUI(strict=False)

        with pytest.raises(BranchNotFoundError) as exc_info:
            down_core(git=git, config=config, ui=ui)

        assert "Could not determine current branch" in str(exc_info.value)

    def test_raises_when_no_children(self):
        """Test error when current branch has no children."""
        git = FakeGit(branches=["main", "feature"], current_branch="feature")
        config = FakeConfig(stack={"feature": {"parent": "main"}})
        ui = FakeUI(strict=False)

        with pytest.raises(BranchNotFoundError) as exc_info:
            down_core(git=git, config=config, ui=ui)

        assert "has no child branches" in str(exc_info.value)

    def test_raises_when_selection_cancelled(self):
        """Test error when user cancels selection."""
        git = FakeGit(
            branches=["main", "feature-a", "feature-b"],
            current_branch="main",
        )
        config = FakeConfig(
            stack={
                "feature-a": {"parent": "main"},
                "feature-b": {"parent": "main"},
            }
        )
        ui = FakeUI(cancel_on_select_branch=True)

        with pytest.raises(UserCancelledError):
            down_core(git=git, config=config, ui=ui)

        assert git.checkout_calls == []

    def test_raises_when_no_selection(self):
        """Test error when user makes no selection."""
        git = FakeGit(
            branches=["main", "feature-a", "feature-b"],
            current_branch="main",
        )
        config = FakeConfig(
            stack={
                "feature-a": {"parent": "main"},
                "feature-b": {"parent": "main"},
            }
        )
        ui = FakeUI(select_branch_responses=[None])

        with pytest.raises(BranchNotFoundError) as exc_info:
            down_core(git=git, config=config, ui=ui)

        assert "No child branch selected" in str(exc_info.value)

    def test_navigates_through_stack(self):
        """Test navigating down through a multi-level stack."""
        git = FakeGit(
            branches=["main", "feature", "sub-feature"],
            current_branch="feature",
        )
        config = FakeConfig(
            stack={
                "feature": {"parent": "main"},
                "sub-feature": {"parent": "feature"},
            }
        )
        ui = FakeUI(strict=False)

        result = down_core(git=git, config=config, ui=ui)

        assert result.target_branch == "sub-feature"
        assert result.previous_branch == "feature"
        assert result.switched is True
        assert git.current_branch == "sub-feature"

    def test_single_child_no_prompt(self):
        """Test that single child does not trigger selection prompt."""
        git = FakeGit(branches=["main", "feature"], current_branch="main")
        config = FakeConfig(stack={"feature": {"parent": "main"}})
        ui = FakeUI(strict=False)

        down_core(git=git, config=config, ui=ui)

        assert len(ui.select_branch_calls) == 0
