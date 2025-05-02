"""Tests for list.py command module."""

from unittest.mock import patch

import pytest

from panqake.commands.list import find_stack_root, list_branches, print_branch_tree


@pytest.fixture
def mock_git_utils():
    """Mock git utility functions."""
    with (
        patch("panqake.commands.list.branch_exists") as mock_exists,
        patch("panqake.commands.list.get_current_branch") as mock_current,
    ):
        mock_current.return_value = "main"
        yield {
            "exists": mock_exists,
            "current": mock_current,
        }


@pytest.fixture
def mock_config_utils():
    """Mock config utility functions."""
    with (
        patch("panqake.commands.list.get_parent_branch") as mock_parent,
        patch("panqake.commands.list.get_child_branches") as mock_children,
    ):
        yield {
            "parent": mock_parent,
            "children": mock_children,
        }


@pytest.fixture
def mock_prompt():
    """Mock questionary prompt functions."""
    with (
        patch("panqake.commands.list.format_branch") as mock_format,
        patch("panqake.commands.list.print_formatted_text") as mock_print,
    ):
        mock_format.side_effect = (
            lambda branch, current=False: f"[formatted]{branch}[/formatted]"
        )
        yield {
            "format": mock_format,
            "print": mock_print,
        }


def test_find_stack_root_no_parent(mock_config_utils):
    """Test finding root when branch has no parent."""
    mock_config_utils["parent"].return_value = ""
    assert find_stack_root("feature") == "feature"


def test_find_stack_root_with_parent(mock_config_utils):
    """Test finding root with multiple levels of parents."""
    # Setup parent chain: feature -> develop -> main
    mock_config_utils["parent"].side_effect = ["develop", "main", ""]
    assert find_stack_root("feature") == "main"


def test_print_branch_tree_single_branch(
    mock_git_utils, mock_config_utils, mock_prompt
):
    """Test printing tree with a single branch."""
    mock_config_utils["children"].return_value = []

    print_branch_tree("main")

    mock_prompt["print"].assert_called_once_with("[formatted]main[/formatted]")


def test_print_branch_tree_with_children(
    mock_git_utils, mock_config_utils, mock_prompt
):
    """Test printing tree with children branches."""
    # Setup a tree: main -> [feature1, feature2]
    mock_config_utils["children"].side_effect = [
        ["feature1", "feature2"],  # main's children
        [],  # feature1's children
        [],  # feature2's children
    ]

    print_branch_tree("main")

    # Verify the output structure
    calls = mock_prompt["print"].call_args_list
    assert len(calls) == 3
    assert calls[0].args[0] == "[formatted]main[/formatted]"
    assert calls[1].args[0] == "    ├── [formatted]feature1[/formatted]"
    assert calls[2].args[0] == "    └── [formatted]feature2[/formatted]"


def test_print_branch_tree_nested(mock_git_utils, mock_config_utils, mock_prompt):
    """Test printing tree with nested branches."""
    # Setup a tree: main -> feature1 -> subfeature
    mock_config_utils["children"].side_effect = [
        ["feature1"],  # main's children
        ["subfeature"],  # feature1's children
        [],  # subfeature's children
    ]

    print_branch_tree("main")

    # Verify the output structure
    calls = mock_prompt["print"].call_args_list
    assert len(calls) == 3
    assert calls[0].args[0] == "[formatted]main[/formatted]"
    assert calls[1].args[0] == "    └── [formatted]feature1[/formatted]"
    assert calls[2].args[0] == "        └── [formatted]subfeature[/formatted]"


def test_list_branches_nonexistent_branch(
    mock_git_utils, mock_config_utils, mock_prompt
):
    """Test listing branches with nonexistent branch."""
    mock_git_utils["exists"].return_value = False

    with pytest.raises(SystemExit):
        list_branches("nonexistent")

    mock_prompt["print"].assert_called_once()
    assert "Error" in mock_prompt["print"].call_args.args[0]


def test_list_branches_current_branch(mock_git_utils, mock_config_utils, mock_prompt):
    """Test listing branches from current branch."""
    mock_git_utils["exists"].return_value = True
    mock_config_utils["parent"].return_value = ""
    mock_config_utils["children"].return_value = []

    list_branches()

    # Should use current branch (called multiple times: for header and in print_branch_tree)
    assert mock_git_utils["current"].call_count >= 1
    # Should print header and tree
    assert mock_prompt["print"].call_count == 2


def test_list_branches_specific_branch(mock_git_utils, mock_config_utils, mock_prompt):
    """Test listing branches from specified branch."""
    mock_git_utils["exists"].return_value = True
    mock_config_utils["parent"].return_value = ""
    mock_config_utils["children"].return_value = []

    list_branches("feature")

    # Current branch is still called for header and in print_branch_tree
    assert mock_git_utils["current"].call_count >= 1
    # Should print header and tree
    assert mock_prompt["print"].call_count == 2


def test_list_branches_with_stack(mock_git_utils, mock_config_utils, mock_prompt):
    """Test listing a complete branch stack."""
    mock_git_utils["exists"].return_value = True
    # Setup stack: main -> feature -> subfeature
    mock_config_utils["parent"].side_effect = [
        "main",
        "",
        None,
    ]  # feature -> main -> None
    mock_config_utils["children"].side_effect = [
        ["feature"],  # main's children
        ["subfeature"],  # feature's children
        [],  # subfeature's children
    ]

    list_branches("subfeature")

    # Should find root and print complete tree
    assert mock_prompt["print"].call_count == 4  # Header + 3 branches
