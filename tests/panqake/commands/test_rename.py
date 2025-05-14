"""Tests for rename.py command module."""

from unittest.mock import patch

import pytest

from panqake.commands.rename import rename


@pytest.fixture
def mock_git_utils():
    """Mock git utility functions."""
    with (
        patch("panqake.commands.rename.get_current_branch") as mock_current,
        patch("panqake.commands.rename.rename_branch") as mock_rename,
    ):
        mock_current.return_value = "feature-branch"
        mock_rename.return_value = True
        yield {
            "current": mock_current,
            "rename": mock_rename,
        }


@pytest.fixture
def mock_stack_utils():
    """Mock stack utility functions."""
    with patch("panqake.commands.rename.Stacks") as mock_stacks_class:
        mock_stacks = mock_stacks_class.return_value
        mock_stacks.branch_exists.return_value = True
        mock_stacks.rename_branch.return_value = True
        yield mock_stacks


@pytest.fixture
def mock_prompt():
    """Mock questionary prompt functions."""
    with (
        patch("panqake.commands.rename.prompt_input") as mock_input,
        patch("panqake.commands.rename.print_formatted_text") as mock_print,
    ):
        mock_input.return_value = "new-feature-branch"
        yield {
            "input": mock_input,
            "print": mock_print,
        }


def test_rename_current_branch(mock_git_utils, mock_stack_utils, mock_prompt):
    """Test renaming the current branch when no branch name is provided."""
    # Execute
    rename(new_name="new-feature-branch")

    # Verify
    mock_git_utils["current"].assert_called_once()
    mock_stack_utils.branch_exists.assert_called_once_with("feature-branch")
    mock_git_utils["rename"].assert_called_once_with(
        "feature-branch", "new-feature-branch"
    )
    mock_stack_utils.rename_branch.assert_called_once_with(
        "feature-branch", "new-feature-branch"
    )


def test_rename_specified_branch(mock_git_utils, mock_stack_utils, mock_prompt):
    """Test renaming a specified branch."""
    # Execute
    rename("test-branch", "new-test-branch")

    # Verify
    mock_git_utils["current"].assert_not_called()
    mock_stack_utils.branch_exists.assert_called_once_with("test-branch")
    mock_git_utils["rename"].assert_called_once_with("test-branch", "new-test-branch")
    mock_stack_utils.rename_branch.assert_called_once_with(
        "test-branch", "new-test-branch"
    )


def test_rename_prompt_for_new_name(mock_git_utils, mock_stack_utils, mock_prompt):
    """Test prompting for a new branch name when not provided."""
    # Execute
    rename("test-branch")

    # Verify
    mock_prompt["input"].assert_called_once()
    assert "Enter new name" in mock_prompt["input"].call_args.args[0]
    mock_git_utils["rename"].assert_called_once_with(
        "test-branch", "new-feature-branch"
    )


def test_rename_no_current_branch(mock_git_utils, mock_stack_utils, mock_prompt):
    """Test error when current branch cannot be determined."""
    # Setup
    mock_git_utils["current"].return_value = None

    # Execute and verify
    with pytest.raises(SystemExit):
        rename()

    # Verify no further operations were performed
    mock_git_utils["rename"].assert_not_called()
    mock_stack_utils.rename_branch.assert_not_called()


def test_rename_untracked_branch(mock_git_utils, mock_stack_utils, mock_prompt):
    """Test renaming a branch that is not tracked in the stack."""
    # Setup
    mock_stack_utils.branch_exists.return_value = False
    mock_git_utils["rename"].return_value = True

    # Mock sys.exit to prevent the test from exiting
    with patch("panqake.commands.rename.sys.exit"):
        # Execute
        rename("test-branch", "new-test-branch")

    # Verify appropriate warning was printed about untracked branch
    info_printed = False
    for call_args in mock_prompt["print"].call_args_list:
        if "not tracked" in str(call_args):
            info_printed = True
            break

    assert info_printed, "Warning about untracked branch was not printed"


def test_rename_git_failure(mock_git_utils, mock_stack_utils, mock_prompt):
    """Test failure in Git rename operation."""
    # Setup
    mock_git_utils["rename"].return_value = False

    # Execute and verify
    with pytest.raises(SystemExit):
        rename("test-branch", "new-test-branch")

    # Verify stack was not updated
    mock_stack_utils.rename_branch.assert_not_called()


def test_rename_stack_failure(mock_git_utils, mock_stack_utils, mock_prompt):
    """Test failure in stack update operation."""
    # Setup
    mock_stack_utils.rename_branch.return_value = False

    # Execute
    rename("test-branch", "new-test-branch")

    # Verify appropriate warning was printed
    warning_calls = [
        call
        for call in mock_prompt["print"].call_args_list
        if "Warning: Failed to update" in call.args[0]
    ]
    assert warning_calls
