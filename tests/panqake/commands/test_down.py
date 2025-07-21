"""Tests for down.py command module."""

from unittest.mock import patch

import pytest

from panqake.commands.down import down


@pytest.fixture
def mock_git_utils():
    """Mock git utility functions."""
    with (
        patch("panqake.commands.down.switch_to_branch_or_worktree") as mock_checkout,
        patch("panqake.commands.down.get_current_branch") as mock_current,
    ):
        mock_current.return_value = "main"
        yield {
            "checkout": mock_checkout,
            "current": mock_current,
        }


@pytest.fixture
def mock_stacks():
    """Mock Stacks class."""
    with patch("panqake.commands.down.Stacks") as mock_stacks_class:
        mock_stacks_instance = mock_stacks_class.return_value
        mock_stacks_instance.__enter__.return_value = mock_stacks_instance
        yield mock_stacks_instance


@pytest.fixture
def mock_prompt():
    """Mock questionary_prompt functions."""
    with (
        patch("panqake.commands.down.print_formatted_text") as mock_print,
        patch("panqake.commands.down.prompt_select") as mock_select,
    ):
        yield {
            "print": mock_print,
            "select": mock_select,
        }


def test_down_with_single_child(mock_git_utils, mock_stacks, mock_prompt):
    """Test navigating down to single child branch."""
    # Set up mock to return a single child branch
    mock_stacks.get_children.return_value = ["feature"]

    # Run the command
    down()

    # Check that we queried for the children of the current branch
    mock_stacks.get_children.assert_called_once_with("main")

    # Check that we checked out the child branch
    mock_git_utils["checkout"].assert_called_once_with("feature", "child branch")

    # Check that we printed a message
    mock_prompt["print"].assert_called_once()
    assert "Moving down to child branch" in mock_prompt["print"].call_args.args[0]

    # Check that we didn't use select prompt
    mock_prompt["select"].assert_not_called()


def test_down_with_multiple_children(mock_git_utils, mock_stacks, mock_prompt):
    """Test navigating down with selection when multiple children exist."""
    # Set up mock to return multiple child branches
    mock_stacks.get_children.return_value = ["feature-a", "feature-b", "feature-c"]

    # Set up mock to return a selected branch
    mock_prompt["select"].return_value = "feature-b"

    # Run the command
    down()

    # Check that we queried for the children of the current branch
    mock_stacks.get_children.assert_called_once_with("main")

    # Check that we prompted for selection
    mock_prompt["print"].assert_called()
    assert "has multiple children" in mock_prompt["print"].call_args_list[0].args[0]

    # Verify prompt select arguments
    mock_prompt["select"].assert_called_once()
    assert "Select a child branch" in mock_prompt["select"].call_args.args[0]
    choices = mock_prompt["select"].call_args.args[1]
    assert len(choices) == 3
    assert [c["value"] for c in choices] == ["feature-a", "feature-b", "feature-c"]

    # Check that we checked out the selected branch
    mock_git_utils["checkout"].assert_called_once_with("feature-b", "child branch")


def test_down_with_multiple_children_cancel(mock_git_utils, mock_stacks, mock_prompt):
    """Test cancelling selection when navigating down with multiple children."""
    # Set up mock to return multiple child branches
    mock_stacks.get_children.return_value = ["feature-a", "feature-b"]

    # Set up mock to simulate cancellation (return None)
    mock_prompt["select"].return_value = None

    # Run the command
    down()

    # Check that we queried for the children of the current branch
    mock_stacks.get_children.assert_called_once_with("main")

    # Check that we prompted for selection
    mock_prompt["select"].assert_called_once()

    # Check that we didn't check out any branch
    mock_git_utils["checkout"].assert_not_called()


def test_down_without_children(mock_git_utils, mock_stacks, mock_prompt):
    """Test error when current branch has no children."""
    # Set up mock to return no children
    mock_stacks.get_children.return_value = []

    # Run the command, should exit with code 1
    with pytest.raises(SystemExit) as excinfo:
        down()
    assert excinfo.value.code == 1

    # Check that we queried for the children of the current branch
    mock_stacks.get_children.assert_called_once_with("main")

    # Check that we didn't check out any branch
    mock_git_utils["checkout"].assert_not_called()

    # Check that we printed an error message
    mock_prompt["print"].assert_called_once()
    assert "has no child branches" in mock_prompt["print"].call_args.args[0]
