"""Tests for pr.py command module."""

from unittest.mock import patch

import pytest

from panqake.commands.pr import (
    create_pr_for_branch,
    create_pull_requests,
    ensure_branch_pushed,
    find_oldest_branch_without_pr,
    is_branch_in_path_to_target,
    process_branch_for_pr,
    prompt_for_reviewers,
)


@pytest.fixture
def mock_git_utils():
    """Mock all git utility functions."""
    with (
        patch("panqake.commands.pr.run_git_command") as mock_run,
        patch("panqake.commands.pr.get_current_branch") as mock_current,
        patch("panqake.commands.pr.branch_exists") as mock_exists,
        patch("panqake.commands.pr.is_branch_pushed_to_remote") as mock_pushed,
        patch("panqake.commands.pr.push_branch_to_remote") as mock_push,
    ):
        mock_current.return_value = "feature-branch"
        mock_exists.return_value = True
        yield {
            "run": mock_run,
            "current": mock_current,
            "exists": mock_exists,
            "pushed": mock_pushed,
            "push": mock_push,
        }


@pytest.fixture
def mock_config_utils():
    """Mock config utility functions."""
    with (
        patch("panqake.commands.pr.get_parent_branch") as mock_get_parent,
        patch("panqake.commands.pr.get_child_branches") as mock_get_children,
    ):
        mock_get_parent.return_value = "main"
        mock_get_children.return_value = []
        yield {
            "get_parent": mock_get_parent,
            "get_children": mock_get_children,
        }


@pytest.fixture
def mock_github_utils():
    """Mock GitHub utility functions."""
    with (
        patch(
            "panqake.commands.pr.check_github_cli_installed"
        ) as mock_check_cli,
        patch("panqake.commands.pr.branch_has_pr") as mock_has_pr,
        patch("panqake.commands.pr.create_pr") as mock_create_pr,
        patch(
            "panqake.commands.pr.get_potential_reviewers"
        ) as mock_get_reviewers,
    ):
        mock_check_cli.return_value = True
        mock_has_pr.return_value = False
        mock_create_pr.return_value = (
            True,
            "https://github.com/user/repo/pull/123",
        )
        mock_get_reviewers.return_value = ["reviewer1", "reviewer2"]
        yield {
            "check_cli": mock_check_cli,
            "has_pr": mock_has_pr,
            "create_pr": mock_create_pr,
            "get_reviewers": mock_get_reviewers,
        }


@pytest.fixture
def mock_prompt():
    """Mock questionary prompt functions."""
    with (
        patch("panqake.commands.pr.print_formatted_text") as mock_print,
        patch("panqake.commands.pr.prompt_confirm") as mock_confirm,
        patch("panqake.commands.pr.prompt_input") as mock_input,
        patch(
            "panqake.commands.pr.prompt_for_reviewers"
        ) as mock_prompt_reviewers,
        patch("panqake.commands.pr.console.print") as mock_console_print,
    ):
        mock_confirm.return_value = True
        mock_input.return_value = "Test PR"
        mock_prompt_reviewers.return_value = []
        yield {
            "print": mock_print,
            "confirm": mock_confirm,
            "input": mock_input,
            "prompt_reviewers": mock_prompt_reviewers,
            "console_print": mock_console_print,
        }


def test_find_oldest_branch_without_pr_no_parent(
    mock_config_utils, mock_github_utils
):
    """Test finding oldest branch when there's no parent."""
    # Setup
    mock_config_utils["get_parent"].return_value = None

    # Execute
    result = find_oldest_branch_without_pr("feature-branch")

    # Verify
    assert result == "feature-branch"


def test_find_oldest_branch_without_pr_parent_has_pr(
    mock_config_utils, mock_github_utils
):
    """Test finding oldest branch when parent has PR."""
    # Setup
    mock_config_utils["get_parent"].return_value = "parent-branch"
    mock_github_utils["has_pr"].return_value = True

    # Execute
    result = find_oldest_branch_without_pr("feature-branch")

    # Verify
    assert result == "feature-branch"


def test_find_oldest_branch_without_pr_recursive(
    mock_config_utils, mock_github_utils
):
    """Test finding oldest branch recursively."""
    # Setup
    mock_config_utils["get_parent"].side_effect = [
        "parent-branch",
        "grandparent-branch",
        None,
    ]
    mock_github_utils["has_pr"].return_value = False

    # Execute
    result = find_oldest_branch_without_pr("feature-branch")

    # Verify
    assert result == "grandparent-branch"


def test_is_branch_in_path_to_target_direct_path(mock_config_utils):
    """Test checking if branch is in direct path to target."""
    # Setup
    mock_config_utils["get_parent"].side_effect = ["parent-branch", "main"]

    # Execute
    result = is_branch_in_path_to_target(
        "parent-branch", "feature-branch", "main"
    )

    # Verify
    assert result is True


