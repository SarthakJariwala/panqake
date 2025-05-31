"""Tests for list.py command module."""

from unittest.mock import MagicMock, patch

import pytest

from panqake.commands.list import find_stack_root, list_branches


@pytest.fixture
def mock_git_utils():
    """Mock git utility functions."""
    with (
        patch("panqake.commands.list.validate_branch") as mock_validate,
        patch("panqake.commands.list.get_current_branch") as mock_current,
    ):
        mock_current.return_value = "main"
        mock_validate.side_effect = lambda x: x if x else "main"
        yield {
            "validate": mock_validate,
            "current": mock_current,
        }


@pytest.fixture
def mock_config_utils():
    """Mock config utility functions."""
    with (
        patch("panqake.commands.list.get_parent_branch") as mock_parent,
    ):
        yield {
            "parent": mock_parent,
        }


@pytest.fixture
def mock_prompt():
    """Mock questionary prompt functions."""
    with (
        patch("panqake.commands.list.print_formatted_text") as mock_print,
    ):
        yield {
            "print": mock_print,
        }


@pytest.fixture
def mock_stacks():
    """Mock the Stacks class."""
    with patch("panqake.commands.list.Stacks") as mock_stacks_class:
        mock_stacks_instance = MagicMock()
        mock_stacks_class.return_value = mock_stacks_instance
        mock_stacks_instance.visualize_tree.return_value = "mock tree output"
        yield mock_stacks_instance


def test_find_stack_root_no_parent(mock_config_utils):
    """Test finding root when branch has no parent."""
    mock_config_utils["parent"].return_value = ""
    assert find_stack_root("feature") == "feature"


def test_find_stack_root_with_parent(mock_config_utils):
    """Test finding root with multiple levels of parents."""
    # Setup parent chain: feature -> develop -> main
    mock_config_utils["parent"].side_effect = ["develop", "main", ""]
    assert find_stack_root("feature") == "main"


def test_list_branches_nonexistent_branch(
    mock_git_utils, mock_config_utils, mock_prompt, mock_stacks
):
    """Test listing branches with nonexistent branch."""
    mock_git_utils["validate"].side_effect = SystemExit(1)

    with pytest.raises(SystemExit):
        list_branches("nonexistent")

    mock_git_utils["validate"].assert_called_once_with("nonexistent")
    # Stacks instance should not be created
    mock_stacks.visualize_tree.assert_not_called()


def test_list_branches_current_branch(
    mock_git_utils, mock_config_utils, mock_prompt, mock_stacks
):
    """Test listing branches from current branch."""
    mock_config_utils["parent"].return_value = ""

    list_branches()

    # Should validate with None (current branch)
    mock_git_utils["validate"].assert_called_once_with(None)
    # Should use current branch (called for header and passed to visualize_tree)
    assert mock_git_utils["current"].call_count >= 1
    # Should call visualize_tree once
    mock_stacks.visualize_tree.assert_called_once()
    # Should print header and tree
    assert mock_prompt["print"].call_count == 2


def test_list_branches_specific_branch(
    mock_git_utils, mock_config_utils, mock_prompt, mock_stacks
):
    """Test listing branches from specified branch."""
    mock_config_utils["parent"].return_value = ""

    list_branches("feature")

    # Should validate the specific branch
    mock_git_utils["validate"].assert_called_once_with("feature")

    # Current branch is still called for header
    assert mock_git_utils["current"].call_count >= 1
    # Should call visualize_tree with specified branch as root
    mock_stacks.visualize_tree.assert_called_once()
    assert mock_stacks.visualize_tree.call_args.kwargs["root"] == "feature"
    # Should print header and tree
    assert mock_prompt["print"].call_count == 2


def test_list_branches_with_stack(
    mock_git_utils, mock_config_utils, mock_prompt, mock_stacks
):
    """Test listing a complete branch stack."""
    # Setup stack: main -> feature -> subfeature
    mock_config_utils["parent"].side_effect = [
        "main",
        "",
        None,
    ]  # feature -> main -> None

    list_branches("subfeature")

    # Should find root (main) and use it as root for visualize_tree
    mock_stacks.visualize_tree.assert_called_once()
    assert mock_stacks.visualize_tree.call_args.kwargs["root"] == "main"
    # Should print header and tree
    assert mock_prompt["print"].call_count == 2
