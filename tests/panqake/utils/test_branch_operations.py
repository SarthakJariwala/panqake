"""Tests for branch_operations.py module."""

from unittest.mock import MagicMock, patch

import pytest

from panqake.utils.branch_operations import (
    fetch_latest_from_remote,
    push_updated_branches,
    return_to_branch,
    update_branch_with_conflict_detection,
)


@pytest.fixture
def mock_git_utils():
    """Mock git utility functions."""
    with (
        patch("panqake.utils.branch_operations.branch_exists") as mock_exists,
        patch("panqake.utils.branch_operations.checkout_branch") as mock_checkout,
        patch("panqake.utils.branch_operations.run_git_command") as mock_run,
        patch(
            "panqake.utils.branch_operations.run_git_command_for_branch_context"
        ) as mock_run_git_for_context,
        patch("panqake.utils.branch_operations.is_branch_worktree") as mock_is_worktree,
    ):
        yield {
            "exists": mock_exists,
            "checkout": mock_checkout,
            "run": mock_run,
            "run_git_for_context": mock_run_git_for_context,
            "is_worktree": mock_is_worktree,
        }


@pytest.fixture
def mock_prompt():
    """Mock questionary prompt functions."""
    with (
        patch("panqake.utils.branch_operations.format_branch") as mock_format,
        patch("panqake.utils.branch_operations.print_formatted_text") as mock_print,
        patch("panqake.utils.branch_operations.status") as mock_status,
    ):
        mock_format.side_effect = lambda branch: f"[formatted]{branch}[/formatted]"
        # Make status context manager return a mock that calls print_formatted_text directly
        mock_status_obj = MagicMock()
        mock_status_obj.pause_and_print = mock_print
        mock_status_obj.update = MagicMock()
        mock_status.return_value.__enter__.return_value = mock_status_obj
        mock_status.return_value.__exit__.return_value = None
        yield {
            "format": mock_format,
            "print": mock_print,
            "status": mock_status,
        }


def test_update_branch_success(mock_git_utils, mock_prompt):
    """Test successful branch update."""
    mock_git_utils["is_worktree"].return_value = False  # Normal branch
    mock_git_utils["run_git_for_context"].return_value = "Success"

    success, error = update_branch_with_conflict_detection("feature", "main")

    assert success is True
    assert error is None
    mock_git_utils["checkout"].assert_called_once_with("feature")
    mock_git_utils["run_git_for_context"].assert_called_with(
        "feature", ["rebase", "--autostash", "main"]
    )
    mock_prompt["print"].assert_called_once()


def test_update_branch_checkout_failure(mock_git_utils, mock_prompt):
    """Test branch update with checkout failure."""
    mock_git_utils["is_worktree"].return_value = False  # Normal branch
    mock_git_utils["checkout"].side_effect = SystemExit(1)

    success, error = update_branch_with_conflict_detection("feature", "main")

    assert success is False
    assert error is not None and "Failed to checkout" in error
    mock_git_utils["run_git_for_context"].assert_not_called()


def test_update_branch_conflict_abort(mock_git_utils, mock_prompt):
    """Test branch update with conflict and abort."""
    # Simulate rebase failure (returns None), then abort success (returns string)
    mock_git_utils["is_worktree"].return_value = False  # Normal branch
    mock_git_utils["run_git_for_context"].side_effect = [None, "Rebase aborted"]

    success, error = update_branch_with_conflict_detection("feature", "main")

    assert success is False
    assert error is not None and "conflict detected" in error
    # Ensure checkout, rebase, and abort were called in order
    mock_git_utils["checkout"].assert_called_once_with("feature")
    calls = mock_git_utils["run_git_for_context"].call_args_list
    assert len(calls) == 2
    assert calls[0].args == ("feature", ["rebase", "--autostash", "main"])
    assert calls[1].args == ("feature", ["rebase", "--abort"])


def test_update_branch_conflict_no_abort(mock_git_utils, mock_prompt):
    """Test branch update with conflict without abort."""
    mock_git_utils["is_worktree"].return_value = False  # Normal branch
    mock_git_utils["run_git_for_context"].return_value = None  # Rebase fails

    success, error = update_branch_with_conflict_detection(
        "feature", "main", abort_on_conflict=False
    )

    assert success is False
    assert error is not None and "resolve conflicts" in error
    # Should not abort the rebase
    calls = mock_git_utils["run_git_for_context"].call_args_list
    assert len(calls) == 1  # Only the rebase call, no abort
    assert calls[0].args == ("feature", ["rebase", "--autostash", "main"])