def test_is_branch_in_path_to_target_not_in_path(mock_config_utils):
    """Test checking if branch is not in path to target."""
    # Setup
    mock_config_utils["get_parent"].side_effect = ["other-branch", "main"]

    # Execute
    result = is_branch_in_path_to_target(
        "unrelated-branch", "feature-branch", "main"
    )

    # Verify
    assert result is False


@patch("panqake.commands.pr.run_git_command")
@patch("panqake.commands.pr.is_branch_pushed_to_remote")
@patch("panqake.commands.pr.push_branch_to_remote")
def test_process_branch_for_pr_with_children(
    mock_push,
    mock_is_pushed,
    mock_run_git,
    mock_config_utils,
    mock_github_utils,
    mock_prompt,
):
    """Test processing branch with children."""
    # Setup
    # Stop recursion: feature -> child -> (None)
    mock_config_utils["get_children"].side_effect = [
        ["child-branch"],  # Children of feature-branch
        [],  # Children of child-branch
    ]
    mock_config_utils["get_parent"].return_value = "main"
    mock_is_pushed.return_value = True  # Assume branches are pushed

    # Mock the git log command
    log_output = "feat: Test Commit\n\nSome body."

    def run_git_side_effect(command):
        if command[:2] == ["log", "main..feature-branch"]:
            return log_output
        # Add log for child branch if needed
        if command[:2] == ["log", "feature-branch..child-branch"]:
            return "feat: Child commit"
        return "Default git output"

    mock_run_git.side_effect = run_git_side_effect

    # Execute
    process_branch_for_pr("feature-branch", "child-branch")

    # Verify is_pushed was checked
    mock_is_pushed.assert_any_call("feature-branch")
    mock_is_pushed.assert_any_call("main")
    # Verify git log was run for feature-branch
    mock_run_git.assert_any_call(["log", "main..feature-branch", "--oneline"])
    # Verify create_pr was called for feature-branch
    mock_github_utils["create_pr"].assert_called()
    # Verify get_children was called twice (feature-branch, child-branch)
    assert mock_config_utils["get_children"].call_count == 2


def test_create_pull_requests_no_gh_cli(mock_github_utils, mock_prompt):
    """Test create_pull_requests when GitHub CLI is not installed."""
    # Setup
    mock_github_utils["check_cli"].return_value = False

    # Execute and verify
    with pytest.raises(SystemExit):
        create_pull_requests()


def test_create_pull_requests_branch_not_exists(mock_git_utils, mock_prompt):
    """Test create_pull_requests with non-existent branch."""
    # Setup
    mock_git_utils["exists"].return_value = False

    # Execute and verify
    with pytest.raises(SystemExit):
        create_pull_requests("nonexistent-branch")


def test_ensure_branch_pushed_already_pushed(mock_git_utils):
    """Test ensure_branch_pushed when branch is already pushed."""
    # Setup
    mock_git_utils["pushed"].return_value = True

    # Execute
    result = ensure_branch_pushed("feature-branch")

    # Verify
    assert result is True


def test_ensure_branch_pushed_push_confirmed(mock_git_utils, mock_prompt):
    """Test ensure_branch_pushed with user confirming push."""
    # Setup
    mock_git_utils["pushed"].return_value = False
    mock_prompt["confirm"].return_value = True
    mock_git_utils["push"].return_value = True

    # Execute
    result = ensure_branch_pushed("feature-branch")

    # Verify
    assert result is True
    mock_git_utils["push"].assert_called_once_with("feature-branch")


def test_ensure_branch_pushed_push_declined(mock_git_utils, mock_prompt):
    """Test ensure_branch_pushed with user declining push."""
    # Setup
    mock_git_utils["pushed"].return_value = False
    mock_prompt["confirm"].return_value = False

    # Execute
    result = ensure_branch_pushed("feature-branch")

    # Verify
    assert result is False


def test_create_pr_for_branch_no_commits(mock_git_utils, mock_prompt):
    """Test PR creation with no commits between branches."""
    # Setup
    mock_git_utils["pushed"].return_value = True
    mock_git_utils["run"].return_value = ""

    # Execute
    result = create_pr_for_branch("feature-branch", "main")

    # Verify
    assert result is False


def test_create_pr_for_branch_user_cancelled(
    mock_git_utils, mock_github_utils, mock_prompt
):
    """Test PR creation cancelled by user."""
    # Setup
    mock_git_utils["pushed"].return_value = True
    mock_git_utils["run"].return_value = "commit1"
    mock_prompt["confirm"].return_value = False

    # Execute
    result = create_pr_for_branch("feature-branch", "main")

    # Verify
    assert result is False


