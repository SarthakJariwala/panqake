"""Tests for merge.py command module using dependency injection pattern."""

import pytest

from panqake.commands.merge import (
    cleanup_local_branch_core,
    merge_branch_core,
    update_child_branches_core,
    update_pr_base_for_direct_children,
)
from panqake.ports import (
    GitHubCLINotFoundError,
    PRMergeError,
    UserCancelledError,
)
from panqake.testing.fakes import FakeConfig, FakeGit, FakeGitHub, FakeUI


class TestUpdatePRBaseForDirectChildren:
    """Tests for update_pr_base_for_direct_children."""

    def test_no_children_returns_empty(self):
        config = FakeConfig()
        github = FakeGitHub()

        result = update_pr_base_for_direct_children("feature", "main", config, github)

        assert result == []

    def test_child_without_pr_not_updated(self):
        config = FakeConfig(
            stack={
                "feature": {"parent": "main"},
                "child": {"parent": "feature"},
            }
        )
        github = FakeGitHub()

        result = update_pr_base_for_direct_children("feature", "main", config, github)

        assert len(result) == 1
        assert result[0].branch == "child"
        assert result[0].had_pr is False
        assert result[0].updated is False
        assert len(github.update_pr_base_calls) == 0

    def test_child_with_pr_updated(self):
        config = FakeConfig(
            stack={
                "feature": {"parent": "main"},
                "child": {"parent": "feature"},
            }
        )
        github = FakeGitHub(branches_with_pr={"child"})

        result = update_pr_base_for_direct_children("feature", "main", config, github)

        assert len(result) == 1
        assert result[0].branch == "child"
        assert result[0].had_pr is True
        assert result[0].updated is True
        assert ("child", "main") in github.update_pr_base_calls

    def test_update_failure_recorded_in_result(self):
        config = FakeConfig(
            stack={
                "feature": {"parent": "main"},
                "child": {"parent": "feature"},
            }
        )
        github = FakeGitHub(branches_with_pr={"child"})
        github.fail_update_pr_base = True

        result = update_pr_base_for_direct_children("feature", "main", config, github)

        assert len(result) == 1
        assert result[0].branch == "child"
        assert result[0].had_pr is True
        assert result[0].updated is False
        assert result[0].error is not None


class TestUpdateChildBranchesCore:
    """Tests for update_child_branches_core."""

    def test_no_children_returns_empty(self):
        git = FakeGit(branches=["main", "feature"])
        config = FakeConfig(stack={"feature": {"parent": "main"}})

        result = update_child_branches_core("feature", "main", git, config)

        assert result == []

    def test_child_rebased_successfully(self):
        git = FakeGit(branches=["main", "feature", "child"])
        config = FakeConfig(
            stack={
                "feature": {"parent": "main"},
                "child": {"parent": "feature"},
            }
        )

        result = update_child_branches_core("feature", "main", git, config)

        assert len(result) == 1
        assert result[0].branch == "child"
        assert result[0].rebased is True
        assert ("child", "main") in git.rebase_calls
        assert config.get_parent_branch("child") == "main"

    def test_rebase_conflict_stops_processing(self):
        git = FakeGit(branches=["main", "feature", "child1", "child2"])
        git.fail_rebase = True
        config = FakeConfig(
            stack={
                "feature": {"parent": "main"},
                "child1": {"parent": "feature"},
                "child2": {"parent": "feature"},
            }
        )

        result = update_child_branches_core("feature", "main", git, config)

        assert len(result) == 1
        assert result[0].rebased is False
        assert result[0].error is not None


