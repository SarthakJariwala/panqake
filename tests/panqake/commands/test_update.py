"""Tests for update.py command module."""

from unittest.mock import patch

import pytest

from panqake.commands.update import (
    get_affected_branches,
    update_branch_and_children,
    update_branches,
    validate_branch,
)


@pytest.fixture
def mock_git_utils():
    """Mock git utility functions."""
    with (
        patch("panqake.commands.update.get_current_branch") as mock_current,
    ):
        mock_current.return_value = "feature-1"
        yield {
            "current": mock_current,
        }


@pytest.fixture
def mock_stack_utils():
    """Mock stack utility functions."""
    with patch("panqake.commands.update.Stacks") as MockStacks:
        mock_stacks = MockStacks.return_value.__enter__.return_value
        mock_stacks.get_children.return_value = ["feature-2", "feature-3"]
        mock_stacks.get_all_descendants.return_value = ["feature-2", "feature-3"]
        mock_stacks.branch_exists.return_value = True
        yield mock_stacks


@pytest.fixture
def mock_branch_ops():
    """Mock branch operation functions."""
    with (
        patch(
            "panqake.commands.update.update_branches_and_handle_conflicts"
        ) as mock_update_branches,
        patch("panqake.commands.update.return_to_branch") as mock_return,
        patch("panqake.commands.update.push_updated_branches") as mock_push,
    ):
        mock_update_branches.return_value = (["feature-2", "feature-3"], [])
        mock_push.return_value = ["feature-2", "feature-3"]
        yield {
            "update_branches": mock_update_branches,
            "return": mock_return,
            "push": mock_push,
        }


@pytest.fixture
def mock_prompt():
    """Mock questionary prompt functions."""
    with (
        patch("panqake.commands.update.prompt_confirm") as mock_confirm,
        patch("panqake.commands.update.print_formatted_text") as mock_print,
    ):
        mock_confirm.return_value = True
        yield {
            "confirm": mock_confirm,
            "print": mock_print,
        }


def test_validate_branch_exists(mock_git_utils, mock_stack_utils):
    """Test validating an existing branch."""
    # Execute
    branch_name, current = validate_branch("test-branch")

    # Verify
    mock_stack_utils.branch_exists.assert_called_once_with("test-branch")
    assert branch_name == "test-branch"
    assert current == "feature-1"


def test_validate_branch_not_exists(mock_git_utils, mock_stack_utils):
    """Test validating a non-existent branch."""
    # Setup
    mock_stack_utils.branch_exists.return_value = False

    # Execute and verify
    with pytest.raises(SystemExit):
        validate_branch("non-existent")


def test_validate_branch_no_name(mock_git_utils, mock_stack_utils):
    """Test validating with no branch name provided."""
    # Setup: Return 'main' when get_current_branch is called
    mock_git_utils["current"].return_value = "main"

    # Execute
    branch_name, current = validate_branch(None)

    # Verify: get_current_branch is called twice
    # 1. To determine the branch_name when None is passed
    # 2. To return the current_branch at the end
    assert mock_git_utils["current"].call_count == 2
    assert branch_name == "main"  # Should be the resolved current branch
    assert current == "main"  # Should be the final current branch call
    # Check branch_exists was called with the resolved branch name
    mock_stack_utils.branch_exists.assert_called_once_with("main")


def test_get_affected_branches_with_children(mock_stack_utils, mock_prompt):
    """Test getting affected branches with confirmation."""
    # Execute
    result = get_affected_branches("feature-1")

    # Verify
    assert result == ["feature-2", "feature-3"]
    mock_prompt["confirm"].assert_called_once()


def test_get_affected_branches_no_children(mock_stack_utils, mock_prompt):
    """Test getting affected branches when there are no children."""
    # Setup
    mock_stack_utils.get_all_descendants.return_value = []

    # Execute
    result = get_affected_branches("feature-1")

    # Verify
    assert result is None
    mock_prompt["confirm"].assert_not_called()


