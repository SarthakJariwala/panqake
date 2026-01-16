"""Tests for update command using dependency injection with fakes.

No mocking - tests use FakeGit, FakeConfig, FakeUI to verify behavior and state.
"""

import pytest

from panqake.commands.update import (
    UpdateResult,
    get_affected_branches_core,
    push_updated_branches_core,
    return_to_branch_core,
    update_all_branches_core,
    update_branch_with_conflict_detection_core,
    update_core,
)
from panqake.ports import BranchNotFoundError, UserCancelledError
from panqake.testing.fakes import FakeConfig, FakeGit, FakeUI


class TestGetAffectedBranchesCore:
    """Tests for get_affected_branches_core function."""

    def test_returns_empty_list_when_no_children(self):
        config = FakeConfig(stack={"main": {"parent": None}})

        result = get_affected_branches_core(config, "main")

        assert result == []

    def test_returns_direct_children(self):
        config = FakeConfig(
            stack={
                "main": {"parent": None},
                "feature-1": {"parent": "main"},
                "feature-2": {"parent": "main"},
            }
        )

        result = get_affected_branches_core(config, "main")

        assert set(result) == {"feature-1", "feature-2"}

    def test_returns_all_descendants_depth_first(self):
        config = FakeConfig(
            stack={
                "main": {"parent": None},
                "feature-1": {"parent": "main"},
                "feature-1a": {"parent": "feature-1"},
                "feature-1b": {"parent": "feature-1"},
                "feature-2": {"parent": "main"},
            }
        )

        result = get_affected_branches_core(config, "main")

        # All descendants should be present
        assert set(result) == {"feature-1", "feature-1a", "feature-1b", "feature-2"}


class TestUpdateBranchWithConflictDetectionCore:
    """Tests for update_branch_with_conflict_detection_core function."""

    def test_successful_rebase_returns_true(self):
        git = FakeGit(branches=["main", "feature-1"])

        success, error = update_branch_with_conflict_detection_core(
            git, "feature-1", "main"
        )

        assert success is True
        assert error is None
        assert ("feature-1", "main") in git.rebase_calls

    def test_rebase_conflict_returns_false_with_error(self):
        git = FakeGit(branches=["main", "feature-1"])
        git.fail_rebase = True

        success, error = update_branch_with_conflict_detection_core(
            git, "feature-1", "main"
        )

        assert success is False
        assert error is not None
        assert "conflict" in error.lower()

    def test_worktree_branch_uses_worktree_rebase(self):
        git = FakeGit(branches=["main", "feature-1"])
        git.worktrees["feature-1"] = "/path/to/worktree"

        success, error = update_branch_with_conflict_detection_core(
            git, "feature-1", "main"
        )

        assert success is True
        assert error is None


class TestUpdateAllBranchesCore:
    """Tests for update_all_branches_core function."""

    def test_updates_all_children_in_order(self):
        git = FakeGit(branches=["main", "feature-1", "feature-2"])
        config = FakeConfig(
            stack={
                "main": {"parent": None},
                "feature-1": {"parent": "main"},
                "feature-2": {"parent": "main"},
            }
        )
        ui = FakeUI(strict=False)

        updated, conflicts = update_all_branches_core(git, config, ui, "main")

        assert set(updated) == {"feature-1", "feature-2"}
        assert conflicts == []
        assert len(ui.success_messages) == 2

    def test_skips_children_of_conflicted_branches(self):
        git = FakeGit(branches=["main", "feature-1", "feature-1a"])
        config = FakeConfig(
            stack={
                "main": {"parent": None},
                "feature-1": {"parent": "main"},
                "feature-1a": {"parent": "feature-1"},
            }
        )
        ui = FakeUI(strict=False)
        git.fail_rebase = True

        updated, conflicts = update_all_branches_core(git, config, ui, "main")

        assert updated == []
        # Both branches should be in conflicts - parent failed and child skipped
        assert set(conflicts) == {"feature-1", "feature-1a"}

    def test_reports_errors_for_conflicts(self):
        git = FakeGit(branches=["main", "feature-1"])
        config = FakeConfig(
            stack={
                "main": {"parent": None},
                "feature-1": {"parent": "main"},
            }
        )
        ui = FakeUI(strict=False)
        git.fail_rebase = True

        update_all_branches_core(git, config, ui, "main")

        assert len(ui.error_messages) >= 1


