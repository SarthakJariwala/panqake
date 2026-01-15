"""Tests for sync.py command module using fakes."""

import pytest

from panqake.commands.sync import (
    fetch_and_pull_main_core,
    get_mergeable_branches_core,
    handle_merged_branches_core,
    push_updated_branches_core,
    return_to_branch_core,
    sync_core,
    update_all_branches_core,
    update_branch_with_conflict_detection_core,
)
from panqake.ports import (
    BranchNotFoundError,
    GitOperationError,
    UserCancelledError,
)
from panqake.testing.fakes import FakeConfig, FakeGit, FakeUI


class TestFetchAndPullMainCore:
    """Tests for fetch_and_pull_main_core."""

    def test_fetches_and_pulls_main(self):
        git = FakeGit(branches=["main", "feature"], current_branch="feature")
        git._commit_hashes["main"] = "abc123def456"
        ui = FakeUI(strict=False)

        result = fetch_and_pull_main_core(git, ui, "main")

        assert result == "abc123def456"
        assert git.fetch_calls == 1
        assert "main" in git.pull_calls
        assert git.current_branch == "main"
        assert any("fast-forwarded" in msg for msg in ui.success_messages)

    def test_raises_on_fetch_failure(self):
        git = FakeGit(branches=["main"])
        git.fail_fetch = True
        ui = FakeUI(strict=False)

        with pytest.raises(GitOperationError, match="fetch"):
            fetch_and_pull_main_core(git, ui, "main")

    def test_raises_on_pull_failure(self):
        git = FakeGit(branches=["main"])
        git.fail_pull = True
        ui = FakeUI(strict=False)

        with pytest.raises(GitOperationError, match="pull"):
            fetch_and_pull_main_core(git, ui, "main")


class TestGetMergeableBranchesCore:
    """Tests for get_mergeable_branches_core."""

    def test_returns_branches_with_main_parent(self):
        git = FakeGit(
            branches=["main", "feature1", "feature2"],
            merged_branches={"main": ["feature1", "feature2"]},
        )
        config = FakeConfig(
            stack={
                "feature1": {"parent": "main"},
                "feature2": {"parent": "main"},
            }
        )

        result = get_mergeable_branches_core(git, config, "main")

        assert set(result) == {"feature1", "feature2"}

    def test_excludes_branches_with_non_main_parent(self):
        git = FakeGit(
            branches=["main", "feature1", "feature2"],
            merged_branches={"main": ["feature1", "feature2"]},
        )
        config = FakeConfig(
            stack={
                "feature1": {"parent": "main"},
                "feature2": {"parent": "feature1"},
            }
        )

        result = get_mergeable_branches_core(git, config, "main")

        assert result == ["feature1"]

    def test_returns_empty_when_no_merged_branches(self):
        git = FakeGit(branches=["main"])
        config = FakeConfig()

        result = get_mergeable_branches_core(git, config, "main")

        assert result == []


class TestHandleMergedBranchesCore:
    """Tests for handle_merged_branches_core."""

    def test_deletes_confirmed_branches(self):
        git = FakeGit(
            branches=["main", "feature1", "feature2"],
            merged_branches={"main": ["feature1", "feature2"]},
        )
        config = FakeConfig(
            stack={
                "feature1": {"parent": "main"},
                "feature2": {"parent": "main"},
            }
        )
        ui = FakeUI(confirm_responses=[True, True])

        result = handle_merged_branches_core(git, config, ui, "main")

        assert set(result) == {"feature1", "feature2"}
        assert "feature1" not in git.branches
        assert "feature2" not in git.branches
        assert "feature1" in git.deleted_local_branches
        assert "feature2" in git.deleted_local_branches
        assert "feature1" not in config.stack
        assert "feature2" not in config.stack

    def test_skips_declined_branches(self):
        git = FakeGit(
            branches=["main", "feature1", "feature2"],
            merged_branches={"main": ["feature1", "feature2"]},
        )
        config = FakeConfig(
            stack={
                "feature1": {"parent": "main"},
                "feature2": {"parent": "main"},
            }
        )
        ui = FakeUI(confirm_responses=[True, False])

        result = handle_merged_branches_core(git, config, ui, "main")

        assert result == ["feature1"]
        assert "feature1" not in git.branches
        assert "feature2" in git.branches

    def test_raises_on_cancellation(self):
        git = FakeGit(
            branches=["main", "feature1"],
            merged_branches={"main": ["feature1"]},
        )
        config = FakeConfig(stack={"feature1": {"parent": "main"}})
        ui = FakeUI(cancel_on_confirm=True)

        with pytest.raises(UserCancelledError):
            handle_merged_branches_core(git, config, ui, "main")


