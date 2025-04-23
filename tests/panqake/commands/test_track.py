"""Tests for the track command."""

from unittest.mock import patch

import pytest

from panqake.commands.track import track


@pytest.fixture
def mock_track_functions():
    """Mock functions used by the track command."""
    with (
        patch("panqake.commands.track.get_current_branch") as mock_current_branch,
        patch("panqake.commands.track.get_potential_parents") as mock_get_parents,
        patch("panqake.commands.track.prompt_for_parent") as mock_prompt_parent,
        patch("panqake.commands.track.add_to_stack") as mock_add_to_stack,
        patch("panqake.commands.track.print_formatted_text") as mock_print,
    ):
        # Set up default return values
        mock_current_branch.return_value = "feature-branch"
        mock_get_parents.return_value = ["main", "develop"]
        mock_prompt_parent.return_value = "main"

        yield {
            "current_branch": mock_current_branch,
            "get_parents": mock_get_parents,
            "prompt_parent": mock_prompt_parent,
            "add_to_stack": mock_add_to_stack,
            "print": mock_print,
        }


def test_track_current_branch_success(mock_track_functions):
    """Test tracking the current branch successfully."""
    # Call the function
    track()

    # Verify the function behavior
    mock_track_functions["current_branch"].assert_called_once()
    mock_track_functions["get_parents"].assert_called_once_with("feature-branch")
    mock_track_functions["prompt_parent"].assert_called_once_with(["main", "develop"])
    mock_track_functions["add_to_stack"].assert_called_once_with(
        "feature-branch", "main"
    )
    # Check that success message was printed (we don't need to check exact message)
    assert mock_track_functions["print"].called


def test_track_specific_branch_success(mock_track_functions):
    """Test tracking a specific branch successfully."""
    # Call the function with a specific branch name
    track("feature-specific")

    # Verify the function behavior
    mock_track_functions[
        "current_branch"
    ].assert_not_called()  # Should not be called when branch name is provided
    mock_track_functions["get_parents"].assert_called_once_with("feature-specific")
    mock_track_functions["prompt_parent"].assert_called_once_with(["main", "develop"])
    mock_track_functions["add_to_stack"].assert_called_once_with(
        "feature-specific", "main"
    )
    # Check that success message was printed
    assert mock_track_functions["print"].called


def test_track_no_potential_parents(mock_track_functions):
    """Test tracking a branch with no potential parents."""
    # Setup mocks
    mock_track_functions["get_parents"].return_value = []

    # Call the function, should exit with error
    with pytest.raises(SystemExit):
        track()

    # Verify the function behavior
    mock_track_functions["current_branch"].assert_called_once()
    mock_track_functions["get_parents"].assert_called_once_with("feature-branch")
    mock_track_functions["prompt_parent"].assert_not_called()
    mock_track_functions["add_to_stack"].assert_not_called()
    # Check that warning message was printed
    assert mock_track_functions["print"].called


def test_track_no_parent_selected(mock_track_functions):
    """Test tracking a branch when no parent is selected."""
    # Setup mocks
    mock_track_functions["prompt_parent"].return_value = None

    # Call the function, should exit with error
    with pytest.raises(SystemExit):
        track()

    # Verify the function behavior
    mock_track_functions["current_branch"].assert_called_once()
    mock_track_functions["get_parents"].assert_called_once_with("feature-branch")
    mock_track_functions["prompt_parent"].assert_called_once_with(["main", "develop"])
    mock_track_functions["add_to_stack"].assert_not_called()
    # Check that warning message was printed
    assert mock_track_functions["print"].called


def test_track_current_branch_not_found(mock_track_functions):
    """Test tracking when current branch cannot be determined."""
    # Setup mocks
    mock_track_functions["current_branch"].return_value = None

    # Call the function, should exit with error
    with pytest.raises(SystemExit):
        track()

    # Verify the function behavior
    mock_track_functions["current_branch"].assert_called_once()
    mock_track_functions["get_parents"].assert_not_called()
    mock_track_functions["prompt_parent"].assert_not_called()
    mock_track_functions["add_to_stack"].assert_not_called()
    # Check that warning message was printed
    assert mock_track_functions["print"].called
