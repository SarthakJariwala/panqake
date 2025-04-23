"""Tests for the update command."""

from unittest.mock import call, patch

import pytest
from prompt_toolkit.formatted_text import HTML

from panqake.commands.update import update_branch_and_children, update_branches


@pytest.fixture
def mock_dependencies():
    """Mock dependencies for update command testing."""
    with (
        patch("panqake.commands.update.get_current_branch") as mock_get_current,
        patch("panqake.commands.update.branch_exists") as mock_branch_exists,
        patch("panqake.commands.update.get_child_branches") as mock_get_children,
        patch("panqake.commands.update.run_git_command") as mock_run_git,
        patch("panqake.commands.update.prompt_confirm") as mock_confirm,
        patch("panqake.commands.update.print_formatted_text") as mock_print,
        patch("panqake.commands.update.format_branch") as mock_format,
        patch("panqake.commands.update.sys.exit") as mock_exit,
        patch("panqake.commands.update.push_branch_to_remote") as mock_push,
        patch("panqake.commands.update.check_github_cli_installed") as mock_github_cli,
        patch("panqake.commands.update.branch_has_pr") as mock_has_pr,
    ):
        # Set default return values
        mock_get_current.return_value = "main"
        mock_branch_exists.return_value = True
        mock_get_children.side_effect = lambda branch: {
            "main": ["develop"],
            "develop": ["feature", "bugfix"],
            "feature": ["enhancement"],
            "bugfix": [],
            "enhancement": [],
        }.get(branch, [])
        mock_run_git.return_value = "Success output"
        mock_confirm.return_value = True
        mock_format.return_value = HTML("<branch>branch-name</branch>")
        mock_push.return_value = True
        mock_github_cli.return_value = True
        mock_has_pr.return_value = False

        yield {
            "get_current_branch": mock_get_current,
            "branch_exists": mock_branch_exists,
            "get_child_branches": mock_get_children,
            "run_git": mock_run_git,
            "confirm": mock_confirm,
            "print": mock_print,
            "format": mock_format,
            "exit": mock_exit,
            "push": mock_push,
            "github_cli": mock_github_cli,
            "has_pr": mock_has_pr,
        }


def test_update_nonexistent_branch(mock_dependencies):
    """Test error handling when trying to update a nonexistent branch."""
    # Setup
    mock_dependencies["branch_exists"].return_value = False

    # Execute
    update_branches("feature")

    # Verify
    assert any(
        "does not exist" in str(call[0][0])
        for call in mock_dependencies["print"].call_args_list
    )
    mock_dependencies["exit"].assert_called_once_with(1)


@patch("panqake.commands.update.get_child_branches")
def test_update_no_children(mock_get_children, mock_dependencies):
    """Test handling when branch has no children to update."""
    # Setup - use direct patching to ensure our mock is used
    mock_get_children.return_value = []
    mock_dependencies["get_child_branches"].return_value = []

    # Create a proper exit to capture the early return
    with patch("panqake.commands.update.sys.exit"):
        # Execute - this should exit early through our patched exit function
        update_branches("feature")

    # Verify the format_branch was called with feature (for the info message)
    mock_dependencies["format"].assert_any_call("feature")


def test_update_user_cancels(mock_dependencies):
    """Test user cancellation of branch update."""
    # Setup
    mock_dependencies["confirm"].return_value = False

    # Execute
    update_branches("develop")

    # Verify user was prompted
    mock_dependencies["confirm"].assert_called_once()

    # Verify cancellation message
    assert any(
        "cancelled" in str(call[0][0]).lower()
        for call in mock_dependencies["print"].call_args_list
    )

    # Verify no Git commands were run
    mock_dependencies["run_git"].assert_not_called()


def test_collect_all_children(mock_dependencies):
    """Test collection of all child branches."""
    # Execute
    update_branches("develop")

    # Format branch is called for each branch
    assert mock_dependencies["format"].call_count >= 3


def test_update_branches_success_local_only(mock_dependencies):
    """Test successful update of branches."""
    # Setup
    # Simplify side effect for more predictable testing
    mock_dependencies["get_child_branches"].side_effect = lambda branch: {
        "develop": ["feature", "bugfix"],
        "feature": [],
        "bugfix": [],
    }.get(branch, [])

    # Execute
    update_branches("develop", skip_push=True)

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

    assert len(checkout_calls) >= 2  # One for each child
    assert len(rebase_calls) >= 2  # One for each child

    # Verify return to original branch
    assert mock_dependencies["run_git"].call_args_list[-1] == call(["checkout", "main"])


