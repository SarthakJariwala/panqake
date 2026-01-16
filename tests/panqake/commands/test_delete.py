"""Tests for delete.py command module using fakes."""

import pytest

from panqake.commands.delete import delete_branch_core
from panqake.ports import (
    BranchNotFoundError,
    CannotDeleteCurrentBranchError,
    InWorktreeBeingDeletedError,
    RebaseConflictError,
    UserCancelledError,
)
from panqake.testing.fakes import FakeConfig, FakeGit, FakeUI


def test_delete_branch_success():
    """Test successful branch deletion with no child branches."""
    git = FakeGit(
        branches=["main", "feature-branch"],
        current_branch="main",
    )
    config = FakeConfig(
        stack={
            "feature-branch": {"parent": "main"},
        }
    )
    ui = FakeUI(confirm_responses=[True])

    result = delete_branch_core(git, config, ui, "feature-branch")

    assert result.deleted_branch == "feature-branch"
    assert result.parent_branch == "main"
    assert result.relinked_children == []
    assert result.removed_from_stack is True
    assert "feature-branch" in git.deleted_local_branches
    assert "feature-branch" not in config.stack


def test_delete_branch_with_children():
    """Test successful branch deletion with child branches that need relinking."""
    git = FakeGit(
        branches=["main", "feature-branch", "child1", "child2"],
        current_branch="main",
    )
    config = FakeConfig(
        stack={
            "feature-branch": {"parent": "main"},
            "child1": {"parent": "feature-branch"},
            "child2": {"parent": "feature-branch"},
        }
    )
    ui = FakeUI(confirm_responses=[True])

    result = delete_branch_core(git, config, ui, "feature-branch")

    assert result.deleted_branch == "feature-branch"
    assert result.parent_branch == "main"
    assert set(result.relinked_children) == {"child1", "child2"}
    assert result.removed_from_stack is True

    assert len(git.rebase_calls) == 2
    for child, base in git.rebase_calls:
        assert base == "main"
        assert child in ["child1", "child2"]

    assert config.get_parent_branch("child1") == "main"
    assert config.get_parent_branch("child2") == "main"


def test_delete_nonexistent_branch():
    """Test error when trying to delete a non-existent branch."""
    git = FakeGit(
        branches=["main"],
        current_branch="main",
    )
    config = FakeConfig()
    ui = FakeUI(confirm_responses=[True])

    with pytest.raises(BranchNotFoundError):
        delete_branch_core(git, config, ui, "nonexistent-branch")

    assert git.deleted_local_branches == []


def test_delete_current_branch():
    """Test error when trying to delete the current branch."""
    git = FakeGit(
        branches=["main", "feature-branch"],
        current_branch="feature-branch",
    )
    config = FakeConfig(
        stack={
            "feature-branch": {"parent": "main"},
        }
    )
    ui = FakeUI(confirm_responses=[True])

    with pytest.raises(CannotDeleteCurrentBranchError):
        delete_branch_core(git, config, ui, "feature-branch")

    assert git.deleted_local_branches == []
    assert "feature-branch" in config.stack


def test_delete_branch_nonexistent_parent():
    """Test error when parent branch doesn't exist."""
    git = FakeGit(
        branches=["main", "feature-branch"],
        current_branch="main",
    )
    config = FakeConfig(
        stack={
            "feature-branch": {"parent": "nonexistent-parent"},
        }
    )
    ui = FakeUI(confirm_responses=[True])

    with pytest.raises(BranchNotFoundError) as exc_info:
        delete_branch_core(git, config, ui, "feature-branch")

    assert "nonexistent-parent" in str(exc_info.value)
    assert git.deleted_local_branches == []


def test_delete_branch_user_cancellation():
    """Test cancellation of branch deletion by user."""
    git = FakeGit(
        branches=["main", "feature-branch"],
        current_branch="main",
    )
    config = FakeConfig(
        stack={
            "feature-branch": {"parent": "main"},
        }
    )
    ui = FakeUI(confirm_responses=[False])

    with pytest.raises(UserCancelledError):
        delete_branch_core(git, config, ui, "feature-branch")

    assert git.deleted_local_branches == []
    assert "feature-branch" in config.stack