class TestUpdateBranchWithConflictDetectionCore:
    """Tests for update_branch_with_conflict_detection_core."""

    def test_successful_rebase_regular_branch(self):
        git = FakeGit(branches=["main", "feature"])

        success, error = update_branch_with_conflict_detection_core(
            git, "feature", "main"
        )

        assert success is True
        assert error is None
        assert ("feature", "main") in git.rebase_calls

    def test_successful_rebase_worktree_branch(self):
        git = FakeGit(branches=["main", "feature"])
        git.worktrees["feature"] = "/path/to/worktree"

        success, error = update_branch_with_conflict_detection_core(
            git, "feature", "main"
        )

        assert success is True
        assert error is None
        assert ("feature", "main") in git.rebase_calls

    def test_conflict_returns_error(self):
        git = FakeGit(branches=["main", "feature"])
        git.fail_rebase = True

        success, error = update_branch_with_conflict_detection_core(
            git, "feature", "main"
        )

        assert success is False
        assert error is not None
        assert "conflict" in error.lower()


class TestUpdateAllBranchesCore:
    """Tests for update_all_branches_core."""

    def test_updates_all_children_successfully(self):
        git = FakeGit(branches=["main", "feature1", "feature2"])
        config = FakeConfig(
            stack={
                "feature1": {"parent": "main"},
                "feature2": {"parent": "main"},
            }
        )
        ui = FakeUI(strict=False)

        updated, conflicts = update_all_branches_core(git, config, ui, "main")

        assert set(updated) == {"feature1", "feature2"}
        assert conflicts == []

    def test_updates_nested_children(self):
        git = FakeGit(branches=["main", "feature1", "feature2"])
        config = FakeConfig(
            stack={
                "feature1": {"parent": "main"},
                "feature2": {"parent": "feature1"},
            }
        )
        ui = FakeUI(strict=False)

        updated, conflicts = update_all_branches_core(git, config, ui, "main")

        assert updated == ["feature1", "feature2"]
        assert conflicts == []

    def test_skips_children_of_conflicting_parent(self):
        git = FakeGit(branches=["main", "feature1", "feature2"])
        git.fail_rebase = True
        config = FakeConfig(
            stack={
                "feature1": {"parent": "main"},
                "feature2": {"parent": "feature1"},
            }
        )
        ui = FakeUI(strict=False)

        updated, conflicts = update_all_branches_core(git, config, ui, "main")

        assert updated == []
        assert set(conflicts) == {"feature1", "feature2"}

    def test_no_children_returns_empty(self):
        git = FakeGit(branches=["main"])
        config = FakeConfig()
        ui = FakeUI(strict=False)

        updated, conflicts = update_all_branches_core(git, config, ui, "main")

        assert updated == []
        assert conflicts == []


class TestPushUpdatedBranchesCore:
    """Tests for push_updated_branches_core."""

    def test_pushes_branches_with_unpushed_changes(self):
        git = FakeGit(
            branches=["main", "feature"],
            pushed_branches={"feature"},
            unpushed_changes={"feature": True},
        )
        ui = FakeUI(strict=False)

        pushed, skipped = push_updated_branches_core(git, ui, ["feature"])

        assert pushed == ["feature"]
        assert skipped == []
        assert ("feature", True) in git.push_calls

    def test_skips_branches_not_on_remote(self):
        git = FakeGit(branches=["main", "feature"])
        ui = FakeUI(strict=False)

        pushed, skipped = push_updated_branches_core(git, ui, ["feature"])

        assert pushed == []
        assert skipped == ["feature"]
        assert git.push_calls == []

    def test_skips_branches_already_in_sync(self):
        git = FakeGit(
            branches=["main", "feature"],
            pushed_branches={"feature"},
            unpushed_changes={"feature": False},
        )
        ui = FakeUI(strict=False)

        pushed, skipped = push_updated_branches_core(git, ui, ["feature"])

        assert pushed == []
        assert skipped == ["feature"]

    def test_skips_worktree_branches(self):
        git = FakeGit(
            branches=["main", "feature"],
            pushed_branches={"feature"},
            unpushed_changes={"feature": True},
        )
        git.worktrees["feature"] = "/path/to/worktree"
        ui = FakeUI(strict=False)

        pushed, skipped = push_updated_branches_core(git, ui, ["feature"])

        assert pushed == []
        assert skipped == ["feature"]

    def test_returns_empty_for_empty_input(self):
        git = FakeGit()
        ui = FakeUI(strict=False)

        pushed, skipped = push_updated_branches_core(git, ui, [])

        assert pushed == []
        assert skipped == []


class TestReturnToBranchCore:
    """Tests for return_to_branch_core."""

    def test_returns_to_target_branch(self):
        git = FakeGit(branches=["main", "feature"], current_branch="main")
        ui = FakeUI(strict=False)

        result = return_to_branch_core(git, ui, "feature", "main", [])

        assert result == "feature"
        assert git.current_branch == "feature"

    def test_returns_to_fallback_if_target_deleted(self):
        git = FakeGit(branches=["main"], current_branch="main")
        ui = FakeUI(strict=False)

        result = return_to_branch_core(git, ui, "feature", "main", ["feature"])

        assert result == "main"
        assert git.current_branch == "main"

    def test_returns_to_fallback_if_target_doesnt_exist(self):
        git = FakeGit(branches=["main"], current_branch="main")
        ui = FakeUI(strict=False)

        result = return_to_branch_core(git, ui, "feature", "main", [])

        assert result == "main"
        assert any("no longer exists" in msg for msg in ui.info_messages)

    def test_returns_none_if_no_valid_branch(self):
        git = FakeGit(branches=[], current_branch=None)
        ui = FakeUI(strict=False)

        result = return_to_branch_core(git, ui, "feature", "main", [])

        assert result is None
        assert any("Unable to find" in msg for msg in ui.error_messages)