class TestPushUpdatedBranchesCore:
    """Tests for push_updated_branches_core function."""

    def test_pushes_branches_with_unpushed_changes(self):
        git = FakeGit(
            branches=["main", "feature-1"],
            pushed_branches={"feature-1"},
            unpushed_changes={"feature-1": True},
        )
        ui = FakeUI(strict=False)

        pushed, skipped = push_updated_branches_core(git, ui, ["feature-1"])

        assert pushed == ["feature-1"]
        assert skipped == []
        assert len(git.push_calls) == 1

    def test_skips_branches_not_on_remote(self):
        git = FakeGit(branches=["main", "feature-1"])
        ui = FakeUI(strict=False)

        pushed, skipped = push_updated_branches_core(git, ui, ["feature-1"])

        assert pushed == []
        assert skipped == ["feature-1"]
        assert len(git.push_calls) == 0

    def test_skips_branches_already_in_sync(self):
        git = FakeGit(
            branches=["main", "feature-1"],
            pushed_branches={"feature-1"},
            unpushed_changes={"feature-1": False},
        )
        ui = FakeUI(strict=False)

        pushed, skipped = push_updated_branches_core(git, ui, ["feature-1"])

        assert pushed == []
        assert skipped == ["feature-1"]

    def test_skips_worktree_branches(self):
        git = FakeGit(
            branches=["main", "feature-1"],
            pushed_branches={"feature-1"},
            unpushed_changes={"feature-1": True},
        )
        git.worktrees["feature-1"] = "/path/to/worktree"
        ui = FakeUI(strict=False)

        pushed, skipped = push_updated_branches_core(git, ui, ["feature-1"])

        assert pushed == []
        assert skipped == ["feature-1"]

    def test_empty_list_returns_empty(self):
        git = FakeGit()
        ui = FakeUI(strict=False)

        pushed, skipped = push_updated_branches_core(git, ui, [])

        assert pushed == []
        assert skipped == []


class TestReturnToBranchCore:
    """Tests for return_to_branch_core function."""

    def test_returns_to_existing_branch(self):
        git = FakeGit(branches=["main", "feature-1"], current_branch="main")
        ui = FakeUI(strict=False)

        result = return_to_branch_core(git, ui, "feature-1")

        assert result == "feature-1"
        assert git.current_branch == "feature-1"

    def test_returns_none_for_nonexistent_branch(self):
        git = FakeGit(branches=["main"], current_branch="main")
        ui = FakeUI(strict=False)

        result = return_to_branch_core(git, ui, "feature-1")

        assert result is None
        assert len(ui.error_messages) == 1


