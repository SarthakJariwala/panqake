"""Tests for sync.py command module."""

from unittest.mock import patch

import pytest

from panqake.commands.sync import (
    get_merged_branches,
    handle_branch_updates,
    handle_merged_branches,
    sync_with_remote,
    update_branches_with_conflict_handling,
)


@pytest.fixture
def mock_git_utils():
    """Mock git utility functions."""
    with (
        patch("panqake.commands.sync.run_git_command") as mock_run,
        patch("panqake.commands.sync.get_current_branch") as mock_current,
        patch("panqake.commands.sync.checkout_branch") as mock_checkout,
    ):
        mock_current.return_value = "feature"
        yield {
            "run": mock_run,
            "current": mock_current,
            "checkout": mock_checkout,
        }


@pytest.fixture
def mock_config_utils():
    """Mock config utility functions."""
    with (
        patch("panqake.commands.sync.get_child_branches") as mock_children,
        patch("panqake.commands.sync.get_parent_branch") as mock_parent,
        patch("panqake.commands.sync.remove_from_stack") as mock_remove,
    ):
        mock_children.return_value = ["feature1", "feature2"]
        mock_parent.return_value = "main"
        yield {
            "children": mock_children,
            "parent": mock_parent,
            "remove": mock_remove,
        }


@pytest.fixture
def mock_branch_ops():
    """Mock branch operation functions."""
    with (
        patch("panqake.commands.sync.fetch_latest_from_remote") as mock_fetch,
        patch("panqake.commands.sync.return_to_branch") as mock_return,
        patch(
            "panqake.commands.sync.update_branch_with_conflict_detection"
        ) as mock_update,
    ):
        mock_fetch.return_value = True
        mock_update.return_value = (True, None)
        yield {
            "fetch": mock_fetch,
            "return": mock_return,
            "update": mock_update,
        }


@pytest.fixture
def mock_prompt():
    """Mock questionary prompt functions."""
    with (
        patch("panqake.commands.sync.print_formatted_text") as mock_print,
        patch("panqake.commands.sync.prompt_confirm") as mock_confirm,
    ):
        mock_confirm.return_value = True
        yield {
            "print": mock_print,
            "confirm": mock_confirm,
        }


def test_get_merged_branches_empty(mock_git_utils):
    """Test getting merged branches when none exist."""
    mock_git_utils["run"].return_value = ""

    result = get_merged_branches()

    assert result == []
    mock_git_utils["run"].assert_called_once_with(["branch", "--merged", "main"])


def test_get_merged_branches_with_results(mock_git_utils):
    """Test getting merged branches with multiple results."""
    mock_git_utils["run"].return_value = "  branch1\n* branch2\n  branch3\n  main"

    result = get_merged_branches()

    assert result == ["branch1", "branch2", "branch3"]
    mock_git_utils["run"].assert_called_once()


def test_handle_merged_branches_none_to_delete(
    mock_git_utils, mock_config_utils, mock_prompt
):
    """Test handling merged branches when none need deletion."""
    mock_git_utils["run"].return_value = ""

    success, deleted = handle_merged_branches("main")

    assert success is True
    assert deleted == []
    mock_prompt["confirm"].assert_not_called()


def test_handle_merged_branches_delete_confirmed(
    mock_git_utils, mock_config_utils, mock_prompt
):
    """Test handling merged branches with user confirming deletion."""
    mock_git_utils["run"].side_effect = [
        "  branch1\n  branch2",
        "Deleted branch branch1",
        "Deleted branch branch2",
    ]
    mock_prompt["confirm"].return_value = True

    success, deleted = handle_merged_branches("main")

    assert success is True
    assert deleted == ["branch1", "branch2"]
    assert mock_git_utils["run"].call_count == 3
    mock_config_utils["remove"].assert_any_call("branch1")
    mock_config_utils["remove"].assert_any_call("branch2")