def test_update_branches_uses_current_branch(mock_dependencies):
    """Test that current branch is used when none specified."""
    # Setup
    mock_dependencies["get_current_branch"].return_value = "develop"

    # Execute
    update_branches()

    # Verify correct branch was used
    mock_dependencies["branch_exists"].assert_called_once_with("develop")


def test_update_branches_checkout_error(mock_dependencies):
    """Test error handling when checkout fails."""
    # Setup - simplified branch structure
    mock_dependencies["get_child_branches"].side_effect = lambda branch: {
        "develop": ["feature"],
        "feature": [],
    }.get(branch, [])

    # Make checkout fail
    mock_dependencies["run_git"].side_effect = (
        lambda cmd: None if cmd[0] == "checkout" else "Success"
    )

    # Execute
    update_branches("develop")

    # Verify error handling
    assert any(
        "Failed to checkout" in str(call[0][0])
        for call in mock_dependencies["print"].call_args_list
    )
    mock_dependencies["exit"].assert_called_once_with(1)


def test_update_branches_with_push(mock_dependencies):
    """Test update with pushing to remote."""
    # Setup
    # Simplify side effect for more predictable testing
    mock_dependencies["get_child_branches"].side_effect = lambda branch: {
        "develop": ["feature", "bugfix"],
        "feature": [],
        "bugfix": [],
    }.get(branch, [])

    # Execute
    update_branches("develop", skip_push=False)

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

    # Should have checkout calls for each branch plus return to original
    assert (
        len(checkout_calls) >= 4
    )  # feature, bugfix, and back to each for pushing, then back to main

    # Should have rebase calls for each child
    assert len(rebase_calls) >= 2  # One for each child

    # Verify push was called for each updated branch
    assert mock_dependencies["push"].call_count == 2
    mock_dependencies["push"].assert_any_call("feature", force=True)
    mock_dependencies["push"].assert_any_call("bugfix", force=True)

    # Verify return to original branch
    assert mock_dependencies["run_git"].call_args_list[-1] == call(["checkout", "main"])


def test_update_branches_without_github_cli(mock_dependencies):
    """Test update with pushing to remote when GitHub CLI is not installed."""
    # Setup
    mock_dependencies["github_cli"].return_value = False
    mock_dependencies["get_child_branches"].side_effect = lambda branch: {
        "develop": ["feature"],
        "feature": [],
    }.get(branch, [])

    # Execute
    update_branches("develop", skip_push=False)

    # Verify push was still called
    assert mock_dependencies["push"].call_count == 1
    mock_dependencies["push"].assert_called_once_with("feature", force=True)

    # Verify GitHub CLI check was called
    assert mock_dependencies["github_cli"].call_count == 1

    # Verify has_pr was not called (since GitHub CLI is not installed)
    assert mock_dependencies["has_pr"].call_count == 0


def test_update_branch_and_children_returns_updated_branches(mock_dependencies):
    """Test that update_branch_and_children returns a list of updated branches."""
    # Setup
    mock_dependencies["get_child_branches"].side_effect = lambda branch: {
        "develop": ["feature", "bugfix"],
        "feature": [],
        "bugfix": [],
    }.get(branch, [])

    # Execute
    result = update_branch_and_children("develop", "main")

    # Verify
    assert sorted(result) == sorted(["feature", "bugfix"])


def test_update_branches_rebase_error(mock_dependencies):
    """Test error handling when rebase fails."""
    # Setup - simplified branch structure
    mock_dependencies["get_child_branches"].side_effect = lambda branch: {
        "develop": ["feature"],
        "feature": [],
    }.get(branch, [])

    # Make rebase fail after checkout
    mock_dependencies["run_git"].side_effect = lambda cmd: (
        "Success" if cmd[0] == "checkout" else None
    )

    # Execute
    update_branches("develop")

    # Verify error handling
    assert any(
        "Rebase conflict" in str(call[0][0])
        for call in mock_dependencies["print"].call_args_list
    )
    mock_dependencies["exit"].assert_called_once_with(1)