def test_update_worktree_branch_success(mock_git_utils, mock_prompt):
    """Test successful worktree branch update."""
    mock_git_utils["is_worktree"].return_value = True  # Worktree branch
    mock_git_utils["run_git_for_context"].side_effect = [
        "feature",
        "Success",
    ]  # HEAD check, then rebase

    success, error = update_branch_with_conflict_detection("feature", "main")

    assert success is True
    assert error is None
    # Should not call checkout for worktree branches
    mock_git_utils["checkout"].assert_not_called()
    # Should verify HEAD and run rebase in worktree directory
    calls = mock_git_utils["run_git_for_context"].call_args_list
    assert len(calls) == 2
    assert calls[0].args == ("feature", ["rev-parse", "--abbrev-ref", "HEAD"])
    assert calls[1].args == ("feature", ["rebase", "--autostash", "main"])
    mock_prompt["print"].assert_called_once()


def test_update_worktree_branch_wrong_head(mock_git_utils, mock_prompt):
    """Test worktree branch update when HEAD is on wrong branch."""
    mock_git_utils["is_worktree"].return_value = True  # Worktree branch
    mock_git_utils[
        "run_git_for_context"
    ].return_value = "main"  # HEAD is on main, not feature

    success, error = update_branch_with_conflict_detection("feature", "main")

    assert success is False
    assert error is not None and "not on the correct branch" in error
    # Should not call checkout or rebase
    mock_git_utils["checkout"].assert_not_called()
    # Should only check HEAD
    calls = mock_git_utils["run_git_for_context"].call_args_list
    assert len(calls) == 1
    assert calls[0].args == ("feature", ["rev-parse", "--abbrev-ref", "HEAD"])


def test_fetch_latest_success(mock_git_utils, mock_prompt):
    """Test successful fetch and pull."""
    mock_git_utils["run"].side_effect = [
        "Fetched",  # fetch
        "Pulled",  # pull
        "abc123",  # rev-parse
    ]

    success = fetch_latest_from_remote("feature")

    assert success is True
    mock_git_utils["run"].assert_any_call(["fetch", "origin"])
    mock_git_utils["run"].assert_any_call(["pull", "origin", "feature"])
    mock_git_utils["run"].assert_any_call(["rev-parse", "HEAD"])


def test_fetch_latest_fetch_failure(mock_git_utils, mock_prompt):
    """Test fetch failure."""
    mock_git_utils["run"].return_value = None

    success = fetch_latest_from_remote("feature")

    assert success is False
    mock_git_utils["run"].assert_called_once_with(["fetch", "origin"])
    mock_prompt["print"].assert_called_with(
        "[warning]Error: Failed to fetch from remote[/warning]"
    )


def test_fetch_latest_checkout_failure(mock_git_utils, mock_prompt):
    """Test fetch with checkout failure."""
    mock_git_utils["run"].return_value = "Fetched"
    mock_git_utils["checkout"].side_effect = SystemExit(1)

    success = fetch_latest_from_remote("feature")

    assert success is False
    mock_git_utils["checkout"].assert_called_once_with("feature")


def test_fetch_latest_pull_failure(mock_git_utils, mock_prompt):
    """Test fetch with pull failure."""
    mock_git_utils["run"].side_effect = ["Fetched", None]

    success = fetch_latest_from_remote("feature", current_branch="main")

    assert success is False
    mock_git_utils["run"].assert_any_call(["pull", "origin", "feature"])
    mock_git_utils["checkout"].assert_called_with("main")


def test_return_to_branch_success(mock_git_utils, mock_prompt):
    """Test successful return to target branch."""
    mock_git_utils["exists"].return_value = True

    success = return_to_branch("feature")

    assert success is True
    mock_git_utils["checkout"].assert_called_once_with("feature")


def test_return_to_branch_deleted(mock_git_utils, mock_prompt):
    """Test return to fallback when target deleted."""
    mock_git_utils["exists"].side_effect = [
        False,
        True,
    ]  # target doesn't exist, fallback does

    success = return_to_branch("feature", fallback_branch="main")

    assert success is True
    mock_git_utils["checkout"].assert_called_once_with("main")


def test_return_to_branch_all_missing(mock_git_utils, mock_prompt):
    """Test handling when all branches missing."""
    mock_git_utils["exists"].return_value = False

    success = return_to_branch("feature", fallback_branch="main")

    assert success is False
    mock_git_utils["checkout"].assert_not_called()
    mock_prompt["print"].assert_called_with(
        "[warning]Error: Unable to find a valid branch to return to[/warning]"
    )


def test_return_to_branch_checkout_failure(mock_git_utils, mock_prompt):
    """Test handling checkout failure."""
    mock_git_utils["exists"].return_value = True
    mock_git_utils["checkout"].side_effect = SystemExit(1)

    success = return_to_branch("feature")

    assert success is False


