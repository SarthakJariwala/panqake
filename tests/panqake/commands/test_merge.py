"""Tests for merge.py command module."""

from unittest.mock import patch

import pytest

from panqake.commands.merge import (
    cleanup_local_branch,
    get_merge_method,
    merge_branch,
    merge_pr,
    update_pr_base_for_children,
)


@pytest.fixture
def mock_git_utils():
    """Mock all git utility functions."""
    with (
        patch("panqake.commands.merge.branch_exists") as mock_exists,
        patch("panqake.commands.merge.checkout_branch") as mock_checkout,
        patch("panqake.commands.merge.get_current_branch") as mock_current,
        patch("panqake.commands.merge.run_git_command") as mock_run,
        patch("panqake.commands.merge.delete_remote_branch") as mock_delete_remote,
        patch("panqake.commands.merge.validate_branch") as mock_validate,
    ):
        mock_current.return_value = "main"
        mock_validate.side_effect = lambda x: x  # Return input unchanged
        yield {
            "exists": mock_exists,
            "checkout": mock_checkout,
            "current": mock_current,
            "run": mock_run,
            "delete_remote": mock_delete_remote,
            "validate": mock_validate,
        }


@pytest.fixture
def mock_config_utils():
    """Mock config utility functions."""
    with (
        patch("panqake.commands.merge.add_to_stack") as mock_add,
        patch("panqake.commands.merge.get_child_branches") as mock_get_children,
        patch("panqake.commands.merge.get_parent_branch") as mock_get_parent,
        patch("panqake.commands.merge.remove_from_stack") as mock_remove,
    ):
        yield {
            "add": mock_add,
            "get_children": mock_get_children,
            "get_parent": mock_get_parent,
            "remove": mock_remove,
        }


@pytest.fixture
def mock_github_utils():
    """Mock GitHub utility functions."""
    with (
        patch("panqake.commands.merge.branch_has_pr") as mock_has_pr,
        patch("panqake.commands.merge.check_github_cli_installed") as mock_check_cli,
        patch("panqake.commands.merge.update_pr_base") as mock_update_base,
        patch("panqake.commands.merge.github_merge_pr") as mock_merge_pr,
    ):
        mock_check_cli.return_value = True
        yield {
            "has_pr": mock_has_pr,
            "check_cli": mock_check_cli,
            "update_base": mock_update_base,
            "merge_pr": mock_merge_pr,
        }


@pytest.fixture
def mock_branch_ops():
    """Mock branch operation utilities."""
    with (
        patch("panqake.commands.merge.fetch_latest_from_remote") as mock_fetch,
        patch(
            "panqake.commands.merge.update_branch_with_conflict_detection"
        ) as mock_update,
        patch("panqake.commands.merge.return_to_branch") as mock_return,
    ):
        yield {
            "fetch": mock_fetch,
            "update": mock_update,
            "return": mock_return,
        }


@pytest.fixture
def mock_prompt():
    """Mock questionary prompt functions."""
    with (
        patch("panqake.commands.merge.format_branch") as mock_format,
        patch("panqake.commands.merge.print_formatted_text") as mock_print,
        patch("panqake.commands.merge.prompt_confirm") as mock_confirm,
        patch("panqake.commands.merge.prompt_select") as mock_select,
    ):
        mock_format.return_value = "formatted_branch"
        yield {
            "format": mock_format,
            "print": mock_print,
            "confirm": mock_confirm,
            "select": mock_select,
        }


def test_merge_pr_success(mock_github_utils, mock_prompt):
    """Test successful PR merge."""
    # Setup
    mock_github_utils["has_pr"].return_value = True
    mock_github_utils["merge_pr"].return_value = True

    # Execute
    result = merge_pr("feature-branch", "squash")

    # Verify
    assert result is True
    mock_github_utils["merge_pr"].assert_called_once_with("feature-branch", "squash")


def test_merge_pr_no_pr(mock_github_utils, mock_prompt):
    """Test merge attempt for branch without PR."""
    # Setup
    mock_github_utils["has_pr"].return_value = False

    # Execute
    result = merge_pr("feature-branch")

    # Verify
    assert result is False
    mock_github_utils["merge_pr"].assert_not_called()


