"""Tests for up.py command module."""

from unittest.mock import patch

import pytest

from panqake.commands.up import up


@pytest.fixture
def mock_git_utils():
    """Mock git utility functions."""
    with (
        patch("panqake.commands.up.checkout_branch") as mock_checkout,
        patch("panqake.commands.up.get_current_branch") as mock_current,
    ):
        mock_current.return_value = "feature"
        yield {
            "checkout": mock_checkout,
            "current": mock_current,
        }


@pytest.fixture
def mock_stacks():
    """Mock Stacks class."""
    with patch("panqake.commands.up.Stacks") as mock_stacks_class:
        mock_stacks_instance = mock_stacks_class.return_value
        mock_stacks_instance.__enter__.return_value = mock_stacks_instance
        yield mock_stacks_instance


@pytest.fixture
def mock_print():
    """Mock print_formatted_text function."""
    with patch("panqake.commands.up.print_formatted_text") as mock_print:
        yield mock_print


def test_up_with_parent(mock_git_utils, mock_stacks, mock_print):
    """Test navigating up to parent branch."""
    # Set up mock to return a parent branch
    mock_stacks.get_parent.return_value = "main"

    # Run the command
    up()

    # Check that we queried for the parent of the current branch
    mock_stacks.get_parent.assert_called_once_with("feature")

    # Check that we checked out the parent branch
    mock_git_utils["checkout"].assert_called_once_with("main")

    # Check that we printed a message
    mock_print.assert_called_once()
    assert "Moving up to parent branch" in mock_print.call_args.args[0]


def test_up_without_parent(mock_git_utils, mock_stacks, mock_print):
    """Test error when current branch has no parent."""
    # Set up mock to return no parent branch
    mock_stacks.get_parent.return_value = ""

    # Run the command, should exit with code 1
    with pytest.raises(SystemExit) as excinfo:
        up()
    assert excinfo.value.code == 1

    # Check that we queried for the parent of the current branch
    mock_stacks.get_parent.assert_called_once_with("feature")

    # Check that we didn't check out any branch
    mock_git_utils["checkout"].assert_not_called()

    # Check that we printed an error message
    mock_print.assert_called_once()
    assert "has no parent branch" in mock_print.call_args.args[0]
