"""Tests for switch.py command module."""

from unittest.mock import patch

import pytest

from panqake.commands.switch import switch_branch


@pytest.fixture
def mock_git_utils():
    """Mock git utility functions."""
    with (
        patch("panqake.commands.switch.list_all_branches") as mock_list,
        patch("panqake.commands.switch.get_current_branch") as mock_current,
        patch("panqake.commands.switch.checkout_branch") as mock_checkout,
    ):
        mock_list.return_value = ["main", "feature", "develop"]
        mock_current.return_value = "main"
        yield {
            "list": mock_list,
            "current": mock_current,
            "checkout": mock_checkout,
        }


@pytest.fixture
def mock_prompt():
    """Mock questionary prompt functions."""
    with (
        patch("panqake.commands.switch.print_formatted_text") as mock_print,
        patch("panqake.commands.switch.prompt_select") as mock_select,
    ):
        yield {
            "print": mock_print,
            "select": mock_select,
        }


@pytest.fixture
def mock_list_command():
    """Mock list command functions."""
    with patch("panqake.commands.switch.list_branches") as mock_list:
        yield mock_list


def test_switch_branch_direct(mock_git_utils, mock_prompt, mock_list_command):
    """Test switching to a branch directly with branch name."""
    switch_branch("feature")

    mock_git_utils["checkout"].assert_called_once_with("feature")
    mock_prompt["select"].assert_not_called()


def test_switch_branch_nonexistent(mock_git_utils, mock_prompt, mock_list_command):
    """Test error when switching to nonexistent branch."""
    with pytest.raises(SystemExit):
        switch_branch("nonexistent")

    mock_git_utils["checkout"].assert_not_called()
    mock_prompt["print"].assert_called_once()
    assert "does not exist" in mock_prompt["print"].call_args.args[0]


def test_switch_branch_already_current(mock_git_utils, mock_prompt, mock_list_command):
    """Test when switching to current branch."""
    switch_branch("main")

    mock_git_utils["checkout"].assert_not_called()
    mock_prompt["print"].assert_called_once()
    assert "Already on branch" in mock_prompt["print"].call_args.args[0]


def test_switch_branch_no_branches(mock_git_utils, mock_prompt, mock_list_command):
    """Test error when no branches exist."""
    mock_git_utils["list"].return_value = []

    with pytest.raises(SystemExit):
        switch_branch()

    mock_prompt["print"].assert_called_once()
    assert "No branches found" in mock_prompt["print"].call_args.args[0]


def test_switch_branch_interactive(mock_git_utils, mock_prompt, mock_list_command):
    """Test interactive branch selection."""
    mock_prompt["select"].return_value = "feature"

    switch_branch()

    # Should show branch list before and after
    assert mock_list_command.call_count == 2
    # Should call select with choices excluding current branch
    mock_prompt["select"].assert_called_once()
    choices = mock_prompt["select"].call_args.args[1]
    assert len(choices) == 2  # main excluded
    assert all(c["value"] != "main" for c in choices)
    # Should checkout selected branch
    mock_git_utils["checkout"].assert_called_once_with("feature")


def test_switch_branch_interactive_cancel(
    mock_git_utils, mock_prompt, mock_list_command
):
    """Test cancellation of interactive selection."""
    mock_prompt["select"].return_value = None

    switch_branch()

    mock_list_command.assert_called_once()  # Only initial list
    mock_git_utils["checkout"].assert_not_called()


def test_switch_branch_no_other_branches(
    mock_git_utils, mock_prompt, mock_list_command
):
    """Test when no other branches available to switch to."""
    mock_git_utils["list"].return_value = ["main"]

    switch_branch()

    mock_prompt["print"].assert_called_with(
        "[warning]No other branches available to switch to[/warning]"
    )
    mock_git_utils["checkout"].assert_not_called()
