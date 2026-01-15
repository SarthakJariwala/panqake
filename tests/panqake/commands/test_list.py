"""Tests for list.py command module using fakes."""

import pytest

from panqake.commands.list import list_branches_core
from panqake.ports import BranchNotFoundError, find_stack_root
from panqake.testing.fakes import FakeConfig, FakeGit, FakeUI


class TestFindStackRoot:
    """Tests for find_stack_root helper."""

    def test_no_parent_returns_branch(self):
        """Branch with no parent is its own root."""
        config = FakeConfig()
        assert find_stack_root("feature", config) == "feature"

    def test_single_parent(self):
        """Branch with one parent returns parent as root."""
        config = FakeConfig(stack={"feature": {"parent": "main"}})
        assert find_stack_root("feature", config) == "main"

    def test_multi_level_stack(self):
        """Finds root through multiple levels."""
        config = FakeConfig(
            stack={
                "subfeature": {"parent": "feature"},
                "feature": {"parent": "main"},
            }
        )
        assert find_stack_root("subfeature", config) == "main"


class TestListBranchesCore:
    """Tests for list_branches_core function."""

    def test_no_current_branch_raises(self):
        """Raises BranchNotFoundError when current branch cannot be determined."""
        git = FakeGit(current_branch=None)
        config = FakeConfig()
        ui = FakeUI(strict=False)

        with pytest.raises(BranchNotFoundError, match="Could not determine"):
            list_branches_core(git, config, ui)

    def test_nonexistent_branch_raises(self):
        """Raises BranchNotFoundError for nonexistent branch."""
        git = FakeGit(branches=["main"], current_branch="main")
        config = FakeConfig()
        ui = FakeUI(strict=False)

        with pytest.raises(BranchNotFoundError, match="does not exist"):
            list_branches_core(git, config, ui, branch_name="nonexistent")

    def test_current_branch_used_when_none_specified(self):
        """Uses current branch when no branch specified."""
        git = FakeGit(branches=["main", "feature"], current_branch="feature")
        config = FakeConfig()
        ui = FakeUI(strict=False)

        result = list_branches_core(git, config, ui)

        assert result.target_branch == "feature"
        assert result.current_branch == "feature"
        assert result.root_branch == "feature"

    def test_specific_branch_used(self):
        """Uses specified branch as target."""
        git = FakeGit(branches=["main", "feature"], current_branch="main")
        config = FakeConfig()
        ui = FakeUI(strict=False)

        result = list_branches_core(git, config, ui, branch_name="feature")

        assert result.target_branch == "feature"
        assert result.current_branch == "main"
        assert result.root_branch == "feature"

    def test_finds_stack_root(self):
        """Finds root through parent chain."""
        git = FakeGit(
            branches=["main", "feature", "subfeature"], current_branch="subfeature"
        )
        config = FakeConfig(
            stack={
                "subfeature": {"parent": "feature"},
                "feature": {"parent": "main"},
            }
        )
        ui = FakeUI(strict=False)

        result = list_branches_core(git, config, ui)

        assert result.target_branch == "subfeature"
        assert result.current_branch == "subfeature"
        assert result.root_branch == "main"

    def test_displays_branch_tree(self):
        """Calls display_branch_tree with correct arguments."""
        git = FakeGit(branches=["main", "feature"], current_branch="feature")
        config = FakeConfig(stack={"feature": {"parent": "main"}})
        ui = FakeUI(strict=False)

        list_branches_core(git, config, ui)

        assert len(ui.display_tree_calls) == 1
        root, current = ui.display_tree_calls[0]
        assert root == "main"
        assert current == "feature"

    def test_displays_tree_for_specific_branch(self):
        """Displays tree from specified branch's root."""
        git = FakeGit(branches=["main", "feature", "other"], current_branch="other")
        config = FakeConfig(stack={"feature": {"parent": "main"}})
        ui = FakeUI(strict=False)

        list_branches_core(git, config, ui, branch_name="feature")

        assert len(ui.display_tree_calls) == 1
        root, current = ui.display_tree_calls[0]
        assert root == "main"
        assert current == "other"  # Current branch passed for highlighting
