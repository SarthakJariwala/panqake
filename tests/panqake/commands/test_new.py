"""Tests for new.py command module."""

from unittest.mock import patch

import pytest

from panqake.commands.new import create_new_branch


@pytest.fixture
def mock_git_utils():
    """Mock all git utility functions."""
    with (
        patch("panqake.commands.new.branch_exists") as mock_exists,
        patch("panqake.commands.new.validate_branch") as mock_validate,
        patch("panqake.commands.new.create_branch") as mock_create,
        patch("panqake.commands.new.get_current_branch") as mock_current,
        patch("panqake.commands.new.list_all_branches") as mock_list,
    ):
        mock_current.return_value = "main"
        mock_list.return_value = ["main", "develop", "feature"]
        mock_validate.side_effect = lambda x: x  # Just return the input
        yield {
            "exists": mock_exists,
            "validate": mock_validate,
            "create": mock_create,
            "current": mock_current,
            "list": mock_list,
        }


@pytest.fixture
def mock_config_utils():
    """Mock config utility functions."""
    with patch("panqake.commands.new.add_to_stack") as mock_add:
        yield mock_add


@pytest.fixture
def mock_prompt():
    """Mock questionary prompt functions."""
    with (
        patch("panqake.commands.new.prompt_input") as mock_input,
        patch("panqake.commands.new.print_formatted_text") as mock_print,
    ):
        yield {"input": mock_input, "print": mock_print}


def test_create_new_branch_with_args(mock_git_utils, mock_config_utils, mock_prompt):
    """Test creating new branch with provided arguments."""
    # Setup
    mock_git_utils["exists"].side_effect = [
        False,
        True,
    ]  # new branch doesn't exist, base does

    # Execute
    create_new_branch("feature-branch", "main")

    # Verify
    mock_git_utils["create"].assert_called_once_with("feature-branch", "main")
    mock_config_utils.assert_called_once_with("feature-branch", "main")
    mock_prompt["print"].assert_called()  # Success message printed


def test_create_new_branch_interactive(mock_git_utils, mock_config_utils, mock_prompt):
    """Test creating new branch interactively."""
    # Setup
    mock_git_utils["exists"].side_effect = [
        False,
        True,
    ]  # new branch doesn't exist, base does
    mock_prompt["input"].side_effect = ["feature-branch", "develop"]  # User inputs

    # Execute
    create_new_branch()

    # Verify
    mock_git_utils["create"].assert_called_once_with("feature-branch", "develop")
    mock_config_utils.assert_called_once_with("feature-branch", "develop")


def test_create_new_branch_existing_branch(
    mock_git_utils, mock_config_utils, mock_prompt
):
    """Test error when new branch already exists."""
    # Setup
    mock_git_utils["exists"].return_value = True

    # Execute and verify
    with pytest.raises(SystemExit):
        create_new_branch("existing-branch", "main")

    # Verify branch was not created
    mock_git_utils["create"].assert_not_called()
    mock_config_utils.assert_not_called()


def test_create_new_branch_nonexistent_base(
    mock_git_utils, mock_config_utils, mock_prompt
):
    """Test error when base branch doesn't exist."""
    # Setup
    mock_git_utils[
        "exists"
    ].return_value = False  # new branch doesn't exist (should pass)
    mock_git_utils["validate"].side_effect = SystemExit(
        1
    )  # base branch validation fails

    # Execute and verify
    with pytest.raises(SystemExit):
        create_new_branch("feature-branch", "nonexistent")

    # Verify branch was not created
    mock_git_utils["create"].assert_not_called()
    mock_config_utils.assert_not_called()


def test_create_new_branch_default_base(mock_git_utils, mock_config_utils, mock_prompt):
    """Test creating branch with default base (current branch)."""
    # Setup
    mock_git_utils["exists"].side_effect = [
        False,  # branch_name doesn't exist
        True,  # base_branch ('main') exists
    ]
    mock_prompt["input"].side_effect = [
        "feature-branch",  # User enters branch name
        "",  # User accepts default base branch by entering empty string
    ]
    # Mock current branch which should be used as default base
    mock_git_utils["current"].return_value = "main"
    # Mock list_all_branches to ensure the base branch prompt happens
    mock_git_utils["list"].return_value = ["main", "other"]

    # Execute
    create_new_branch()

    # Verify
    # get_current_branch called to determine default base
    mock_git_utils["current"].assert_called_once()
    # list_all_branches called to provide completer
    mock_git_utils["list"].assert_called_once()
    # prompt_input called twice (name, base)
    assert mock_prompt["input"].call_count == 2
    # create_branch called with the value returned by prompt ("")
    mock_git_utils["create"].assert_called_once_with("feature-branch", "")
    # add_to_stack also called with the value returned by prompt ("")
    mock_config_utils.assert_called_once_with("feature-branch", "")


def test_create_new_branch_with_validation(
    mock_git_utils, mock_config_utils, mock_prompt
):
    """Test branch name validation in interactive mode."""
    # Setup
    mock_git_utils["exists"].side_effect = [
        False,
        True,
    ]  # new branch doesn't exist, base does
    mock_prompt["input"].side_effect = [
        "feature/branch",
        "main",
    ]  # User inputs with validation

    # Execute
    create_new_branch()

    # Verify validator was used
    assert "validator" in mock_prompt["input"].call_args_list[0].kwargs
    mock_git_utils["create"].assert_called_once_with("feature/branch", "main")


def test_create_new_branch_with_branch_completion(
    mock_git_utils, mock_config_utils, mock_prompt
):
    """Test base branch completion in interactive mode."""
    # Setup
    mock_git_utils["exists"].side_effect = [
        False,
        True,
    ]  # new branch doesn't exist, base does
    mock_prompt["input"].side_effect = ["feature-branch", "develop"]  # User inputs

    # Execute
    create_new_branch()

    # Verify completer was used with branch list
    assert "completer" in mock_prompt["input"].call_args_list[1].kwargs
    assert mock_prompt["input"].call_args_list[1].kwargs["completer"] == [
        "main",
        "develop",
        "feature",
    ]
