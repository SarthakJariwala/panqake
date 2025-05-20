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
            "panqake.commands.sync.update_branch_with_conflict_detection"
        ) as mock_update,
        patch("panqake.commands.sync.is_branch_pushed_to_remote") as mock_is_pushed,
        patch("panqake.commands.sync.push_branch_to_remote") as mock_push,
    ):
        mock_fetch.return_value = True
        mock_update.return_value = (True, None)
        mock_is_pushed.return_value = True
        mock_push.return_value = True
        yield {
            "fetch": mock_fetch,
            "return": mock_return,
            "update": mock_update,
            "is_pushed": mock_is_pushed,
            "push": mock_push,
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
    # Simulate hierarchy: main -> feature -> feature1 -> (end)
    mock_stack_utils.get_children.side_effect = [
        ["feature1"],  # Children of 'feature'
        [],  # Children of 'feature1'
    ]
    mock_branch_ops["update"].return_value = (True, None)

    # Execute: Start update from 'feature', assuming current branch is irrelevant here
    updated, conflicts = update_branches_with_conflict_handling(
        "feature", "current-irrelevant"
    )

    # Verify: Should succeed with updated branches and no conflicts
    assert updated == ["feature1"]
    assert conflicts == []
    # Update called for feature1 (based on feature)
    mock_branch_ops["update"].assert_called_once_with(
        "feature1",
        "feature",
        abort_on_conflict=True,  # Sync uses abort=True
    )


def test_update_branches_with_conflict_handling_conflict(
    mock_stack_utils, mock_branch_ops
):
    """Test update of branches with conflict."""
    mock_stack_utils.get_children.side_effect = [
        ["feature1", "feature2"],  # Children of main
        [],  # Children of feature1
        [],  # Children of feature2
    ]
    # Set up conflicts for feature1 but success for feature2
    mock_branch_ops["update"].side_effect = [
        (False, "Conflict in feature1"),  # First call for feature1
        (True, None),  # Second call for feature2
    ]

    updated, conflicts = update_branches_with_conflict_handling("main", "feature")

    # The function should now continue processing after conflicts
    assert "feature1" in conflicts
    assert "feature2" in updated

    # Both branches should be processed
    assert mock_branch_ops["update"].call_count == 2


def test_update_branches_with_conflict_handling_parent_conflicts(
    mock_stack_utils, mock_branch_ops
):
    """Test skipping branches whose parents had conflicts."""
    # Simulate a hierarchy: main -> feature1 -> feature3
    #                       main -> feature2
    mock_stack_utils.get_children.side_effect = [
        ["feature1", "feature2"],  # Children of main
        ["feature3"],  # Children of feature1
        [],  # Children of feature2
        [],  # Children of feature3
    ]

    # Set up conflict for feature1 but success for feature2
    mock_branch_ops["update"].side_effect = [
        (False, "Conflict in feature1"),  # First call for feature1
        (True, None),  # Second call for feature2
    ]

    updated, conflicts = update_branches_with_conflict_handling("main", "feature")

    # feature1 has conflict, feature2 is updated, feature3 is skipped due to parent conflict
    assert "feature1" in conflicts
    assert "feature3" in conflicts  # Should be skipped and marked as conflict
    assert "feature2" in updated

    # Only feature1 and feature2 should be processed, feature3 should be skipped
    assert mock_branch_ops["update"].call_count == 2


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

        result = sync_with_remote()

        assert result == (True, None)
        mock_branch_ops["fetch"].assert_called_once()
        mock_branch_ops["return"].assert_called_once()
        mock_branch_ops["push"].assert_called()  # Should attempt to push feature1
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

        result = sync_with_remote(skip_push=True)

        assert result == (True, None)
        mock_branch_ops["push"].assert_not_called()  # Should not attempt to push
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

        result = sync_with_remote()

        assert result == (False, "Some branches had conflicts during sync")
        mock_branch_ops["push"].assert_called()  # Should still push feature2
        mock_prompt["print"].assert_any_call(
            "[warning]The following branches had conflicts during sync:[/warning]"
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
