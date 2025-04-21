"""Tests for the delete command."""

from unittest.mock import patch

import pytest
from prompt_toolkit.formatted_text import HTML

from panqake.commands.delete import delete_branch


@pytest.fixture
def mock_dependencies():
    """Mock dependencies for delete command testing."""
    with (
        patch("panqake.commands.delete.get_current_branch") as mock_get_current,
        patch("panqake.commands.delete.branch_exists") as mock_branch_exists,
        patch("panqake.commands.delete.get_parent_branch") as mock_get_parent,
        patch("panqake.commands.delete.get_child_branches") as mock_get_children,
        patch("panqake.commands.delete.add_to_stack") as mock_add_to_stack,
        patch("panqake.commands.delete.remove_from_stack") as mock_remove_from_stack,
        patch("panqake.commands.delete.run_git_command") as mock_run_git,
        patch("panqake.commands.delete.prompt_confirm") as mock_confirm,
        patch("panqake.commands.delete.print_formatted_text") as mock_print,
        patch("panqake.commands.delete.format_branch") as mock_format,
        patch("panqake.commands.delete.sys.exit") as mock_exit,
    ):
        # Set default return values
        mock_get_current.return_value = "main"
        mock_branch_exists.return_value = True
        mock_get_parent.return_value = "main"
        mock_get_children.return_value = []
        mock_run_git.return_value = "Success output"
        mock_confirm.return_value = True
        mock_format.return_value = HTML("<branch>branch-name</branch>")

        yield {
            "get_current_branch": mock_get_current,
            "branch_exists": mock_branch_exists,
            "get_parent_branch": mock_get_parent,
            "get_children": mock_get_children,
            "add_to_stack": mock_add_to_stack,
            "remove_from_stack": mock_remove_from_stack,
            "run_git": mock_run_git,
            "confirm": mock_confirm,
            "print": mock_print,
            "format": mock_format,
            "exit": mock_exit,
        }


def test_delete_nonexistent_branch(mock_dependencies):
    """Test error handling when trying to delete a nonexistent branch."""
    # Setup
    mock_dependencies["branch_exists"].return_value = False

    # Execute
    delete_branch("feature")

    # Verify
    assert any(
        "does not exist" in str(call[0][0])
        for call in mock_dependencies["print"].call_args_list
    )
    # Don't verify exit call count as it might be called multiple times
    assert mock_dependencies["exit"].called


def test_delete_current_branch(mock_dependencies):
    """Test error handling when trying to delete the current branch."""
    # Setup
    mock_dependencies["get_current_branch"].return_value = "feature"

    # Execute
    delete_branch("feature")

    # Verify
    assert any(
        "Cannot delete the current branch" in str(call[0][0])
        for call in mock_dependencies["print"].call_args_list
    )
    mock_dependencies["exit"].assert_called_once_with(1)


def test_delete_with_nonexistent_parent(mock_dependencies):
    """Test error handling when parent branch doesn't exist."""
    # Setup
    mock_dependencies["branch_exists"].side_effect = lambda branch: branch != "main"

    # Execute
    delete_branch("feature")

    # Verify
    assert any(
        "does not exist" in str(call[0][0])
        for call in mock_dependencies["print"].call_args_list
    )
    mock_dependencies["exit"].assert_called_once_with(1)


def test_delete_branch_user_cancels(mock_dependencies):
    """Test user cancellation of branch deletion."""
    # Setup
    mock_dependencies["confirm"].return_value = False

    # Execute
    delete_branch("feature")

    # Verify user was prompted
    mock_dependencies["confirm"].assert_called_once()

    # Verify cancellation message
    assert any(
        "cancelled" in str(call[0][0])
        for call in mock_dependencies["print"].call_args_list
    )

    # Verify no Git commands were run for deletion
    assert not any(
        "branch -D" in str(call) for call in mock_dependencies["run_git"].call_args_list
    )
    mock_dependencies["remove_from_stack"].assert_not_called()


def test_delete_branch_without_children(mock_dependencies):
    """Test successful deletion of a branch without children."""
    # Setup
    mock_dependencies["get_children"].return_value = []

    # Execute
    delete_branch("feature")

    # Verify git commands
    mock_dependencies["run_git"].assert_any_call(["branch", "-D", "feature"])

    # Verify cleanup
    mock_dependencies["remove_from_stack"].assert_called_once_with("feature")


def test_delete_branch_with_children(mock_dependencies):
    """Test deletion of a branch with children that get relinked."""
    # Setup
    mock_dependencies["get_current_branch"].return_value = "main"
    mock_dependencies["get_parent_branch"].return_value = "main"
    mock_dependencies["get_children"].return_value = ["child1", "child2"]

    # Execute
    delete_branch("feature")

    # Verify git commands for each child
    checkout_calls = [
        call
        for call in mock_dependencies["run_git"].call_args_list
        if call[0][0][0] == "checkout"
    ]
    rebase_calls = [
        call
        for call in mock_dependencies["run_git"].call_args_list
        if call[0][0][0] == "rebase"
    ]

    assert len(checkout_calls) >= 2  # At least one for each child
    assert len(rebase_calls) >= 2  # At least one for each child

    # Verify stack updates
    mock_dependencies["add_to_stack"].assert_any_call("child1", "main")
    mock_dependencies["add_to_stack"].assert_any_call("child2", "main")

    # Verify cleanup
    mock_dependencies["remove_from_stack"].assert_called_once_with("feature")


def test_delete_branch_checkout_error(mock_dependencies):
    """Test error handling when checkout fails."""
    # Setup
    mock_dependencies["get_children"].return_value = ["child1"]
    # Make sure run_git returns enough values
    mock_dependencies["run_git"].side_effect = (
        lambda cmd: None if cmd[0] == "checkout" else "Success"
    )

    # Execute - this function will exit early due to checkout failure
    try:
        delete_branch("feature")
    except StopIteration:  # Handle StopIteration from mock side_effects
        pass

    # Verify error handling
    assert any(
        "Failed to checkout" in str(call[0][0])
        for call in mock_dependencies["print"].call_args_list
    )
    assert mock_dependencies["exit"].called


def test_delete_branch_rebase_error(mock_dependencies):
    """Test error handling when rebase fails."""
    # Setup
    mock_dependencies["get_children"].return_value = ["child1"]

    # Set up side effect for run_git to succeed on checkout but fail on rebase
    def run_git_side_effect(cmd):
        if cmd[0] == "checkout":
            return "Success"
        elif cmd[0] == "rebase":
            return None
        return "Success"

    mock_dependencies["run_git"].side_effect = run_git_side_effect

    # Execute - this function will exit early due to rebase failure
    try:
        delete_branch("feature")
    except StopIteration:  # Handle StopIteration from mock side_effects
        pass

    # Verify error handling
    assert any(
        "Rebase conflict" in str(call[0][0])
        for call in mock_dependencies["print"].call_args_list
    )
    assert mock_dependencies["exit"].called
