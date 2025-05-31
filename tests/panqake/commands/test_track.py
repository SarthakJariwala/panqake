"""Tests for track.py command module."""

from unittest.mock import patch

import pytest

from panqake.commands.track import track


@pytest.fixture
def mock_git_utils():
    """Mock git utility functions."""
    with (
        patch("panqake.commands.track.get_current_branch") as mock_current,
        patch("panqake.commands.track.get_potential_parents") as mock_parents,
    ):
        mock_current.return_value = "feature-branch"
        mock_parents.return_value = ["main", "develop"]
        yield {
            "current": mock_current,
            "parents": mock_parents,
        }


@pytest.fixture
def mock_config_utils():
    """Mock config utility functions."""
    with patch("panqake.commands.track.add_to_stack") as mock_add:
        yield mock_add


@pytest.fixture
def mock_prompt():
    """Mock questionary prompt functions."""
    with (
        patch("panqake.commands.track.select_parent_branch") as mock_parent_prompt,
        patch("panqake.commands.track.print_formatted_text") as mock_print,
    ):
        mock_parent_prompt.return_value = "main"
        yield {
            "parent": mock_parent_prompt,
            "print": mock_print,
        }


def test_track_current_branch(mock_git_utils, mock_config_utils, mock_prompt):
    """Test tracking current branch when no branch name is provided."""
    # Execute
    track()

    # Verify
    mock_git_utils["current"].assert_called_once()
    mock_git_utils["parents"].assert_called_once_with("feature-branch")
    mock_prompt["parent"].assert_called_once_with(["main", "develop"])
    mock_config_utils.assert_called_once_with("feature-branch", "main")


def test_track_specified_branch(mock_git_utils, mock_config_utils, mock_prompt):
    """Test tracking a specified branch name."""
    # Execute
    track("test-branch")

    # Verify
    mock_git_utils["current"].assert_not_called()
    mock_git_utils["parents"].assert_called_once_with("test-branch")
    mock_prompt["parent"].assert_called_once_with(["main", "develop"])
    mock_config_utils.assert_called_once_with("test-branch", "main")


def test_track_no_current_branch(mock_git_utils, mock_config_utils, mock_prompt):
    """Test error when current branch cannot be determined."""
    # Setup
    mock_git_utils["current"].return_value = None

    # Execute and verify
    with pytest.raises(SystemExit):
        track()

    # Verify no further operations were performed
    mock_git_utils["parents"].assert_not_called()
    mock_prompt["parent"].assert_not_called()
    mock_config_utils.assert_not_called()


def test_track_no_potential_parents(mock_git_utils, mock_config_utils, mock_prompt):
    """Test error when no potential parent branches are found."""
    # Setup
    mock_git_utils["parents"].return_value = []

    # Execute and verify
    with pytest.raises(SystemExit):
        track("test-branch")

    # Verify no further operations were performed
    mock_prompt["parent"].assert_not_called()
    mock_config_utils.assert_not_called()


def test_track_user_cancels_parent_selection(
    mock_git_utils, mock_config_utils, mock_prompt
):
    """Test when user cancels parent branch selection."""
    # Setup
    mock_prompt["parent"].return_value = None

    # Execute and verify
    with pytest.raises(SystemExit):
        track("test-branch")

    # Verify no stack update was performed
    mock_config_utils.assert_not_called()


def test_track_success_messages(mock_git_utils, mock_config_utils, mock_prompt):
    """Test success messages are printed correctly."""
    # Execute
    track("test-branch")

    # Verify appropriate messages were printed
    mock_prompt["print"].assert_called()
    success_call = mock_prompt["print"].call_args_list[-1]
    assert "Successfully" in success_call.args[0]
    assert "test-branch" in success_call.args[0]
    assert "main" in success_call.args[0]
