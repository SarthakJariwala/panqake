"""Simplified tests for the PR command focusing on basic functionality."""

import subprocess
from unittest.mock import patch

import pytest

from panqake.commands.pr import create_pull_requests


@pytest.fixture
def mock_dependencies():
    """Mock dependencies for PR command testing with minimal needed mocks."""
    with (
        patch("panqake.commands.pr.shutil.which") as mock_which,
        patch("panqake.commands.pr.get_current_branch") as mock_get_current,
        patch("panqake.commands.pr.branch_exists") as mock_branch_exists,
        patch("panqake.commands.pr.print_formatted_text") as mock_print,
        patch("panqake.commands.pr.sys.exit") as mock_exit,
    ):
        # Set default return values
        mock_which.return_value = "/usr/bin/gh"  # Mock GitHub CLI available
        mock_get_current.return_value = "feature"
        mock_branch_exists.return_value = True

        yield {
            "which": mock_which,
            "get_current_branch": mock_get_current,
            "branch_exists": mock_branch_exists,
            "print": mock_print,
            "exit": mock_exit,
        }


def test_missing_github_cli(mock_dependencies):
    """Test error handling when GitHub CLI is not installed."""
    # Setup
    mock_dependencies["which"].return_value = None

    # Execute - don't actually run the command since it has side effects
    with patch("panqake.commands.pr.subprocess"):
        # Skip execution with a safe exit
        with patch.object(
            mock_dependencies["exit"], "__call__", side_effect=SystemExit
        ):
            try:
                create_pull_requests()
            except SystemExit:
                pass

    # Verify
    assert any(
        "required but not installed" in str(call[0][0])
        for call in mock_dependencies["print"].call_args_list
    )
    assert mock_dependencies["exit"].called


def test_nonexistent_branch(mock_dependencies):
    """Test error handling when specified branch doesn't exist."""
    # Setup
    mock_dependencies["branch_exists"].return_value = False

    # Execute - add patch for subprocess to ensure it's not actually executed
    with patch("panqake.commands.pr.subprocess"):
        # Safely trigger the intended failure
        with patch.object(
            mock_dependencies["exit"], "__call__", side_effect=SystemExit
        ):
            try:
                create_pull_requests("nonexistent")
            except SystemExit:
                pass
            except Exception:  # Use explicit exception type
                # Ignore any other exceptions that might occur
                pass

    # Verify
    assert any(
        "does not exist" in str(call[0][0])
        for call in mock_dependencies["print"].call_args_list
    )
    assert mock_dependencies["exit"].called


def test_pr_creation_basic(mock_dependencies):
    """Test the basic start of PR creation."""
    # Setup - we can't fully test PR creation without mocking a lot of nested calls
    # This test just ensures the branch checking logic works
    mock_dependencies["get_current_branch"].return_value = "feature"

    # We need to patch subprocess to avoid actual subprocess calls
    with patch("panqake.commands.pr.subprocess.run") as mock_subprocess:
        # Make subprocess.run raise CalledProcessError to skip PR creation
        mock_subprocess.side_effect = subprocess.CalledProcessError(1, ["gh"])

        try:
            # Execute - will fail due to missing gh command, but we just test the branch check
            create_pull_requests("feature")
        except Exception:  # Use explicit exception type
            # Ignore any exceptions from the mocked subprocess
            pass

    # Verify the branch existence was checked
    mock_dependencies["branch_exists"].assert_called_with("feature")