def test_delete_branch_no_branch_name_provided():
    """Test branch deletion when no branch name is provided."""
    git = FakeGit(
        branches=["main", "feature-branch", "another-branch"],
        current_branch="main",
    )
    config = FakeConfig(
        stack={
            "feature-branch": {"parent": "main"},
        }
    )
    ui = FakeUI(
        select_branch_responses=["feature-branch"],
        confirm_responses=[True],
    )

    result = delete_branch_core(git, config, ui, branch_name=None)

    assert result.deleted_branch == "feature-branch"
    assert len(ui.select_branch_calls) == 1
    assert "feature-branch" in git.deleted_local_branches


def test_delete_branch_no_selection():
    """Test when user doesn't select a branch."""
    git = FakeGit(
        branches=["main", "feature-branch"],
        current_branch="main",
    )
    config = FakeConfig()
    ui = FakeUI(select_branch_responses=[None])

    with pytest.raises(UserCancelledError):
        delete_branch_core(git, config, ui, branch_name=None)

    assert git.deleted_local_branches == []


def test_delete_branch_no_eligible_branches():
    """Test when only current/protected branches are available."""
    git = FakeGit(
        branches=["main"],
        current_branch="main",
    )
    config = FakeConfig()
    ui = FakeUI()

    result = delete_branch_core(git, config, ui, branch_name=None)

    assert result.status == "skipped"
    assert result.skip_reason == "no_eligible_branches"
    assert result.deleted_branch is None


def test_delete_branch_rebase_conflict():
    """Test error during rebase of child branches."""
    git = FakeGit(
        branches=["main", "feature-branch", "child1"],
        current_branch="main",
    )
    git.fail_rebase = True

    config = FakeConfig(
        stack={
            "feature-branch": {"parent": "main"},
            "child1": {"parent": "feature-branch"},
        }
    )
    ui = FakeUI(confirm_responses=[True])

    with pytest.raises(RebaseConflictError):
        delete_branch_core(git, config, ui, "feature-branch")

    assert git.deleted_local_branches == []
    assert "feature-branch" in config.stack


def test_delete_branch_with_worktree():
    """Test branch deletion with worktree cleanup."""
    git = FakeGit(
        branches=["main", "feature-branch"],
        current_branch="main",
    )
    git.worktrees["feature-branch"] = "/path/to/worktree"

    config = FakeConfig(
        stack={
            "feature-branch": {"parent": "main", "worktree": "/path/to/worktree"},
        }
    )
    ui = FakeUI(confirm_responses=[True])

    result = delete_branch_core(
        git, config, ui, "feature-branch", current_dir="/other/path"
    )

    assert result.deleted_branch == "feature-branch"
    assert result.worktree_removed is True
    assert "/path/to/worktree" in git.removed_worktrees


def test_delete_branch_in_worktree_being_deleted():
    """Test error when in the worktree being deleted."""
    git = FakeGit(
        branches=["main", "feature-branch"],
        current_branch="main",
    )
    git.worktrees["feature-branch"] = "/path/to/worktree"

    config = FakeConfig(
        stack={
            "feature-branch": {"parent": "main", "worktree": "/path/to/worktree"},
        }
    )
    ui = FakeUI(confirm_responses=[True])

    with pytest.raises(InWorktreeBeingDeletedError) as exc_info:
        delete_branch_core(
            git, config, ui, "feature-branch", current_dir="/path/to/worktree"
        )

    assert exc_info.value.worktree_path == "/path/to/worktree"
    assert git.deleted_local_branches == []


def test_delete_branch_not_in_stack():
    """Test deleting a branch that exists in git but not in stack."""
    git = FakeGit(
        branches=["main", "untracked-branch"],
        current_branch="main",
    )
    config = FakeConfig()
    ui = FakeUI(confirm_responses=[True])

    result = delete_branch_core(git, config, ui, "untracked-branch")

    assert result.deleted_branch == "untracked-branch"
    assert result.parent_branch is None
    assert result.relinked_children == []
    assert result.removed_from_stack is False
    assert "untracked-branch" in git.deleted_local_branches


def test_delete_branch_returns_to_original():
    """Test that we return to the original branch after relinking children."""
    git = FakeGit(
        branches=["main", "feature-branch", "child1"],
        current_branch="main",
    )
    config = FakeConfig(
        stack={
            "feature-branch": {"parent": "main"},
            "child1": {"parent": "feature-branch"},
        }
    )
    ui = FakeUI(confirm_responses=[True])

    delete_branch_core(git, config, ui, "feature-branch")

    assert git.current_branch == "main"