class TestUpdateCore:
    """Tests for the main update_core function."""

    def test_returns_early_when_no_children(self):
        git = FakeGit(branches=["main", "feature-1"], current_branch="feature-1")
        config = FakeConfig(stack={"feature-1": {"parent": "main"}})
        ui = FakeUI(strict=False)

        result = update_core(git, config, ui, branch_name="feature-1")

        assert isinstance(result, UpdateResult)
        assert result.affected_branches == []
        assert result.updated_branches == []
        assert len(ui.info_messages) >= 1

    def test_uses_current_branch_when_none_specified(self):
        git = FakeGit(branches=["main", "feature-1"], current_branch="feature-1")
        config = FakeConfig(stack={"feature-1": {"parent": "main"}})
        ui = FakeUI(strict=False)

        result = update_core(git, config, ui, branch_name=None)

        assert result.starting_branch == "feature-1"

    def test_raises_when_current_branch_unknown(self):
        git = FakeGit(branches=["main"], current_branch=None)
        config = FakeConfig()
        ui = FakeUI(strict=False)

        with pytest.raises(BranchNotFoundError):
            update_core(git, config, ui)

    def test_raises_when_branch_not_found(self):
        git = FakeGit(branches=["main"], current_branch="main")
        config = FakeConfig()
        ui = FakeUI(strict=False)

        with pytest.raises(BranchNotFoundError):
            update_core(git, config, ui, branch_name="nonexistent")

    def test_returns_cancelled_result_when_user_declines(self):
        git = FakeGit(
            branches=["main", "feature-1", "feature-2"], current_branch="feature-1"
        )
        config = FakeConfig(
            stack={
                "feature-1": {"parent": "main"},
                "feature-2": {"parent": "feature-1"},
            }
        )
        ui = FakeUI(confirm_responses=[False], strict=False)

        result = update_core(git, config, ui, branch_name="feature-1")

        assert result.updated_branches == []
        assert result.affected_branches == ["feature-2"]

    def test_raises_on_user_cancel(self):
        git = FakeGit(
            branches=["main", "feature-1", "feature-2"], current_branch="feature-1"
        )
        config = FakeConfig(
            stack={
                "feature-1": {"parent": "main"},
                "feature-2": {"parent": "feature-1"},
            }
        )
        ui = FakeUI(cancel_on_confirm=True, strict=False)

        with pytest.raises(UserCancelledError):
            update_core(git, config, ui, branch_name="feature-1")

    def test_full_update_success(self):
        git = FakeGit(
            branches=["main", "feature-1", "feature-2"],
            current_branch="feature-1",
            pushed_branches={"feature-2"},
            unpushed_changes={"feature-2": True},
        )
        config = FakeConfig(
            stack={
                "main": {"parent": None},
                "feature-1": {"parent": "main"},
                "feature-2": {"parent": "feature-1"},
            }
        )
        ui = FakeUI(confirm_responses=[True], strict=False)

        result = update_core(git, config, ui, branch_name="feature-1")

        assert result.starting_branch == "feature-1"
        assert result.updated_branches == ["feature-2"]
        assert result.conflict_branches == []
        assert result.pushed_branches == ["feature-2"]
        assert result.returned_to == "feature-1"

    def test_skip_push_flag(self):
        git = FakeGit(
            branches=["main", "feature-1", "feature-2"],
            current_branch="feature-1",
            pushed_branches={"feature-2"},
            unpushed_changes={"feature-2": True},
        )
        config = FakeConfig(
            stack={
                "main": {"parent": None},
                "feature-1": {"parent": "main"},
                "feature-2": {"parent": "feature-1"},
            }
        )
        ui = FakeUI(confirm_responses=[True], strict=False)

        result = update_core(git, config, ui, branch_name="feature-1", skip_push=True)

        assert result.updated_branches == ["feature-2"]
        assert result.pushed_branches == []
        assert result.skip_push is True
        # Verify "local only" message
        assert any("local only" in msg.lower() for msg in ui.success_messages)

    def test_reports_conflicts(self):
        git = FakeGit(
            branches=["main", "feature-1", "feature-2"], current_branch="feature-1"
        )
        git.fail_rebase = True
        config = FakeConfig(
            stack={
                "main": {"parent": None},
                "feature-1": {"parent": "main"},
                "feature-2": {"parent": "feature-1"},
            }
        )
        ui = FakeUI(confirm_responses=[True], strict=False)

        result = update_core(git, config, ui, branch_name="feature-1")

        assert result.updated_branches == []
        assert result.conflict_branches == ["feature-2"]
        assert len(ui.error_messages) >= 1

    def test_returns_to_original_branch(self):
        git = FakeGit(
            branches=["main", "feature-1", "feature-2"], current_branch="feature-1"
        )
        config = FakeConfig(
            stack={
                "main": {"parent": None},
                "feature-1": {"parent": "main"},
                "feature-2": {"parent": "feature-1"},
            }
        )
        ui = FakeUI(confirm_responses=[True], strict=False)

        result = update_core(git, config, ui, branch_name="feature-1")

        assert result.original_branch == "feature-1"
        assert result.returned_to == "feature-1"
        assert git.current_branch == "feature-1"
