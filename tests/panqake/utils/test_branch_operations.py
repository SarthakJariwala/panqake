"""Tests for branch_operations.py module."""

from unittest.mock import patch

import pytest

from panqake.utils.branch_operations import (
    fetch_latest_from_remote,
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
    ):
        yield {
            "exists": mock_exists,
            "checkout": mock_checkout,
            "run": mock_run,
        }


@pytest.fixture
def mock_prompt():
    """Mock questionary prompt functions."""
    with (
        patch("panqake.utils.branch_operations.format_branch") as mock_format,
        patch("panqake.utils.branch_operations.print_formatted_text") as mock_print,
    ):
        mock_format.side_effect = lambda branch: f"[formatted]{branch}[/formatted]"
        yield {
            "format": mock_format,
            "print": mock_print,
        }


def test_update_branch_success(mock_git_utils, mock_prompt):
    """Test successful branch update."""
    mock_git_utils["run"].return_value = "Success"

    success, error = update_branch_with_conflict_detection("feature", "main")

    assert success is True
    assert error is None
    mock_git_utils["checkout"].assert_called_once_with("feature")
    mock_git_utils["run"].assert_called_with(["rebase", "main"])
    mock_prompt["print"].assert_called_once()


def test_update_branch_checkout_failure(mock_git_utils, mock_prompt):
    """Test branch update with checkout failure."""
    mock_git_utils["checkout"].side_effect = SystemExit(1)

    success, error = update_branch_with_conflict_detection("feature", "main")

    assert success is False
    assert "Failed to checkout" in error
    mock_git_utils["run"].assert_not_called()


def test_update_branch_conflict_abort(mock_git_utils, mock_prompt):
    """Test branch update with conflict and abort."""
    # Simulate rebase failure (returns None), then abort success (returns string)
    mock_git_utils["run"].side_effect = [None, "Rebase aborted"]

    success, error = update_branch_with_conflict_detection("feature", "main")

    assert success is False
    assert "conflict detected" in error
    # Ensure checkout, rebase, and abort were called in order
    mock_git_utils["checkout"].assert_called_once_with("feature")
    calls = mock_git_utils["run"].call_args_list
    assert len(calls) == 2
    assert calls[0].args[0] == ["rebase", "main"]
    assert calls[1].args[0] == ["rebase", "--abort"]


def test_update_branch_conflict_no_abort(mock_git_utils, mock_prompt):
    """Test branch update with conflict without abort."""
    mock_git_utils["run"].return_value = None  # Rebase fails

    success, error = update_branch_with_conflict_detection(
        "feature", "main", abort_on_conflict=False
    )

    assert success is False
    assert "resolve conflicts" in error
    # Should not abort the rebase
    assert ["rebase", "--abort"] not in mock_git_utils["run"].call_args_list


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