class TestSyncCore:
    """Tests for sync_core."""

    def test_successful_sync_no_children(self):
        git = FakeGit(branches=["main"], current_branch="main")
        git._commit_hashes["main"] = "abc123"
        config = FakeConfig()
        ui = FakeUI(strict=False)

        result = sync_core(git, config, ui, "main")

        assert result.main_branch == "main"
        assert result.deleted_branches == []
        assert result.updated_branches == []
        assert result.conflict_branches == []
        assert any("completed successfully" in msg for msg in ui.success_messages)

    def test_successful_sync_with_children(self):
        git = FakeGit(
            branches=["main", "feature1", "feature2"],
            current_branch="feature1",
        )
        git._commit_hashes["main"] = "abc123"
        config = FakeConfig(
            stack={
                "feature1": {"parent": "main"},
                "feature2": {"parent": "main"},
            }
        )
        ui = FakeUI(strict=False)

        result = sync_core(git, config, ui, "main", skip_push=True)

        assert result.main_branch == "main"
        assert set(result.updated_branches) == {"feature1", "feature2"}
        assert result.conflict_branches == []
        assert result.skip_push is True

    def test_sync_with_merged_branch_deletion(self):
        git = FakeGit(
            branches=["main", "feature1"],
            current_branch="main",
            merged_branches={"main": ["feature1"]},
        )
        git._commit_hashes["main"] = "abc123"
        config = FakeConfig(stack={"feature1": {"parent": "main"}})
        ui = FakeUI(confirm_responses=[True], strict=False)

        result = sync_core(git, config, ui, "main")

        assert result.deleted_branches == ["feature1"]
        assert "feature1" not in git.branches

    def test_sync_with_conflicts(self):
        git = FakeGit(
            branches=["main", "feature1"],
            current_branch="feature1",
        )
        git._commit_hashes["main"] = "abc123"
        git.fail_rebase = True
        config = FakeConfig(stack={"feature1": {"parent": "main"}})
        ui = FakeUI(strict=False)

        result = sync_core(git, config, ui, "main", skip_push=True)

        assert result.conflict_branches == ["feature1"]
        assert result.updated_branches == []

    def test_sync_raises_on_no_current_branch(self):
        git = FakeGit(current_branch=None)
        config = FakeConfig()
        ui = FakeUI(strict=False)

        with pytest.raises(BranchNotFoundError, match="current branch"):
            sync_core(git, config, ui, "main")

    def test_sync_returns_to_original_branch(self):
        git = FakeGit(
            branches=["main", "feature1"],
            current_branch="feature1",
        )
        git._commit_hashes["main"] = "abc123"
        config = FakeConfig()
        ui = FakeUI(strict=False)

        result = sync_core(git, config, ui, "main")

        assert result.original_branch == "feature1"
        assert result.returned_to == "feature1"
        assert git.current_branch == "feature1"

    def test_sync_returns_to_main_if_original_deleted(self):
        git = FakeGit(
            branches=["main", "feature1"],
            current_branch="feature1",
            merged_branches={"main": ["feature1"]},
        )
        git._commit_hashes["main"] = "abc123"
        config = FakeConfig(stack={"feature1": {"parent": "main"}})
        ui = FakeUI(confirm_responses=[True], strict=False)

        result = sync_core(git, config, ui, "main")

        assert result.original_branch == "feature1"
        assert result.returned_to == "main"
        assert git.current_branch == "main"

    def test_sync_with_push(self):
        git = FakeGit(
            branches=["main", "feature1"],
            current_branch="feature1",
            pushed_branches={"feature1"},
            unpushed_changes={"feature1": True},
        )
        git._commit_hashes["main"] = "abc123"
        config = FakeConfig(stack={"feature1": {"parent": "main"}})
        ui = FakeUI(strict=False)

        result = sync_core(git, config, ui, "main", skip_push=False)

        assert result.pushed_branches == ["feature1"]
        assert ("feature1", True) in git.push_calls

    def test_sync_skip_push(self):
        git = FakeGit(
            branches=["main", "feature1"],
            current_branch="feature1",
            pushed_branches={"feature1"},
            unpushed_changes={"feature1": True},
        )
        git._commit_hashes["main"] = "abc123"
        config = FakeConfig(stack={"feature1": {"parent": "main"}})
        ui = FakeUI(strict=False)

        result = sync_core(git, config, ui, "main", skip_push=True)

        assert result.pushed_branches == []
        assert result.skip_push is True
        assert git.push_calls == []
        assert any("local only" in msg for msg in ui.success_messages)