def test_handle_merged_branches_delete_declined(
    mock_git_utils, mock_config_utils, mock_prompt
):
    """Test handling merged branches with user declining deletion."""
    mock_git_utils["run"].return_value = "  branch1\n  branch2"
    mock_prompt["confirm"].return_value = False

    success, deleted = handle_merged_branches("main")

    assert success is True
    assert deleted == []
    mock_config_utils["remove"].assert_not_called()


def test_update_branches_with_conflict_handling_no_children(mock_config_utils):
    """Test updating branches when no children exist."""
    mock_config_utils["children"].return_value = []

    success, failed = update_branches_with_conflict_handling("main", "feature")

    assert success is True
    assert failed == []


def test_update_branches_with_conflict_handling_success(
    mock_config_utils, mock_branch_ops
):
    """Test successful update of branches without conflicts."""
    # Simulate hierarchy: main -> feature -> feature1 -> (end)
    mock_config_utils["children"].side_effect = [
        ["feature1"],  # Children of 'feature'
        [],  # Children of 'feature1'
    ]
    mock_branch_ops["update"].return_value = (True, None)

    # Execute: Start update from 'feature', assuming current branch is irrelevant here
    success, failed = update_branches_with_conflict_handling(
        "feature", "current-irrelevant"
    )

    # Verify: Should succeed with no failed branches
    assert success is True
    assert failed == []
    # Update called for feature1 (based on feature)
    mock_branch_ops["update"].assert_called_once_with(
        "feature1",
        "feature",
        abort_on_conflict=True,  # Sync uses abort=True
    )
    # Ensure get_child_branches was called for 'feature' and 'feature1'
    assert mock_config_utils["children"].call_count == 2


def test_update_branches_with_conflict_handling_conflict(
    mock_config_utils, mock_branch_ops
):
    """Test update of branches with conflict."""
    mock_config_utils["children"].return_value = ["feature1"]
    mock_branch_ops["update"].return_value = (False, "Conflict in feature1")

    success, failed = update_branches_with_conflict_handling("main", "feature")

    assert success is False
    assert "feature1" in failed


def test_handle_branch_updates_no_children(mock_config_utils):
    """Test handling branch updates when no children exist."""
    mock_config_utils["children"].return_value = []

    success, failed = handle_branch_updates("main", "feature")

    assert success is True
    assert failed == []


def test_handle_branch_updates_with_conflicts(
    mock_config_utils, mock_branch_ops, mock_prompt
):
    """Test handling branch updates with conflicts."""
    mock_config_utils["children"].return_value = ["feature1"]
    mock_branch_ops["update"].return_value = (False, "Conflict in feature1")

    success, failed = handle_branch_updates("main", "feature")

    assert success is False
    assert "feature1" in failed
    assert mock_prompt["print"].call_count >= 2  # Warning and branch name


def test_sync_with_remote_success(mock_git_utils, mock_branch_ops, mock_prompt):
    """Test successful sync with remote."""
    mock_branch_ops["fetch"].return_value = True
    mock_git_utils["run"].return_value = ""  # No merged branches

    sync_with_remote()

    mock_branch_ops["fetch"].assert_called_once()
    mock_branch_ops["return"].assert_called_once()
    mock_prompt["print"].assert_called_with(
        "[success]Sync completed successfully[/success]"
    )


def test_sync_with_remote_fetch_failure(mock_git_utils, mock_branch_ops, mock_prompt):
    """Test sync with remote when fetch fails."""
    mock_branch_ops["fetch"].return_value = False

    with pytest.raises(SystemExit):
        sync_with_remote()

    mock_git_utils["checkout"].assert_called_once_with("feature")


def test_sync_with_remote_no_current_branch(
    mock_git_utils, mock_branch_ops, mock_prompt
):
    """Test sync with remote when current branch cannot be determined."""
    mock_git_utils["current"].return_value = None

    with pytest.raises(SystemExit):
        sync_with_remote()

    mock_prompt["print"].assert_called_once()
    assert (
        "Unable to determine current branch" in mock_prompt["print"].call_args.args[0]
    )