@patch("panqake.utils.branch_operations.is_branch_worktree")
@patch("panqake.utils.branch_operations.is_branch_pushed_to_remote")
@patch("panqake.utils.branch_operations.has_unpushed_changes")
@patch("panqake.utils.branch_operations.push_branch_to_remote")
@patch("panqake.utils.branch_operations.checkout_branch")
def test_push_updated_branches_with_changes(
    mock_checkout,
    mock_push,
    mock_has_changes,
    mock_is_pushed,
    mock_is_worktree,
    mock_prompt,
):
    """Test pushing branches with changes."""
    # Setup mocks for a branch that exists on remote and has changes
    mock_is_pushed.return_value = True
    mock_has_changes.return_value = True
    mock_is_worktree.return_value = False
    mock_push.return_value = True

    branches = ["feature1", "feature2"]
    result = push_updated_branches(branches)

    assert result == branches
    assert mock_checkout.call_count == 2
    assert mock_push.call_count == 2
    # Verify correct args were passed
    mock_push.assert_any_call("feature1", force_with_lease=True)
    mock_push.assert_any_call("feature2", force_with_lease=True)


@patch("panqake.utils.branch_operations.is_branch_worktree")
@patch("panqake.utils.branch_operations.is_branch_pushed_to_remote")
@patch("panqake.utils.branch_operations.has_unpushed_changes")
@patch("panqake.utils.branch_operations.push_branch_to_remote")
@patch("panqake.utils.branch_operations.checkout_branch")
def test_push_updated_branches_no_changes(
    mock_checkout,
    mock_push,
    mock_has_changes,
    mock_is_pushed,
    mock_is_worktree,
    mock_prompt,
):
    """Test skipping branches with no changes."""
    # Setup mocks for a branch that exists on remote but has no changes
    mock_is_pushed.return_value = True
    mock_has_changes.return_value = False
    mock_is_worktree.return_value = False

    branches = ["feature1", "feature2"]
    result = push_updated_branches(branches)

    assert result == []
    # Shouldn't even attempt to checkout or push
    mock_checkout.assert_not_called()
    mock_push.assert_not_called()


@patch("panqake.utils.branch_operations.is_branch_worktree")
@patch("panqake.utils.branch_operations.is_branch_pushed_to_remote")
@patch("panqake.utils.branch_operations.has_unpushed_changes")
@patch("panqake.utils.branch_operations.push_branch_to_remote")
@patch("panqake.utils.branch_operations.checkout_branch")
def test_push_updated_branches_mixed_status(
    mock_checkout,
    mock_push,
    mock_has_changes,
    mock_is_pushed,
    mock_is_worktree,
    mock_prompt,
):
    """Test pushing with mixed branch statuses."""
    # Branch 1: On remote, has changes
    # Branch 2: Not on remote yet
    # Branch 3: On remote, no changes
    # Branch 4: On remote, has changes but push fails
    mock_is_pushed.side_effect = [True, False, True, True]
    mock_has_changes.side_effect = [True, True, False, True]
    mock_is_worktree.return_value = False
    mock_push.side_effect = [True, False]  # Branch 4 push fails

    branches = ["feature1", "feature2", "feature3", "feature4"]
    result = push_updated_branches(branches)

    # Only feature1 should be successfully pushed
    assert result == ["feature1"]
    assert mock_checkout.call_count == 2  # Only for feature1 and feature4
    assert mock_push.call_count == 2  # Only for feature1 and feature4


@patch("panqake.utils.branch_operations.run_git_command_for_branch_context")
@patch("panqake.utils.branch_operations.is_branch_worktree")
@patch("panqake.utils.branch_operations.is_branch_pushed_to_remote")
@patch("panqake.utils.branch_operations.has_unpushed_changes")
@patch("panqake.utils.branch_operations.push_branch_to_remote")
@patch("panqake.utils.branch_operations.checkout_branch")
def test_push_updated_branches_worktree_branch(
    mock_checkout,
    mock_push,
    mock_has_changes,
    mock_is_pushed,
    mock_is_worktree,
    mock_run_for_context,
    mock_prompt,
):
    """Test pushing a worktree branch without checkout."""
    mock_is_pushed.return_value = True
    mock_has_changes.return_value = True
    mock_is_worktree.return_value = True
    mock_run_for_context.return_value = "feature1"
    mock_push.return_value = True

    branches = ["feature1"]
    result = push_updated_branches(branches)

    assert result == ["feature1"]
    mock_checkout.assert_not_called()
    mock_run_for_context.assert_called_once_with(
        "feature1", ["rev-parse", "--abbrev-ref", "HEAD"], silent_fail=True
    )
    mock_push.assert_called_once_with("feature1", force_with_lease=True)
