"""Tests for switch.py command module using dependency injection pattern."""

import pytest

from panqake.commands.switch import find_stack_root, switch_branch_core
from panqake.ports import BranchNotFoundError, UserCancelledError
from panqake.testing.fakes import FakeConfig, FakeGit, FakeUI


class TestFindStackRoot:
    """Tests for find_stack_root helper."""

    def test_branch_without_parent_is_root(self):
        config = FakeConfig(stack={"feature": {"parent": "main"}})
        assert find_stack_root("main", config) == "main"

    def test_finds_root_through_chain(self):
        config = FakeConfig(
            stack={
                "feature": {"parent": "main"},
                "child": {"parent": "feature"},
                "grandchild": {"parent": "child"},
            }
        )
        assert find_stack_root("grandchild", config) == "main"


class TestSwitchBranchCore:
    """Tests for switch_branch_core."""

    def test_raises_when_no_branches(self):
        git = FakeGit(branches=[])
        config = FakeConfig()
        ui = FakeUI(strict=False)

        with pytest.raises(BranchNotFoundError, match="No branches found"):
            switch_branch_core(git=git, config=config, ui=ui)

    def test_raises_when_branch_not_exists(self):
        git = FakeGit(branches=["main", "develop"])
        config = FakeConfig()
        ui = FakeUI(strict=False)

        with pytest.raises(BranchNotFoundError, match="does not exist"):
            switch_branch_core(git=git, config=config, ui=ui, branch_name="nonexistent")

    def test_already_on_branch(self):
        git = FakeGit(branches=["main", "feature"], current_branch="feature")
        config = FakeConfig()
        ui = FakeUI(strict=False)

        result = switch_branch_core(
            git=git, config=config, ui=ui, branch_name="feature"
        )

        assert result.target_branch == "feature"
        assert result.switched is False
        assert any("Already on branch" in msg for msg in ui.info_messages)

    def test_switch_to_explicit_branch(self):
        git = FakeGit(branches=["main", "feature"], current_branch="main")
        config = FakeConfig()
        ui = FakeUI(strict=False)

        result = switch_branch_core(
            git=git, config=config, ui=ui, branch_name="feature"
        )

        assert result.target_branch == "feature"
        assert result.previous_branch == "main"
        assert result.switched is True
        assert git.current_branch == "feature"
        assert "feature" in git.checkout_calls

    def test_worktree_branch_not_checked_out(self):
        git = FakeGit(branches=["main", "feature"], current_branch="main")
        git.worktrees["feature"] = "/path/to/worktree"
        config = FakeConfig()
        ui = FakeUI(strict=False)

        result = switch_branch_core(
            git=git, config=config, ui=ui, branch_name="feature"
        )

        assert result.switched is False
        assert result.worktree_path == "/path/to/worktree"
        assert "feature" not in git.checkout_calls
        assert any("/path/to/worktree" in msg for msg in ui.info_messages)

    def test_interactive_selection(self):
        git = FakeGit(branches=["main", "feature", "develop"], current_branch="main")
        config = FakeConfig(stack={"feature": {"parent": "main"}})
        ui = FakeUI(select_branch_responses=["develop"])

        result = switch_branch_core(git=git, config=config, ui=ui, show_tree=False)

        assert result.target_branch == "develop"
        assert result.switched is True
        assert git.current_branch == "develop"

    def test_interactive_shows_tree(self):
        git = FakeGit(branches=["main", "feature"], current_branch="main")
        config = FakeConfig(stack={"feature": {"parent": "main"}})
        ui = FakeUI(select_branch_responses=["feature"])

        switch_branch_core(git=git, config=config, ui=ui, show_tree=True)

        assert len(ui.display_tree_calls) == 2  # Before and after selection

    def test_interactive_worktree_not_checked_out(self):
        git = FakeGit(branches=["main", "feature"], current_branch="main")
        git.worktrees["feature"] = "/worktree/path"
        config = FakeConfig()
        ui = FakeUI(select_branch_responses=["feature"])

        result = switch_branch_core(git=git, config=config, ui=ui, show_tree=False)

        assert result.switched is False
        assert result.worktree_path == "/worktree/path"

    def test_no_selection_available(self):
        git = FakeGit(branches=["main"], current_branch="main")
        config = FakeConfig()
        ui = FakeUI(select_branch_responses=[None], strict=False)

        with pytest.raises(BranchNotFoundError, match="No branches available"):
            switch_branch_core(git=git, config=config, ui=ui, show_tree=False)


class TestUserCancellation:
    """Tests for user cancellation handling."""

    def test_cancel_on_branch_selection(self):
        git = FakeGit(branches=["main", "feature"], current_branch="main")
        config = FakeConfig()
        ui = FakeUI(cancel_on_select_branch=True)

        with pytest.raises(UserCancelledError):
            switch_branch_core(git=git, config=config, ui=ui, show_tree=False)

        assert git.current_branch == "main"  # State unchanged
