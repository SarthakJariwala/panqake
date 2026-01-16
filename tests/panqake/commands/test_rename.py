"""Tests for rename.py command module using dependency injection."""

import pytest

from panqake.commands.rename import rename_core
from panqake.ports import (
    BranchExistsError,
    BranchNotFoundError,
    RenameResult,
    UserCancelledError,
)
from panqake.testing import FakeConfig, FakeGit, FakeUI


class TestRenameCore:
    """Tests for rename_core function."""

    def test_renames_current_branch(self):
        """Test renaming the current branch."""
        git = FakeGit(branches=["main", "feature"], current_branch="feature")
        config = FakeConfig(stack={"feature": {"parent": "main"}})
        ui = FakeUI(strict=False)

        result = rename_core(
            git=git, config=config, ui=ui, old_name=None, new_name="feature-v2"
        )

        assert result == RenameResult(
            old_name="feature",
            new_name="feature-v2",
            was_tracked=True,
            remote_updated=False,
        )
        assert "feature" not in git.branches
        assert "feature-v2" in git.branches
        assert git.current_branch == "feature-v2"
        assert "feature-v2" in config.stack
        assert "feature" not in config.stack

    def test_renames_specified_branch(self):
        """Test renaming a specified branch (not current)."""
        git = FakeGit(branches=["main", "feature", "other"], current_branch="other")
        config = FakeConfig(stack={"feature": {"parent": "main"}})
        ui = FakeUI(strict=False)

        result = rename_core(
            git=git, config=config, ui=ui, old_name="feature", new_name="feature-v2"
        )

        assert result.old_name == "feature"
        assert result.new_name == "feature-v2"
        assert "feature-v2" in git.branches
        assert "feature" not in git.branches

    def test_prompts_for_new_name(self):
        """Test prompting for new name when not provided."""
        git = FakeGit(branches=["main", "feature"], current_branch="feature")
        config = FakeConfig(stack={"feature": {"parent": "main"}})
        ui = FakeUI(input_responses=["new-feature"])

        result = rename_core(
            git=git, config=config, ui=ui, old_name="feature", new_name=None
        )

        assert result.new_name == "new-feature"
        assert len(ui.input_calls) == 1
        assert "feature" in ui.input_calls[0].message

    def test_updates_remote_when_pushed(self):
        """Test updating remote branch when branch was pushed."""
        git = FakeGit(
            branches=["main", "feature"],
            current_branch="feature",
            pushed_branches={"feature"},
        )
        config = FakeConfig(stack={"feature": {"parent": "main"}})
        ui = FakeUI(strict=False)

        result = rename_core(
            git=git, config=config, ui=ui, old_name="feature", new_name="feature-v2"
        )

        assert result.remote_updated is True
        assert "feature" in git.deleted_remote_branches
        assert ("feature-v2", False) in git.push_calls

    def test_handles_untracked_branch(self):
        """Test renaming a branch not tracked by panqake."""
        git = FakeGit(branches=["main", "feature"], current_branch="feature")
        config = FakeConfig()  # No stack entries
        ui = FakeUI(strict=False)

        result = rename_core(
            git=git, config=config, ui=ui, old_name="feature", new_name="feature-v2"
        )

        assert result.was_tracked is False
        assert "feature-v2" in git.branches

    def test_updates_child_parent_references(self):
        """Test that child branches' parent references are updated."""
        git = FakeGit(
            branches=["main", "feature", "child"],
            current_branch="feature",
        )
        config = FakeConfig(
            stack={
                "feature": {"parent": "main"},
                "child": {"parent": "feature"},
            }
        )
        ui = FakeUI(strict=False)

        rename_core(
            git=git, config=config, ui=ui, old_name="feature", new_name="feature-v2"
        )

        assert config.get_parent_branch("child") == "feature-v2"

    def test_raises_when_no_current_branch(self):
        """Test error when current branch cannot be determined."""
        git = FakeGit(branches=["main"], current_branch=None)
        config = FakeConfig()
        ui = FakeUI(strict=False)

        with pytest.raises(BranchNotFoundError) as exc_info:
            rename_core(git=git, config=config, ui=ui, old_name=None, new_name="new")

        assert "Could not determine" in str(exc_info.value)

    def test_raises_when_branch_not_found(self):
        """Test error when specified branch doesn't exist."""
        git = FakeGit(branches=["main"], current_branch="main")
        config = FakeConfig()
        ui = FakeUI(strict=False)

        with pytest.raises(BranchNotFoundError):
            rename_core(
                git=git, config=config, ui=ui, old_name="nonexistent", new_name="new"
            )

    def test_raises_when_new_name_exists(self):
        """Test error when new name already exists."""
        git = FakeGit(
            branches=["main", "feature", "existing"], current_branch="feature"
        )
        config = FakeConfig()
        ui = FakeUI(strict=False)

        with pytest.raises(BranchExistsError):
            rename_core(
                git=git, config=config, ui=ui, old_name="feature", new_name="existing"
            )

    def test_raises_when_user_cancels(self):
        """Test error when user cancels input prompt."""
        git = FakeGit(branches=["main", "feature"], current_branch="feature")
        config = FakeConfig()
        ui = FakeUI(cancel_on_input=True)

        with pytest.raises(UserCancelledError):
            rename_core(
                git=git, config=config, ui=ui, old_name="feature", new_name=None
            )

    def test_preserves_worktree_path(self):
        """Test that worktree path is preserved after rename."""
        git = FakeGit(branches=["main", "feature"], current_branch="feature")
        git.worktrees["feature"] = "/path/to/worktree"
        config = FakeConfig(
            stack={"feature": {"parent": "main", "worktree": "/path/to/worktree"}}
        )
        ui = FakeUI(strict=False)

        rename_core(
            git=git, config=config, ui=ui, old_name="feature", new_name="feature-v2"
        )

        assert git.worktrees.get("feature-v2") == "/path/to/worktree"
        assert "feature" not in git.worktrees