class TestCleanupLocalBranchCore:
    """Tests for cleanup_local_branch_core."""

    def test_branch_not_exists_returns_success(self):
        git = FakeGit(branches=["main"])
        config = FakeConfig()

        local_del, stack_del, warnings = cleanup_local_branch_core(
            "feature", "main", git, config
        )

        assert local_del is True
        assert stack_del is True
        assert warnings == []

    def test_deletes_local_branch(self):
        git = FakeGit(branches=["main", "feature"], current_branch="main")
        config = FakeConfig(stack={"feature": {"parent": "main"}})

        local_del, stack_del, warnings = cleanup_local_branch_core(
            "feature", "main", git, config
        )

        assert local_del is True
        assert stack_del is True
        assert "feature" in git.deleted_local_branches
        assert "feature" not in config.stack

    def test_checkout_parent_if_on_branch(self):
        git = FakeGit(branches=["main", "feature"], current_branch="feature")
        config = FakeConfig(stack={"feature": {"parent": "main"}})

        local_del, stack_del, warnings = cleanup_local_branch_core(
            "feature", "main", git, config
        )

        assert local_del is True
        assert "main" in git.checkout_calls

    def test_worktree_removed_before_delete(self):
        git = FakeGit(branches=["main", "feature"], current_branch="main")
        git.worktrees["feature"] = "/path/to/worktree"
        config = FakeConfig(
            stack={"feature": {"parent": "main", "worktree": "/path/to/worktree"}}
        )

        local_del, stack_del, warnings = cleanup_local_branch_core(
            "feature", "main", git, config
        )

        assert local_del is True
        assert "/path/to/worktree" in git.removed_worktrees