def test_merge_pr_merge_failed(mock_github_utils, mock_prompt):
    """Test PR merge failure."""
    # Setup
    mock_github_utils["has_pr"].return_value = True
    mock_github_utils["merge_pr"].return_value = False

    # Execute
    result = merge_pr("feature-branch")

    # Verify
    assert result is False


def test_update_pr_base_for_children_success(
    mock_github_utils, mock_config_utils, mock_prompt
):
    """Test successful PR base update for child branches."""
    # Setup: parent -> [child1, child2], child1 -> [], child2 -> []
    mock_config_utils["get_children"].side_effect = [
        ["child1", "child2"],  # Children of parent-branch
        [],  # Children of child1
        [],  # Children of child2
    ]
    mock_github_utils["has_pr"].return_value = True
    mock_github_utils["update_base"].return_value = True

    # Execute
    result = update_pr_base_for_children("parent-branch", "main")

    # Verify
    assert result is True
    assert (
        mock_github_utils["update_base"].call_count == 2
    )  # Called for child1 and child2
    mock_github_utils["update_base"].assert_any_call("child1", "main")
    mock_github_utils["update_base"].assert_any_call("child2", "main")
    assert (
        mock_config_utils["get_children"].call_count == 3
    )  # Called for parent, child1, child2


def test_update_pr_base_for_children_no_children(mock_config_utils):
    """Test PR base update when no child branches exist."""
    # Setup
    mock_config_utils["get_children"].return_value = []

    # Execute
    result = update_pr_base_for_children("parent-branch", "main")

    # Verify
    assert result is True


def test_cleanup_local_branch_success(mock_git_utils, mock_config_utils, mock_prompt):
    """Test successful local branch cleanup."""
    # Setup
    mock_git_utils["exists"].return_value = True
    mock_git_utils["run"].return_value = "success"
    mock_config_utils["remove"].return_value = True  # Successful stack removal

    # Execute
    result = cleanup_local_branch("feature-branch")

    # Verify
    assert result is True
    mock_git_utils["run"].assert_called_with(["branch", "-D", "feature-branch"])
    mock_config_utils["remove"].assert_called_once_with("feature-branch")


def test_cleanup_local_branch_current_branch(
    mock_git_utils, mock_config_utils, mock_prompt
):
    """Test cleanup when branch is current branch."""
    # Setup
    mock_git_utils["exists"].return_value = True
    mock_git_utils["current"].return_value = "feature-branch"
    mock_git_utils["run"].return_value = "success"
    mock_config_utils["get_parent"].return_value = "main"

    # Execute
    result = cleanup_local_branch("feature-branch")

    # Verify
    assert result is True
    mock_git_utils["checkout"].assert_called_once_with("main")


def test_get_merge_method(mock_prompt):
    """Test merge method selection."""
    # Setup
    mock_prompt["select"].return_value = "squash"

    # Execute
    result = get_merge_method()

    # Verify
    assert result == "squash"
    mock_prompt["select"].assert_called_once()


def test_merge_branch_success(
    mock_git_utils,
    mock_config_utils,
    mock_github_utils,
    mock_branch_ops,
    mock_prompt,
):
    """Test successful branch merge with all operations."""
    # Setup
    mock_config_utils["get_parent"].return_value = "main"
    mock_github_utils["has_pr"].return_value = True
    mock_github_utils["merge_pr"].return_value = True
    mock_prompt["select"].return_value = "squash"
    mock_prompt["confirm"].return_value = True
    mock_branch_ops["update"].return_value = (True, None)

    # Execute
    merge_branch("feature-branch")

    # Verify
    mock_git_utils["delete_remote"].assert_called_once_with("feature-branch")
    mock_branch_ops["return"].assert_called_once()


def test_merge_branch_no_github_cli(mock_github_utils):
    """Test merge attempt without GitHub CLI installed."""
    # Setup
    mock_github_utils["check_cli"].return_value = False

    # Execute and verify
    with pytest.raises(SystemExit):
        merge_branch("feature-branch")


