"""Tests for delete.py command module."""

from unittest.mock import patch

import pytest

from panqake.commands.delete import delete_branch

# Constants for testing
MOCK_BRANCHES = ["main", "feature-branch", "another-feature", "develop"]


@pytest.fixture
def mock_git_utils():
    """Mock all git utility functions."""
    with (
        patch("panqake.commands.delete.branch_exists") as mock_exists,
        patch("panqake.commands.delete.validate_branch") as mock_validate,
        patch("panqake.commands.delete.checkout_branch") as mock_checkout,
        patch("panqake.commands.delete.get_current_branch") as mock_current,
        patch("panqake.commands.delete.run_git_command") as mock_run,
    ):
        mock_current.return_value = "main"
        mock_validate.side_effect = lambda x: x  # Just return the input
        yield {
            "exists": mock_exists,
            "validate": mock_validate,
            "checkout": mock_checkout,
            "current": mock_current,
            "run": mock_run,
        }


@pytest.fixture
def mock_config_utils():
    """Mock config utility functions."""
    with (
        patch("panqake.commands.delete.add_to_stack") as mock_add,
        patch("panqake.commands.delete.get_child_branches") as mock_get_children,
        patch("panqake.commands.delete.get_parent_branch") as mock_get_parent,
        patch("panqake.commands.delete.remove_from_stack") as mock_remove,
    ):
        yield {
            "add": mock_add,
            "get_children": mock_get_children,
            "get_parent": mock_get_parent,
            "remove": mock_remove,
        }


@pytest.fixture
def mock_prompt():
    """Mock questionary prompt functions."""
    with (
        patch("panqake.commands.delete.format_branch") as mock_format,
        patch("panqake.commands.delete.print_formatted_text") as mock_print,
        patch("panqake.commands.delete.prompt_confirm") as mock_confirm,
        patch(
            "panqake.commands.delete.select_branch_excluding_current"
        ) as mock_select_branch,
    ):
        mock_format.return_value = "formatted_branch"
        mock_select_branch.return_value = "feature-branch"
        yield {
            "format": mock_format,
            "print": mock_print,
            "confirm": mock_confirm,
            "select_branch": mock_select_branch,
        }


def test_delete_branch_success(mock_git_utils, mock_config_utils, mock_prompt):
    """Test successful branch deletion with no child branches."""
    # Setup
    mock_git_utils["exists"].return_value = True
    mock_config_utils["get_parent"].return_value = "main"
    mock_config_utils["get_children"].return_value = []
    mock_prompt["confirm"].return_value = True
    mock_git_utils["run"].return_value = "success"
    mock_config_utils["remove"].return_value = True  # Successful stack removal

    # Execute
    delete_branch("feature-branch")

    # Verify
    mock_git_utils["run"].assert_called_with(["branch", "-D", "feature-branch"])
    mock_config_utils["remove"].assert_called_once_with("feature-branch")
    assert (
        mock_prompt["print"]
        .call_args_list[-1]
        .args[0]
        .endswith("relinked the stack[/success]")
    )


def test_delete_branch_with_children(mock_git_utils, mock_config_utils, mock_prompt):
    """Test successful branch deletion with child branches that need relinking."""
    # Setup
    mock_git_utils["exists"].return_value = True
    mock_config_utils["get_parent"].return_value = "main"
    mock_config_utils["get_children"].return_value = ["child1", "child2"]
    mock_prompt["confirm"].return_value = True
    mock_git_utils["run"].return_value = "success"

    # Execute
    delete_branch("feature-branch")

    # Verify
    assert (
        mock_git_utils["checkout"].call_count == 3
    )  # Once for each child and back to main
    assert mock_config_utils["add"].call_count == 2  # Once for each child
    mock_git_utils["run"].assert_called_with(["branch", "-D", "feature-branch"])
    mock_config_utils["remove"].assert_called_once_with("feature-branch")


def test_delete_nonexistent_branch(mock_git_utils, mock_config_utils, mock_prompt):
    """Test error when trying to delete a non-existent branch."""
    # Setup
    mock_git_utils["exists"].return_value = False

    # Execute and verify
    with pytest.raises(SystemExit):
        delete_branch("nonexistent-branch")

    # Verify branch was not deleted
    mock_git_utils["run"].assert_not_called()
    mock_config_utils["remove"].assert_not_called()