class TestMergeBranchCore:
    """Tests for merge_branch_core."""

    def test_raises_when_cli_not_installed(self):
        git = FakeGit(branches=["main", "feature"], current_branch="feature")
        github = FakeGitHub(cli_installed=False)
        config = FakeConfig()
        ui = FakeUI(strict=False)

        with pytest.raises(GitHubCLINotFoundError):
            merge_branch_core(
                git=git,
                github=github,
                config=config,
                ui=ui,
                branch_name="feature",
            )

    def test_raises_when_no_pr(self):
        git = FakeGit(branches=["main", "feature"], current_branch="feature")
        github = FakeGitHub()
        config = FakeConfig(stack={"feature": {"parent": "main"}})
        ui = FakeUI(strict=False)

        with pytest.raises(PRMergeError):
            merge_branch_core(
                git=git,
                github=github,
                config=config,
                ui=ui,
                branch_name="feature",
            )

    def test_merges_pr_successfully(self):
        git = FakeGit(branches=["main", "feature"], current_branch="main")
        github = FakeGitHub(branches_with_pr={"feature"})
        config = FakeConfig(stack={"feature": {"parent": "main"}})
        ui = FakeUI(strict=False)

        result = merge_branch_core(
            git=git,
            github=github,
            config=config,
            ui=ui,
            branch_name="feature",
            delete_branch=False,
            update_children=False,
        )

        assert result.branch == "feature"
        assert result.parent_branch == "main"
        assert ("feature", "squash") in github.merge_pr_calls

    def test_deletes_remote_branch_when_requested(self):
        git = FakeGit(
            branches=["main", "feature"],
            current_branch="main",
            pushed_branches={"feature"},
        )
        github = FakeGitHub(branches_with_pr={"feature"})
        config = FakeConfig(stack={"feature": {"parent": "main"}})
        ui = FakeUI(strict=False)

        result = merge_branch_core(
            git=git,
            github=github,
            config=config,
            ui=ui,
            branch_name="feature",
            delete_branch=True,
            update_children=False,
        )

        assert result.remote_branch_deleted is True
        assert "feature" in git.deleted_remote_branches

    def test_checks_pr_status_before_merge(self):
        git = FakeGit(branches=["main", "feature"], current_branch="main")
        github = FakeGitHub(
            branches_with_pr={"feature"},
            pr_checks={"feature": (False, ["CI failed"])},
        )
        config = FakeConfig(stack={"feature": {"parent": "main"}})
        ui = FakeUI(confirm_responses=[False], strict=False)

        with pytest.raises(UserCancelledError):
            merge_branch_core(
                git=git,
                github=github,
                config=config,
                ui=ui,
                branch_name="feature",
            )

    def test_proceeds_when_user_confirms_failed_checks(self):
        git = FakeGit(branches=["main", "feature"], current_branch="main")
        github = FakeGitHub(
            branches_with_pr={"feature"},
            pr_checks={"feature": (False, ["CI failed"])},
        )
        config = FakeConfig(stack={"feature": {"parent": "main"}})
        ui = FakeUI(confirm_responses=[True], strict=False)

        result = merge_branch_core(
            git=git,
            github=github,
            config=config,
            ui=ui,
            branch_name="feature",
            delete_branch=False,
            update_children=False,
        )

        assert result.checks_passed is False
        assert "CI failed" in result.failed_checks
        assert "feature" in github.merged_prs

    def test_updates_child_pr_bases(self):
        git = FakeGit(branches=["main", "feature", "child"], current_branch="main")
        github = FakeGitHub(branches_with_pr={"feature", "child"})
        config = FakeConfig(
            stack={
                "feature": {"parent": "main"},
                "child": {"parent": "feature"},
            }
        )
        ui = FakeUI(strict=False)

        result = merge_branch_core(
            git=git,
            github=github,
            config=config,
            ui=ui,
            branch_name="feature",
            delete_branch=False,
            update_children=True,
        )

        assert len(result.pr_base_updates) == 1
        assert result.pr_base_updates[0].branch == "child"
        assert result.pr_base_updates[0].updated is True
        assert ("child", "main") in github.update_pr_base_calls

    def test_rebases_child_branches(self):
        git = FakeGit(branches=["main", "feature", "child"], current_branch="main")
        github = FakeGitHub(branches_with_pr={"feature"})
        config = FakeConfig(
            stack={
                "feature": {"parent": "main"},
                "child": {"parent": "feature"},
            }
        )
        ui = FakeUI(strict=False)

        result = merge_branch_core(
            git=git,
            github=github,
            config=config,
            ui=ui,
            branch_name="feature",
            delete_branch=False,
            update_children=True,
        )

        assert len(result.child_updates) == 1
        assert result.child_updates[0].branch == "child"
        assert result.child_updates[0].rebased is True
        assert ("child", "main") in git.rebase_calls

    def test_returns_to_original_branch(self):
        git = FakeGit(branches=["main", "feature", "other"], current_branch="other")
        github = FakeGitHub(branches_with_pr={"feature"})
        config = FakeConfig(stack={"feature": {"parent": "main"}})
        ui = FakeUI(strict=False)

        result = merge_branch_core(
            git=git,
            github=github,
            config=config,
            ui=ui,
            branch_name="feature",
            delete_branch=False,
            update_children=False,
        )

        assert result.returned_to == "other"

    def test_returns_to_parent_if_original_deleted(self):
        git = FakeGit(branches=["main", "feature"], current_branch="feature")
        github = FakeGitHub(branches_with_pr={"feature"})
        config = FakeConfig(stack={"feature": {"parent": "main"}})
        ui = FakeUI(strict=False)

        result = merge_branch_core(
            git=git,
            github=github,
            config=config,
            ui=ui,
            branch_name="feature",
            delete_branch=True,
            update_children=False,
        )

        assert result.returned_to == "main"


class TestUserCancellation:
    """Tests for user cancellation handling."""

    def test_cancel_on_failed_checks_confirmation(self):
        git = FakeGit(branches=["main", "feature"], current_branch="main")
        github = FakeGitHub(
            branches_with_pr={"feature"},
            pr_checks={"feature": (False, ["CI failed"])},
        )
        config = FakeConfig(stack={"feature": {"parent": "main"}})
        ui = FakeUI(cancel_on_confirm=True)

        with pytest.raises(UserCancelledError):
            merge_branch_core(
                git=git,
                github=github,
                config=config,
                ui=ui,
                branch_name="feature",
            )
