"""Tests for update.py command module."""

from unittest.mock import patch

import pytest

from panqake.commands.update import (
    collect_all_children,
    get_affected_branches,
    update_branch_and_children,
    update_branches,
    validate_branch,
)


@pytest.fixture
def mock_git_utils():
    """Mock git utility functions."""
    with (
        patch("panqake.commands.update.branch_exists") as mock_exists,
        patch("panqake.commands.update.checkout_branch") as mock_checkout,
        patch("panqake.commands.update.get_current_branch") as mock_current,
        patch("panqake.commands.update.push_branch_to_remote") as mock_push,
    ):
        mock_exists.return_value = True
        mock_current.return_value = "feature-1"
        mock_push.return_value = True
        yield {
            "exists": mock_exists,
            "checkout": mock_checkout,
            "current": mock_current,
            "push": mock_push,
        }


@pytest.fixture
def mock_config_utils():
    """Mock config utility functions."""
    with patch("panqake.commands.update.get_child_branches") as mock_children:
        mock_children.return_value = ["feature-2", "feature-3"]
        yield mock_children


@pytest.fixture
def mock_branch_ops():
    """Mock branch operation functions."""
    with (
        patch(
            "panqake.commands.update.update_branch_with_conflict_detection"
        ) as mock_update,
        patch("panqake.commands.update.return_to_branch") as mock_return,
    ):
        mock_update.return_value = (True, None)
        yield {
            "update": mock_update,
            "return": mock_return,
        }


