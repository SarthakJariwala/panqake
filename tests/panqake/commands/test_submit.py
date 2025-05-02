"""Tests for submit.py command module."""

from unittest.mock import patch

import pytest

from panqake.commands.submit import update_pull_request


@pytest.fixture
def mock_git_utils():
    """Mock all git utility functions."""
    with (
        patch("panqake.commands.submit.validate_branch") as mock_validate,
        patch("panqake.commands.submit.push_branch_to_remote") as mock_push,
    ):
        mock_validate.return_value = "feature-branch"
        mock_push.return_value = True
        yield {
            "validate": mock_validate,
            "push": mock_push,
        }


@pytest.fixture
def mock_github_utils():
    """Mock GitHub utility functions."""
    with (
        patch("panqake.commands.submit.check_github_cli_installed") as mock_check_cli,
        patch("panqake.commands.submit.branch_has_pr") as mock_has_pr,
        patch("panqake.commands.submit.create_pr_for_branch") as mock_create_pr,
    ):
        mock_check_cli.return_value = True
        mock_has_pr.return_value = False
        mock_create_pr.return_value = True
        yield {
            "check_cli": mock_check_cli,
            "has_pr": mock_has_pr,
            "create_pr": mock_create_pr,
        }


@pytest.fixture
def mock_config_utils():
    """Mock config utility functions."""
    with patch("panqake.commands.submit.get_parent_branch") as mock_get_parent:
        mock_get_parent.return_value = "main"
        yield {
            "get_parent": mock_get_parent,
        }


@pytest.fixture
def mock_prompt():
    """Mock questionary prompt functions."""
    with (
        patch("panqake.commands.submit.print_formatted_text") as mock_print,
        patch("panqake.commands.submit.prompt_confirm") as mock_confirm,
    ):
        mock_confirm.return_value = True
        yield {
            "print": mock_print,
            "confirm": mock_confirm,
        }


def test_update_pull_request_no_gh_cli(mock_github_utils, mock_prompt):
    """Test update_pull_request when GitHub CLI is not installed."""
    # Setup
    mock_github_utils["check_cli"].return_value = False

    # Execute and verify it exits with code 1
    with pytest.raises(SystemExit) as e:
        update_pull_request()
    assert e.value.code == 1
    # Verify error messages were printed
    mock_prompt["print"].assert_any_call(
        "[warning]Error: GitHub CLI (gh) is required but not installed.[/warning]"
    )


def test_update_pull_request_existing_pr(
    mock_git_utils, mock_github_utils, mock_prompt
):
    """Test updating a branch that has an existing PR."""
    # Setup
    mock_github_utils["has_pr"].return_value = True
    mock_prompt["confirm"].return_value = True  # Confirm force push
    mock_git_utils["push"].return_value = True  # Assume push succeeds

    # Execute
    update_pull_request("feature-branch")

    # Verify
    mock_git_utils["push"].assert_called_once_with("feature-branch", force=True)
    # Check the exact success message from submit.py
    mock_prompt["print"].assert_any_call(
        "[success]PR for feature-branch has been updated[/success]"
    )


def test_update_pull_request_no_pr_create_confirmed(
    mock_git_utils, mock_github_utils, mock_config_utils, mock_prompt
):
    """Test updating a branch without PR and user confirms PR creation."""
    # Setup
    mock_github_utils["has_pr"].return_value = False
    mock_prompt["confirm"].side_effect = [True, True]  # Force push and create PR
    mock_config_utils["get_parent"].return_value = "main"

    # Execute
    update_pull_request("feature-branch")

    # Verify
    mock_git_utils["push"].assert_called_once_with("feature-branch", force=True)
    mock_github_utils["create_pr"].assert_called_once_with("feature-branch", "main")


def test_update_pull_request_no_pr_create_declined(
    mock_git_utils, mock_github_utils, mock_prompt
):
    """Test updating a branch without PR and user declines PR creation."""
    # Setup
    mock_github_utils["has_pr"].return_value = False
    mock_prompt["confirm"].side_effect = [True, False]  # Force push but decline PR

    # Execute
    update_pull_request("feature-branch")

    # Verify
    mock_git_utils["push"].assert_called_once_with("feature-branch", force=True)
    mock_prompt["print"].assert_any_call("[info]To create a PR, run: pq pr[/info]")


def test_update_pull_request_force_push_declined(
    mock_git_utils, mock_github_utils, mock_prompt
):
    """Test when user declines force push."""
    # Setup
    mock_github_utils["has_pr"].return_value = True
    mock_prompt["confirm"].return_value = False  # Decline force push

    # Execute
    update_pull_request("feature-branch")

    # Verify
    mock_git_utils["push"].assert_called_once_with("feature-branch", force=False)


def test_update_pull_request_push_failed(
    mock_git_utils, mock_github_utils, mock_prompt
):
    """Test when branch push fails."""
    # Setup
    mock_github_utils["has_pr"].return_value = True
    mock_git_utils["push"].return_value = False  # Push fails
    mock_prompt["confirm"].return_value = True

    # Execute
    update_pull_request("feature-branch")

    # Verify
    mock_git_utils["push"].assert_called_once_with("feature-branch", force=True)
    # Check that info messages were printed, but not the final success message
    info_calls = 0
    success_call_found = False
    expected_success_message = (
        "[success]PR for feature-branch has been updated[/success]"
    )
    for call_args, call_kwargs in mock_prompt["print"].call_args_list:
        message = call_args[0]
        if message.startswith("[info]"):
            info_calls += 1
        if message == expected_success_message:
            success_call_found = True

    assert info_calls >= 1  # Should print info messages before push
    assert not success_call_found  # Should NOT print success message if push failed