def test_delete_current_branch(mock_git_utils, mock_config_utils, mock_prompt):
    """Test error when trying to delete the current branch."""
    # Setup
    mock_git_utils["exists"].return_value = True
    mock_git_utils["current"].return_value = "feature-branch"

    # Execute and verify
    with pytest.raises(SystemExit):
        delete_branch("feature-branch")

    # Verify branch was not deleted
    mock_git_utils["run"].assert_not_called()
    mock_config_utils["remove"].assert_not_called()


def test_delete_branch_nonexistent_parent(
    mock_git_utils, mock_config_utils, mock_prompt
):
    """Test error when parent branch doesn't exist."""
    # Setup: the validation call will succeed, but the parent check will fail
    mock_config_utils["get_parent"].return_value = "nonexistent-parent"
    mock_git_utils["exists"].side_effect = lambda branch: branch != "nonexistent-parent"

    # Execute and verify
    with pytest.raises(SystemExit):
        delete_branch("feature-branch")

    # Verify branch was not deleted
    mock_git_utils["run"].assert_not_called()
    mock_config_utils["remove"].assert_not_called()


def test_delete_branch_user_cancellation(
    mock_git_utils, mock_config_utils, mock_prompt
):
    """Test cancellation of branch deletion by user."""
    # Setup
    mock_git_utils["exists"].return_value = True
    mock_config_utils["get_parent"].return_value = "main"
    mock_config_utils["get_children"].return_value = []
    mock_prompt["confirm"].return_value = False

    # Execute
    delete_branch("feature-branch")

    # Verify branch was not deleted
    mock_git_utils["run"].assert_not_called()
    mock_config_utils["remove"].assert_not_called()


def test_delete_branch_no_branch_name_provided(
    mock_git_utils, mock_config_utils, mock_prompt
):
    """Test branch deletion when no branch name is provided."""
    # Setup
    mock_git_utils["exists"].return_value = True
    mock_config_utils["get_parent"].return_value = "main"
    mock_config_utils["get_children"].return_value = []
    mock_prompt["confirm"].return_value = True
    mock_git_utils["run"].return_value = "success"
    mock_config_utils["remove"].return_value = True

    # Execute
    delete_branch()  # No branch name provided

    # Verify select_branch_excluding_current was called
    mock_prompt["select_branch"].assert_called_once()

    # Verify deletion was performed with the selected branch name
    mock_git_utils["run"].assert_called_with(["branch", "-D", "feature-branch"])
    mock_config_utils["remove"].assert_called_once_with("feature-branch")


def test_delete_branch_no_available_branches(
    mock_git_utils, mock_config_utils, mock_prompt
):
    """Test when no branches are available for deletion."""
    # Setup
    mock_prompt["select_branch"].return_value = None  # No branch selected

    # Execute
    delete_branch()  # No branch name provided

    # Verify warning message was shown
    assert any(
        "No branches available for deletion" in str(args)
        for args in mock_prompt["print"].call_args_list
    )

    # Verify no deletion was attempted
    mock_git_utils["run"].assert_not_called()
    mock_config_utils["remove"].assert_not_called()


def test_delete_branch_rebase_error(mock_git_utils, mock_config_utils, mock_prompt):
    """Test error during rebase of child branches."""
    # Setup
    mock_git_utils["exists"].return_value = True
    mock_config_utils["get_parent"].return_value = "main"
    mock_config_utils["get_children"].return_value = ["child1"]
    mock_prompt["confirm"].return_value = True
    mock_git_utils["run"].side_effect = [
        "success",
        None,
    ]  # Success for first command, fail for rebase

    # Execute and verify
    with pytest.raises(SystemExit):
        delete_branch("feature-branch")

    # Verify branch was not deleted
    assert "branch -D" not in str(mock_git_utils["run"].call_args_list)
    mock_config_utils["remove"].assert_not_called()


def test_delete_branch_deletion_error(mock_git_utils, mock_config_utils, mock_prompt):
    """Test error during branch deletion."""
    # Setup
    mock_git_utils["exists"].return_value = True
    mock_config_utils["get_parent"].return_value = "main"
    mock_config_utils["get_children"].return_value = []
    mock_prompt["confirm"].return_value = True
    mock_git_utils["run"].return_value = None  # Deletion command fails

    # Execute and verify
    with pytest.raises(SystemExit):
        delete_branch("feature-branch")

    # Verify stack was not modified
    mock_config_utils["remove"].assert_not_called()
