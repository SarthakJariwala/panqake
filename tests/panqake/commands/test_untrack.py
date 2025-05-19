"""Tests for untrack.py command module."""

from unittest.mock import patch

import pytest

from panqake.commands.untrack import untrack


@pytest.fixture
def mock_git_utils():
    """Mock git utility functions."""
    with patch("panqake.commands.untrack.get_current_branch") as mock_current:
        mock_current.return_value = "feature-branch"
        yield mock_current


@pytest.fixture
def mock_config_utils():
    """Mock config utility functions."""
    with patch("panqake.commands.untrack.remove_from_stack") as mock_remove:
        yield mock_remove


@pytest.fixture
def mock_prompt():
    """Mock questionary prompt functions."""
    with patch("panqake.commands.untrack.print_formatted_text") as mock_print:
        yield mock_print


def test_untrack_current_branch(mock_git_utils, mock_config_utils, mock_prompt):
    """Test untracking current branch when no branch name is provided."""
    # Execute
    untrack()

    # Verify
    mock_git_utils.assert_called_once()
    mock_config_utils.assert_called_once_with("feature-branch")


def test_untrack_specified_branch(mock_git_utils, mock_config_utils, mock_prompt):
    """Test untracking a specified branch name."""
    # Setup
    mock_config_utils.return_value = True  # Successful removal

    # Execute
    untrack("test-branch")

    # Verify
    mock_git_utils.assert_not_called()
    mock_config_utils.assert_called_once_with("test-branch")


def test_untrack_no_current_branch(mock_git_utils, mock_config_utils, mock_prompt):
    """Test error when current branch cannot be determined."""
    # Setup
    mock_git_utils.return_value = None

    # Execute and verify
    with pytest.raises(SystemExit):
        untrack()

    # Verify no further operations were performed
    mock_config_utils.assert_not_called()


def test_untrack_success_messages(mock_git_utils, mock_config_utils, mock_prompt):
    """Test success messages are printed correctly."""
    # Execute
    untrack("test-branch")

    # Verify appropriate messages were printed
    assert mock_prompt.call_count >= 2
    success_call = mock_prompt.call_args_list[-1]
    assert "Successfully" in success_call.args[0]
    assert "test-branch" in success_call.args[0]
