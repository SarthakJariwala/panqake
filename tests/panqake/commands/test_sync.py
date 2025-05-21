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
        patch("panqake.commands.sync.get_parent_branch") as mock_parent,
        patch("panqake.commands.sync.remove_from_stack") as mock_remove,
    ):
        mock_parent.return_value = "main"
        yield {
            "parent": mock_parent,
            "remove": mock_remove,
        }


@pytest.fixture
def mock_stack_utils():
    """Mock Stack utility functions."""
    with patch("panqake.commands.sync.Stacks") as mock_stacks:
        stack_instance = mock_stacks.return_value.__enter__.return_value
        stack_instance.get_children.return_value = ["feature1", "feature2"]
        stack_instance.get_all_descendants.return_value = ["feature1", "feature2"]
        yield stack_instance


@pytest.fixture
def mock_branch_ops():
    """Mock branch operation functions."""
    with (
        patch("panqake.commands.sync.fetch_latest_from_remote") as mock_fetch,
        patch("panqake.commands.sync.return_to_branch") as mock_return,
        patch(
            "panqake.commands.sync.update_branches_and_handle_conflicts"
        ) as mock_update_branches,
        patch("panqake.commands.sync.push_updated_branches") as mock_push,
        patch("panqake.commands.sync.report_update_conflicts") as mock_report,
    ):
        mock_fetch.return_value = True
        mock_update_branches.return_value = (["feature1", "feature2"], [])
        mock_push.return_value = ["feature1", "feature2"]
        mock_report.return_value = (True, None)
        yield {
            "fetch": mock_fetch,
            "return": mock_return,
            "update_branches": mock_update_branches,
            "push": mock_push,
            "report": mock_report,
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
    mock_config_utils["remove"].return_value = True  # Successful stack removal

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


def test_update_branches_with_conflict_handling_no_children(mock_stack_utils):
    """Test updating branches when no children exist."""
    mock_stack_utils.get_children.return_value = []

    updated, conflicts = update_branches_with_conflict_handling("main", "feature")

    assert updated == []
    assert conflicts == []


def test_update_branches_with_conflict_handling_success(
    mock_stack_utils, mock_branch_ops
):
    """Test successful update of branches without conflicts."""
    # Mock return value for the refactored function
    mock_branch_ops["update_branches"].return_value = (["feature1"], [])

    # Execute: Start update from 'feature', assuming current branch is irrelevant here
    updated, conflicts = update_branches_with_conflict_handling(
        "feature", "current-irrelevant"
    )

    # Verify: Function now delegates to the shared utility
    mock_branch_ops["update_branches"].assert_called_once_with(
        "feature", "current-irrelevant"
    )
    assert updated == ["feature1"]
    assert conflicts == []


def test_update_branches_with_conflict_handling_conflict(
    mock_stack_utils, mock_branch_ops
):
    """Test update of branches with conflict."""
    # Mock the return value for the refactored function
    mock_branch_ops["update_branches"].return_value = (["feature2"], ["feature1"])

    updated, conflicts = update_branches_with_conflict_handling("main", "feature")

    # Verify the function calls the shared utility
    mock_branch_ops["update_branches"].assert_called_once_with("main", "feature")
    assert "feature1" in conflicts
    assert "feature2" in updated


def test_update_branches_with_conflict_handling_parent_conflicts(
    mock_stack_utils, mock_branch_ops
):
    """Test skipping branches whose parents had conflicts."""
    # Mock return value for the refactored function
    mock_branch_ops["update_branches"].return_value = (
        ["feature2"],
        ["feature1", "feature3"],
    )

    updated, conflicts = update_branches_with_conflict_handling("main", "feature")

    # Verify the function calls the shared utility
    mock_branch_ops["update_branches"].assert_called_once_with("main", "feature")
    assert "feature1" in conflicts
    assert "feature3" in conflicts
    assert "feature2" in updated


def test_handle_branch_updates_no_children(mock_stack_utils):
    """Test handling branch updates when no children exist."""
    mock_stack_utils.get_children.return_value = []

    updated, conflicts = handle_branch_updates("main", "feature")

    assert updated == []
    assert conflicts == []


def test_handle_branch_updates_with_conflicts(
    mock_stack_utils, mock_branch_ops, mock_prompt
):
    """Test handling branch updates with conflicts."""
    # Patch update_branches_with_conflict_handling to return conflicts
    with patch(
        "panqake.commands.sync.update_branches_with_conflict_handling"
    ) as mock_update_branches:
        mock_update_branches.return_value = (["feature2"], ["feature1"])

        updated, conflicts = handle_branch_updates("main", "feature")

        assert "feature1" in conflicts
        assert "feature2" in updated
        assert mock_prompt["print"].call_count >= 2  # Warning and branch name


def test_sync_with_remote_success(
    mock_git_utils, mock_branch_ops, mock_prompt, mock_stack_utils
):
    """Test successful sync with remote."""
    mock_branch_ops["fetch"].return_value = True
    mock_git_utils["run"].return_value = ""  # No merged branches

    # Patch handle_branch_updates to return some updated branches
    with patch("panqake.commands.sync.handle_branch_updates") as mock_handle_updates:
        mock_handle_updates.return_value = (["feature1"], [])
        mock_branch_ops["report"].return_value = (True, None)

        result = sync_with_remote()

        assert result == (True, None)
        mock_branch_ops["fetch"].assert_called_once()
        mock_branch_ops["return"].assert_called_once()
        mock_branch_ops["push"].assert_called_once_with(
            ["feature1"]
        )  # Should attempt to push feature1
        mock_prompt["print"].assert_any_call(
            "[success]Sync completed successfully[/success]"
        )


def test_sync_with_remote_with_no_push_flag(
    mock_git_utils, mock_branch_ops, mock_prompt, mock_stack_utils
):
    """Test sync with remote with --no-push flag."""
    mock_branch_ops["fetch"].return_value = True
    mock_git_utils["run"].return_value = ""  # No merged branches

    # Patch handle_branch_updates to return some updated branches
    with patch("panqake.commands.sync.handle_branch_updates") as mock_handle_updates:
        mock_handle_updates.return_value = (["feature1"], [])
        mock_branch_ops["report"].return_value = (True, None)

        result = sync_with_remote(skip_push=True)

        assert result == (True, None)

        mock_prompt["print"].assert_any_call(
            "[success]Sync completed successfully (local only)[/success]"
        )


def test_sync_with_remote_with_conflicts(
    mock_git_utils, mock_branch_ops, mock_prompt, mock_stack_utils
):
    """Test sync with remote when there are conflicts."""
    mock_branch_ops["fetch"].return_value = True
    mock_git_utils["run"].return_value = ""  # No merged branches

    # Patch handle_branch_updates to return conflicts
    with patch("panqake.commands.sync.handle_branch_updates") as mock_handle_updates:
        mock_handle_updates.return_value = (["feature2"], ["feature1"])
        mock_branch_ops["report"].return_value = (
            False,
            "Some branches had conflicts during sync",
        )

        result = sync_with_remote()

        assert result == (False, "Some branches had conflicts during sync")
        mock_branch_ops["push"].assert_called_once_with(
            ["feature2"]
        )  # Should still push feature2
        mock_branch_ops["report"].assert_called_once_with(["feature1"])


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
