"""Tests for the new command."""

from unittest.mock import patch

import pytest

from panqake.commands.new import create_new_branch


@pytest.fixture
def mock_git_functions():
    """Mock git functions for testing."""
    with (
        patch("panqake.commands.new.get_current_branch") as mock_get_current,
        patch("panqake.commands.new.branch_exists") as mock_branch_exists,
        patch("panqake.commands.new.run_git_command") as mock_run_git,
        patch("panqake.commands.new.add_to_stack") as mock_add_to_stack,
        patch("panqake.commands.new.list_all_branches") as mock_list_branches,
        patch("panqake.commands.new.prompt_input") as mock_prompt_input,
    ):
        # Set default return values
        mock_get_current.return_value = "main"
        mock_branch_exists.side_effect = lambda branch: branch == "main"
        mock_run_git.return_value = "Switched to a new branch"
        mock_list_branches.return_value = ["main", "develop"]

        yield {
            "get_current_branch": mock_get_current,
            "branch_exists": mock_branch_exists,
            "run_git_command": mock_run_git,
            "add_to_stack": mock_add_to_stack,
            "list_all_branches": mock_list_branches,
            "prompt_input": mock_prompt_input,
        }


def test_create_new_branch_with_args(mock_git_functions):
    """Test creating a new branch when args are provided."""
    create_new_branch("feature-branch", "main")

    # Should not prompt for input
    mock_git_functions["prompt_input"].assert_not_called()

    # Should check if branches exist
    mock_git_functions["branch_exists"].assert_any_call("feature-branch")
    mock_git_functions["branch_exists"].assert_any_call("main")

    # Should create branch and add to stack
    mock_git_functions["run_git_command"].assert_called_once_with(
        ["checkout", "-b", "feature-branch", "main"]
    )
    mock_git_functions["add_to_stack"].assert_called_once_with(
        "feature-branch", "main"
    )


def test_create_new_branch_interactive(mock_git_functions):
    """Test creating a new branch interactively."""
    # Simulate user input
    mock_git_functions["prompt_input"].side_effect = ["feature-branch", "main"]

    # Call function without args
    create_new_branch()

    # Should prompt for branch name and base branch
    assert mock_git_functions["prompt_input"].call_count == 2

    # Should create branch and add to stack
    mock_git_functions["run_git_command"].assert_called_once_with(
        ["checkout", "-b", "feature-branch", "main"]
    )
    mock_git_functions["add_to_stack"].assert_called_once_with(
        "feature-branch", "main"
    )