@pytest.fixture
def mock_github_utils():
    """Mock GitHub utility functions."""
    with (
        patch("panqake.commands.update.check_github_cli_installed") as mock_cli,
        patch("panqake.commands.update.branch_has_pr") as mock_has_pr,
    ):
        mock_cli.return_value = True
        mock_has_pr.return_value = True
        yield {
            "cli": mock_cli,
            "has_pr": mock_has_pr,
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


def test_collect_all_children(mock_config_utils):
    """Test collecting all child branches recursively."""
    # Setup: feature-1 -> [feature-2, feature-3], feature-2 -> [feature-4]
    mock_config_utils.side_effect = [
        ["feature-2", "feature-3"],  # Children of feature-1
        ["feature-4"],  # Children of feature-2
        [],  # Children of feature-3
        [],  # Children of feature-4
    ]

    # Execute
    result = collect_all_children("feature-1")

    # Verify (Order depends on depth-first traversal)
    assert result == ["feature-2", "feature-4", "feature-3"]
    assert mock_config_utils.call_count == 4


def test_validate_branch_exists(mock_git_utils):
    """Test validating an existing branch."""
    # Execute
    branch_name, current = validate_branch("test-branch")

    # Verify
    mock_git_utils["exists"].assert_called_once_with("test-branch")
    assert branch_name == "test-branch"
    assert current == "feature-1"


def test_validate_branch_not_exists(mock_git_utils):
    """Test validating a non-existent branch."""
    # Setup
    mock_git_utils["exists"].return_value = False

    # Execute and verify
    with pytest.raises(SystemExit):
        validate_branch("non-existent")


def test_validate_branch_no_name(mock_git_utils):
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
    # Check exists was called with the resolved branch name
    mock_git_utils["exists"].assert_called_once_with("main")


def test_get_affected_branches_with_children(mock_config_utils, mock_prompt):
    """Test getting affected branches with confirmation."""
    # Execute
    result = get_affected_branches("feature-1")

    # Verify
    assert result == ["feature-2", "feature-3"]
    mock_prompt["confirm"].assert_called_once()


def test_get_affected_branches_no_children(mock_config_utils, mock_prompt):
    """Test getting affected branches when there are no children."""
    # Setup
    mock_config_utils.return_value = []

    # Execute
    result = get_affected_branches("feature-1")

    # Verify
    assert result is None
    mock_prompt["confirm"].assert_not_called()


def test_get_affected_branches_user_cancels(mock_config_utils, mock_prompt):
    """Test when user cancels the update operation."""
    # Setup
    mock_prompt["confirm"].return_value = False

    # Execute
    result = get_affected_branches("feature-1")

    # Verify
    assert result is None


def test_update_branch_and_children_success(mock_config_utils, mock_branch_ops):
    """Test successful recursive branch updates."""
    # Setup mock to simulate branch hierarchy and end recursion
    mock_config_utils.side_effect = [
        ["feature-2", "feature-3"],  # Children of feature-1
        [],  # Children of feature-2
        [],  # Children of feature-3
    ]
    # Execute
    # Initialize updated_branches list for tracking
    updated_branches = []
    update_branch_and_children("feature-1", "feature-1", updated_branches)

    # Verify
    # Check the contents, order might vary depending on implementation
    assert set(updated_branches) == {"feature-2", "feature-3"}
    assert len(updated_branches) == 2
    # Called once for feature-2, once for feature-3
    assert mock_branch_ops["update"].call_count == 2


def test_update_branch_and_children_conflict(mock_config_utils, mock_branch_ops):
    """Test handling update conflicts."""
    # Setup
    mock_branch_ops["update"].return_value = (False, "Merge conflict detected")

    # Execute and verify
    with pytest.raises(SystemExit):
        update_branch_and_children("feature-1", "feature-1")


@patch("panqake.commands.update.update_branch_and_children")
@patch("panqake.commands.update.collect_all_children")
def test_update_branches_full_success(
    mock_collect_children,
    mock_update_children,
    mock_git_utils,
    mock_config_utils,
    mock_branch_ops,
    mock_github_utils,
    mock_prompt,
):
    """Test full update process with pushing to remote."""
    mock_collect_children.return_value = ["feature-2", "feature-3"]
    mock_update_children.return_value = ["feature-2", "feature-3"]
    # Assume validate_branch determines current branch is 'main'
    mock_git_utils["current"].return_value = "main"

    update_branches("feature-1")

    mock_collect_children.assert_called_once_with("feature-1")
    mock_update_children.assert_called_once_with("feature-1", "main")
    mock_git_utils["push"].assert_called()
    mock_branch_ops["return"].assert_called_once_with("main")
    assert mock_prompt["print"].call_args_list[-1].args[0].startswith("[success]")


@patch("panqake.commands.update.update_branch_and_children")
@patch("panqake.commands.update.collect_all_children")
def test_update_branches_skip_push(
    mock_collect_children,
    mock_update_children,
    mock_git_utils,
    mock_config_utils,
    mock_branch_ops,
    mock_github_utils,
    mock_prompt,
):
    """Test update process without pushing to remote."""
    mock_collect_children.return_value = ["feature-2", "feature-3"]
    mock_update_children.return_value = ["feature-2", "feature-3"]
    mock_git_utils["current"].return_value = "main"

    update_branches("feature-1", skip_push=True)

    mock_collect_children.assert_called_once_with("feature-1")
    mock_update_children.assert_called_once_with("feature-1", "main")
    mock_git_utils["push"].assert_not_called()
    mock_branch_ops["return"].assert_called_once_with("main")
    success_message_found = False
    for call in mock_prompt["print"].call_args_list:
        if "local only" in call.args[0] and call.args[0].startswith("[success]"):
            success_message_found = True
            break
    assert success_message_found, "Success message with 'local only' not found"


@patch("panqake.commands.update.update_branch_and_children")
@patch("panqake.commands.update.collect_all_children")
def test_update_branches_no_github_cli(
    mock_collect_children,
    mock_update_children,
    mock_git_utils,
    mock_config_utils,
    mock_branch_ops,
    mock_github_utils,
    mock_prompt,
):
    """Test update process when GitHub CLI is not installed."""
    mock_github_utils["cli"].return_value = False
    mock_collect_children.return_value = ["feature-2", "feature-3"]
    mock_update_children.return_value = ["feature-2", "feature-3"]
    mock_git_utils["current"].return_value = "main"

    update_branches("feature-1")

    mock_collect_children.assert_called_once_with("feature-1")
    mock_update_children.assert_called_once_with("feature-1", "main")
    mock_github_utils["has_pr"].assert_not_called()
    mock_git_utils["push"].assert_called()
    mock_branch_ops["return"].assert_called_once_with("main")
