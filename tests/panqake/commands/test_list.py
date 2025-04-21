"""Tests for the list command."""

from unittest.mock import call, patch

import pytest

from panqake.commands.list import (
    find_stack_root,
    list_branches,
    print_branch_tree,
)


@pytest.fixture
def mock_git_config():
    """Mock git and config functions for testing."""
    with (
        patch("panqake.commands.list.get_current_branch") as mock_get_current,
        patch("panqake.commands.list.branch_exists") as mock_branch_exists,
        patch("panqake.commands.list.get_parent_branch") as mock_get_parent,
        patch("panqake.commands.list.get_child_branches") as mock_get_children,
        patch("panqake.commands.list.print") as mock_print,
        patch("panqake.commands.list.sys.exit") as mock_exit,
    ):
        # Set default return values
        mock_get_current.return_value = "feature"
        mock_branch_exists.return_value = True
        mock_get_parent.side_effect = lambda branch: {
            "feature": "develop",
            "develop": "main",
            "main": None,
            "bugfix": "develop",
            "enhancement": "feature",
        }.get(branch)
        mock_get_children.side_effect = lambda branch: {
            "main": ["develop"],
            "develop": ["feature", "bugfix"],
            "feature": ["enhancement"],
            "bugfix": [],
            "enhancement": [],
        }.get(branch, [])

        yield {
            "get_current_branch": mock_get_current,
            "branch_exists": mock_branch_exists,
            "get_parent_branch": mock_get_parent,
            "get_child_branches": mock_get_children,
            "print": mock_print,
            "exit": mock_exit,
        }


def test_find_stack_root(mock_git_config):
    """Test finding the root of a branch stack."""
    # Test with leaf branch
    assert find_stack_root("enhancement") == "main"

    # Test with middle branch
    assert find_stack_root("feature") == "main"

    # Test with root branch
    assert find_stack_root("main") == "main"

    # Verify parent branch lookup calls
    mock_git_config["get_parent_branch"].assert_has_calls(
        [
            call("enhancement"),
            call("feature"),
            call("develop"),
            call("main"),
            call("feature"),
            call("develop"),
            call("main"),
            call("main"),
        ],
        any_order=True,
    )


def test_print_branch_tree(mock_git_config):
    """Test printing a branch tree."""
    # Test printing from the root
    print_branch_tree("main")

    # Verify the print calls (ignoring prefix differences that could be whitespace-related)
    # Just check the branch names are there in the right order
    print_calls = mock_git_config["print"].call_args_list
    assert len(print_calls) >= 5
    for i, branch in enumerate(
        ["main", "develop", "feature", "enhancement", "bugfix"]
    ):
        assert branch in print_calls[i][0][0]


def test_print_branch_tree_current_branch_marker(mock_git_config):
    """Test that the current branch is marked with an asterisk."""
    # Set current branch
    mock_git_config["get_current_branch"].return_value = "develop"

    # Print tree
    print_branch_tree("main")

    # Verify current branch has asterisk
    print_calls = mock_git_config["print"].call_args_list
    assert any("* develop" in call[0][0] for call in print_calls)
    assert not any(
        "* main" in call[0][0] for call in print_calls
    )  # Main shouldn't have asterisk


def test_list_branches_with_specified_branch(mock_git_config):
    """Test listing branches from a specified branch."""
    # Call with specific branch
    list_branches("develop")

    # Verify branch existence check
    mock_git_config["branch_exists"].assert_called_with("develop")

    # Verify root finding
    mock_git_config["get_parent_branch"].assert_any_call("develop")

    # Verify header print
    assert any(
        "Branch stack (current: feature)" in call[0][0]
        for call in mock_git_config["print"].call_args_list
    )

    # Verify tree printing
    assert mock_git_config["print"].call_count > 5


def test_list_branches_current_branch(mock_git_config):
    """Test listing branches from current branch when none specified."""
    # Call without specific branch
    list_branches()

    # Verify current branch retrieval
    mock_git_config["get_current_branch"].assert_called()

    # Verify branch existence check
    mock_git_config["branch_exists"].assert_called_with("feature")

    # Verify tree printing
    assert mock_git_config["print"].call_count > 0


def test_list_branches_nonexistent_branch(mock_git_config):
    """Test error handling when specified branch doesn't exist."""
    # Set branch to not exist
    mock_git_config["branch_exists"].return_value = False

    # Call with nonexistent branch
    list_branches("nonexistent")

    # Verify error message
    mock_git_config["print"].assert_any_call(
        "Error: Branch 'nonexistent' does not exist"
    )

    # Verify exit
    mock_git_config["exit"].assert_called_once_with(1)
