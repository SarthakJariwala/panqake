"""Tests for the switch command."""

from unittest.mock import MagicMock, patch

import pytest

from panqake.commands.switch import switch_branch


@pytest.fixture
def mock_git_functions():
    """Mock git functions used by the switch command."""
    with (
        patch("panqake.commands.switch.list_all_branches") as mock_list_branches,
        patch("panqake.commands.switch.get_current_branch") as mock_current_branch,
        patch("panqake.commands.switch.run_git_command") as mock_run_git,
        patch("panqake.commands.switch.print_formatted_text") as mock_print,
    ):
        # Set up default return values
        mock_list_branches.return_value = ["main", "feature1", "feature2"]
        mock_current_branch.return_value = "main"
        mock_run_git.return_value = "Switched to branch 'feature1'"

        yield {
            "list_branches": mock_list_branches,
            "current_branch": mock_current_branch,
            "run_git": mock_run_git,
            "print": mock_print,
        }


@pytest.fixture
def mock_questionary():
    """Mock questionary select function."""
    with patch("questionary.select") as mock_select:
        mock_ask = MagicMock()
        mock_ask.ask.return_value = "feature1"
        mock_select.return_value = mock_ask
        yield mock_select


def test_switch_branch_with_arg(mock_git_functions):
    """Test switching branch with a branch name argument."""
    # Call the function with a branch name
    switch_branch("feature1")

    # Verify git checkout was called with the correct branch
    mock_git_functions["run_git"].assert_called_once_with(["checkout", "feature1"])

    # Verify success message was printed
    mock_git_functions["print"].assert_any_call(
        "<success>Successfully switched to branch 'feature1'</success>"
    )


def test_switch_branch_interactive(mock_git_functions, mock_questionary):
    """Test interactive branch switching."""
    # Call the function without a branch name to trigger interactive mode
    switch_branch()

    # Verify questionary was called with the right options
    mock_questionary.assert_called_once()

    # Verify git checkout was called with the selected branch
    mock_git_functions["run_git"].assert_called_once_with(["checkout", "feature1"])


def test_switch_to_current_branch(mock_git_functions):
    """Test switching to the current branch does nothing."""
    # Set current branch to main
    mock_git_functions["current_branch"].return_value = "main"

    # Try to switch to main
    switch_branch("main")

    # Verify git checkout was NOT called
    mock_git_functions["run_git"].assert_not_called()

    # Verify appropriate message was printed
    mock_git_functions["print"].assert_called_once_with(
        "<info>Already on branch 'main'</info>"
    )


def test_switch_to_nonexistent_branch(mock_git_functions):
    """Test attempting to switch to a nonexistent branch."""
    with pytest.raises(SystemExit):
        switch_branch("nonexistent")

    # Verify error message was printed
    mock_git_functions["print"].assert_called_once_with(
        "<warning>Error: Branch 'nonexistent' does not exist</warning>"
    )

    # Verify git checkout was NOT called
    mock_git_functions["run_git"].assert_not_called()


def test_checkout_failure(mock_git_functions):
    """Test handling of checkout failure."""
    # Set run_git_command to return None (indicating failure)
    mock_git_functions["run_git"].return_value = None

    # Attempt to switch branch, should exit with error
    with pytest.raises(SystemExit):
        switch_branch("feature1")

    # Verify error message was printed
    mock_git_functions["print"].assert_any_call(
        "<danger>Failed to switch branches</danger>"
    )