def test_get_affected_branches_user_cancels(mock_stack_utils, mock_prompt):
    """Test when user cancels the update operation."""
    # Setup
    mock_prompt["confirm"].return_value = False

    # Execute
    result = get_affected_branches("feature-1")

    # Verify
    assert result is None


def test_update_branch_and_children_success(mock_stack_utils, mock_branch_ops):
    """Test successful branch updates with the new non-recursive approach."""
    # Execute
    updated_branches, conflict_branches = update_branch_and_children(
        "feature-1", "feature-1"
    )

    # Verify
    # The function now delegates to update_branches_and_handle_conflicts
    mock_branch_ops["update_branches"].assert_called_once_with("feature-1", "feature-1")
    assert set(updated_branches) == {"feature-2", "feature-3"}
    assert len(updated_branches) == 2
    assert len(conflict_branches) == 0


def test_update_branch_and_children_conflict(mock_stack_utils, mock_branch_ops):
    """Test handling update conflicts."""
    # Setup
    mock_branch_ops["update_branches"].return_value = ([], ["feature-2", "feature-3"])

    # Execute
    updated_branches, conflict_branches = update_branch_and_children(
        "feature-1", "feature-1"
    )

    # Verify
    mock_branch_ops["update_branches"].assert_called_once_with("feature-1", "feature-1")
    assert len(updated_branches) == 0
    assert set(conflict_branches) == {"feature-2", "feature-3"}


def test_update_branches_full_success(
    mock_git_utils,
    mock_stack_utils,
    mock_branch_ops,
    mock_prompt,
):
    """Test full update process with pushing to remote."""
    mock_stack_utils.get_all_descendants.return_value = ["feature-2", "feature-3"]
    # Assume validate_branch determines current branch is 'main'
    mock_git_utils["current"].return_value = "main"

    update_branches("feature-1")

    mock_stack_utils.get_all_descendants.assert_called_with("feature-1")
    mock_branch_ops["update_branches"].assert_called_once_with("feature-1", "main")
    mock_branch_ops["push"].assert_called_once_with(["feature-2", "feature-3"])
    mock_branch_ops["return"].assert_called_once_with("main")
    assert mock_prompt["print"].call_args_list[-1].args[0].startswith("[success]")


def test_update_branches_skip_push(
    mock_git_utils,
    mock_stack_utils,
    mock_branch_ops,
    mock_prompt,
):
    """Test update process without pushing to remote."""
    mock_stack_utils.get_all_descendants.return_value = ["feature-2", "feature-3"]
    mock_git_utils["current"].return_value = "main"

    update_branches("feature-1", skip_push=True)

    mock_stack_utils.get_all_descendants.assert_called_with("feature-1")
    mock_branch_ops["update_branches"].assert_called_once_with("feature-1", "main")
    mock_branch_ops["return"].assert_called_once_with("main")
    success_message_found = False
    for call in mock_prompt["print"].call_args_list:
        if "local only" in call.args[0] and call.args[0].startswith("[success]"):
            success_message_found = True
            break
    assert success_message_found, "Success message with 'local only' not found"


def test_update_branches_with_conflicts(
    mock_git_utils,
    mock_stack_utils,
    mock_branch_ops,
    mock_prompt,
):
    """Test update process with conflict branches."""
    mock_stack_utils.get_all_descendants.return_value = ["feature-2", "feature-3"]
    mock_branch_ops["update_branches"].return_value = (["feature-2"], ["feature-3"])
    mock_git_utils["current"].return_value = "main"

    with patch(
        "panqake.commands.update.report_update_conflicts",
        return_value=(False, "Some branches had conflicts during update"),
    ) as mock_report:
        result, error = update_branches("feature-1")

    assert result is False
    assert "conflicts" in error
    mock_stack_utils.get_all_descendants.assert_called_with("feature-1")
    mock_branch_ops["update_branches"].assert_called_once_with("feature-1", "main")
    mock_branch_ops["push"].assert_called_once_with(["feature-2"])
    mock_branch_ops["return"].assert_called_once_with("main")
    mock_report.assert_called_once_with(["feature-3"])