def test_prompt_for_reviewers():
    """Test prompt_for_reviewers functionality."""
    with patch("panqake.commands.pr.select_reviewers") as mock_select_reviewers:
        mock_select_reviewers.return_value = ["user1", "user2"]

        result = prompt_for_reviewers(["user1", "user2", "user3"])

        assert result == ["user1", "user2"]
        mock_select_reviewers.assert_called_once_with(
            ["user1", "user2", "user3"], include_skip_option=True
        )


def test_prompt_for_reviewers_empty_list():
    """Test prompt_for_reviewers with empty list."""
    with patch("panqake.commands.pr.select_reviewers") as mock_select_reviewers:
        mock_select_reviewers.return_value = []
        result = prompt_for_reviewers([])
        assert result == []
        mock_select_reviewers.assert_called_once_with(
            [], include_skip_option=True
        )


def test_prompt_for_reviewers_skip_selection():
    """Test prompt_for_reviewers when skip option is selected."""
    with patch("panqake.commands.pr.select_reviewers") as mock_select_reviewers:
        mock_select_reviewers.return_value = []

        result = prompt_for_reviewers(["user1", "user2"])

        assert result == []
        mock_select_reviewers.assert_called_once_with(
            ["user1", "user2"], include_skip_option=True
        )


def test_create_pr_for_branch_as_draft(
    mock_git_utils, mock_github_utils, mock_prompt
):
    """Test creating a PR as draft."""
    # Setup
    mock_git_utils["pushed"].return_value = True
    mock_git_utils["run"].return_value = "commit1\ncommit2"
    mock_prompt["confirm"].side_effect = [
        True,
        True,
    ]  # First for draft, second for creation
    mock_prompt["input"].return_value = "Test PR"
    mock_github_utils["create_pr"].return_value = (
        True,
        "https://github.com/user/repo/pull/123",
    )

    # Execute
    result = create_pr_for_branch("feature-branch", "main", draft=True)

    # Verify
    assert result is True
    # Verify create_pr was called with draft=True (it's the 6th positional argument)
    mock_github_utils["create_pr"].assert_called_once()
    call_args = mock_github_utils["create_pr"].call_args
    assert (
        call_args[0][5] is True
    )  # The draft parameter is the 6th positional argument (index 5)


def test_create_pr_for_branch_prompt_for_draft(
    mock_git_utils, mock_github_utils, mock_prompt
):
    """Test prompting for draft status when not specified."""
    # Setup
    mock_git_utils["pushed"].return_value = True
    mock_git_utils["run"].return_value = "commit1"
    mock_prompt["confirm"].side_effect = [
        True,
        True,
    ]  # First for draft prompt, second for creation
    mock_prompt["input"].return_value = "Test PR"
    mock_github_utils["create_pr"].return_value = (
        True,
        "https://github.com/user/repo/pull/123",
    )

    # Execute
    result = create_pr_for_branch("feature-branch", "main")

    # Verify
    assert result is True
    # Verify draft prompt was called
    mock_prompt["confirm"].assert_any_call("Is this a draft PR?")
    # Verify create_pr was called with draft=True (based on prompt response)
    mock_github_utils["create_pr"].assert_called_once()
    call_args = mock_github_utils["create_pr"].call_args
    assert (
        call_args[0][5] is True
    )  # The draft parameter is the 6th positional argument (index 5)


def test_process_branch_for_pr_with_draft(
    mock_config_utils, mock_github_utils, mock_prompt
):
    """Test processing branch for PR with draft flag."""
    # Setup
    mock_config_utils["get_parent"].return_value = "main"
    mock_config_utils["get_children"].return_value = []
    mock_github_utils["has_pr"].return_value = False

    with patch(
        "panqake.commands.pr.create_pr_for_branch"
    ) as mock_create_pr_for_branch:
        mock_create_pr_for_branch.return_value = True

        # Execute
        process_branch_for_pr("feature-branch", "feature-branch", draft=True)

        # Verify
        mock_create_pr_for_branch.assert_called_once_with(
            "feature-branch", "main", True
        )


def test_create_pull_requests_with_draft_flag(
    mock_git_utils, mock_config_utils, mock_github_utils, mock_prompt
):
    """Test create_pull_requests with draft flag."""
    # Setup
    mock_git_utils["current"].return_value = "feature-branch"
    mock_git_utils["exists"].return_value = True
    mock_config_utils["get_parent"].return_value = "main"
    mock_config_utils["get_children"].return_value = []
    mock_github_utils["has_pr"].return_value = False

    with patch(
        "panqake.commands.pr.find_oldest_branch_without_pr"
    ) as mock_find_oldest:
        mock_find_oldest.return_value = "feature-branch"
        with patch("panqake.commands.pr.process_branch_for_pr") as mock_process:
            # Execute
            create_pull_requests("feature-branch", draft=True)

            # Verify
            mock_process.assert_called_once_with(
                "feature-branch", "feature-branch", True
            )