def test_merge_branch_user_cancellation(
    mock_git_utils,
    mock_config_utils,
    mock_github_utils,
    mock_prompt,
):
    """Test merge cancellation by user."""
    # Setup
    mock_config_utils["get_parent"].return_value = "main"
    mock_prompt["select"].return_value = "squash"
    mock_prompt["confirm"].return_value = False

    # Execute
    merge_branch("feature-branch")

    # Verify no merge operations occurred
    mock_github_utils["merge_pr"].assert_not_called()
    mock_git_utils["delete_remote"].assert_not_called()


def test_merge_branch_with_children(
    mock_git_utils,
    mock_config_utils,
    mock_github_utils,
    mock_branch_ops,
    mock_prompt,
):
    """Test merge with child branches that need updating."""
    # Setup
    mock_config_utils["get_parent"].return_value = "main"
    # Setup side_effect for get_children:
    # 1. update_pr_base_for_children('feature-branch') -> [child1, child2]
    # 2. update_pr_base_for_children('child1') -> []
    # 3. update_pr_base_for_children('child2') -> []
    # 4. update_child_branches('feature-branch') -> [child1, child2]
    # 5. update_child_branches('child1') -> [] (inside recursive call)
    # 6. update_child_branches('child2') -> [] (inside recursive call)
    mock_config_utils["get_children"].side_effect = [
        ["child1", "child2"],
        [],
        [],
        ["child1", "child2"],  # Called again in update_child_branches
        [],  # For recursive call on child1
        [],  # For recursive call on child2
    ]
    mock_github_utils["has_pr"].return_value = True
    mock_github_utils["merge_pr"].return_value = True
    mock_github_utils["update_base"].return_value = True
    mock_prompt["select"].return_value = "squash"
    mock_prompt["confirm"].return_value = True
    mock_branch_ops["update"].return_value = (True, None)

    # Execute
    merge_branch("feature-branch", update_children=True)

    # Verify main actions
    mock_github_utils["merge_pr"].assert_called_once()
    assert mock_github_utils["update_base"].call_count == 2
    mock_github_utils["update_base"].assert_any_call("child1", "main")
    mock_github_utils["update_base"].assert_any_call("child2", "main")
    # Verify branch updates were attempted
    assert mock_branch_ops["update"].call_count == 2  # Called for child1, child2
    mock_branch_ops["update"].assert_any_call("child1", "main", abort_on_conflict=False)
    mock_branch_ops["update"].assert_any_call("child2", "main", abort_on_conflict=False)
    mock_git_utils["delete_remote"].assert_called_once_with("feature-branch")
    mock_config_utils["remove"].assert_called_once_with("feature-branch")


@pytest.mark.parametrize(
    "checks_passed,user_confirm,expected_result",
    [
        # All checks passed - should proceed with merge
        (True, True, True),
        # Checks failed but user confirms - should proceed with merge
        (False, True, True),
        # Checks failed and user cancels - should abort
        (False, False, False),
    ],
)
def test_merge_with_checks_status(
    checks_passed,
    user_confirm,
    expected_result,
    mock_github_utils,
    mock_prompt,
    mock_branch_ops,
):
    """Test that merge warns about failed checks and respects user confirmation."""
    with (
        patch("panqake.utils.github.get_pr_checks_status", return_value=checks_passed),
        patch("panqake.commands.merge.fetch_latest_base_branch"),
        patch("panqake.commands.merge.handle_pr_base_updates"),
        patch("panqake.commands.merge.prompt_confirm", return_value=user_confirm),
        patch("panqake.commands.merge.merge_pr", return_value=True),
        patch("panqake.commands.merge.delete_remote_branch"),
        patch("panqake.commands.merge.handle_branch_updates"),
        patch("panqake.commands.merge.cleanup_local_branch"),
        patch("panqake.commands.merge.return_to_branch"),
        patch("panqake.commands.merge.print_formatted_text"),
    ):
        from panqake.commands.merge import perform_merge_operations

        result = perform_merge_operations(
            "test-branch", "main", "current-branch", "squash", True, True
        )

        assert result == expected_result
