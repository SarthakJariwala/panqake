"""Tests for move.py command module using dependency injection."""

import pytest

from panqake.commands.move import move_branch_core
from panqake.ports import (
    BranchNotFoundError,
    GitOperationError,
    MoveResult,
)
from panqake.testing import FakeConfig, FakeGit, FakeGitHub, FakeUI


class TestMoveBranchCore:
    """Tests for move_branch_core."""

    def test_moves_leaf_branch_with_no_pr(self):
        """Happy path: leaf branch, no descendants, no PR."""
        git = FakeGit(
            branches=["main", "feature-a", "feature-b"], current_branch="main"
        )
        git._commit_hashes = {"feature-b": "sha-b-old"}
        config = FakeConfig(
            stack={
                "feature-a": {"parent": "main"},
                "feature-b": {"parent": "feature-a"},
            }
        )
        github = FakeGitHub()
        ui = FakeUI(strict=False)

        result = move_branch_core(
            git=git,
            github=github,
            config=config,
            ui=ui,
            branch_name="feature-b",
            new_parent="main",
        )

        assert result.branch == "feature-b"
        assert result.old_parent == "feature-a"
        assert result.new_parent == "main"
        assert result.no_op is False
        assert config.get_parent_branch("feature-b") == "main"
        assert len(result.rebases) == 1
        assert result.rebases[0].rebased is True
        assert result.rebases[0].branch == "feature-b"
        # The branch itself was rebased with --onto main feature-a feature-b
        assert ("feature-b", "main", "feature-a", False) in git.rebase_onto_calls

    def test_defaults_to_current_branch(self):
        """When branch_name is omitted, use current branch."""
        git = FakeGit(
            branches=["main", "feature-a", "feature-b"], current_branch="feature-b"
        )
        config = FakeConfig(
            stack={
                "feature-a": {"parent": "main"},
                "feature-b": {"parent": "feature-a"},
            }
        )
        ui = FakeUI(strict=False)

        result = move_branch_core(
            git=git,
            github=FakeGitHub(),
            config=config,
            ui=ui,
            branch_name=None,
            new_parent="main",
        )

        assert result.branch == "feature-b"
        assert config.get_parent_branch("feature-b") == "main"

    def test_subtree_move_rebases_all_descendants(self):
        """Moving a branch with descendants rebases the whole subtree."""
        git = FakeGit(
            branches=["main", "a", "b", "c", "d", "feature"], current_branch="main"
        )
        git._commit_hashes = {
            "b": "sha-b-old",
            "c": "sha-c-old",
            "d": "sha-d-old",
        }
        config = FakeConfig(
            stack={
                "a": {"parent": "main"},
                "b": {"parent": "a"},
                "c": {"parent": "b"},
                "d": {"parent": "b"},
                "feature": {"parent": "main"},
            }
        )
        ui = FakeUI(strict=False)

        result = move_branch_core(
            git=git,
            github=FakeGitHub(),
            config=config,
            ui=ui,
            branch_name="b",
            new_parent="feature",
        )

        rebased = [r.branch for r in result.rebases if r.rebased]
        assert rebased == ["b", "c", "d"] or rebased == ["b", "d", "c"]
        assert config.get_parent_branch("b") == "feature"
        # Descendants' parents in the stack don't change
        assert config.get_parent_branch("c") == "b"
        assert config.get_parent_branch("d") == "b"
        # b rebased with --onto feature a b
        assert ("b", "feature", "a", False) in git.rebase_onto_calls
        # c rebased with --onto b sha-b-old c
        assert ("c", "b", "sha-b-old", False) in git.rebase_onto_calls
        # d rebased with --onto b sha-b-old d
        assert ("d", "b", "sha-b-old", False) in git.rebase_onto_calls

    def test_cycle_detection_rejects_descendant_as_parent(self):
        """Moving B onto one of its descendants raises an error."""
        git = FakeGit(branches=["main", "a", "b", "c"], current_branch="main")
        config = FakeConfig(
            stack={
                "a": {"parent": "main"},
                "b": {"parent": "a"},
                "c": {"parent": "b"},
            }
        )
        ui = FakeUI(strict=False)

        with pytest.raises(GitOperationError) as exc_info:
            move_branch_core(
                git=git,
                github=FakeGitHub(),
                config=config,
                ui=ui,
                branch_name="b",
                new_parent="c",
            )
        assert "cycle" in str(exc_info.value).lower()
        # Metadata should not have been touched
        assert config.get_parent_branch("b") == "a"
        assert git.rebase_onto_calls == []

    def test_self_reparent_rejected(self):
        """Moving a branch onto itself is a cycle."""
        git = FakeGit(branches=["main", "feature"], current_branch="main")
        config = FakeConfig(stack={"feature": {"parent": "main"}})
        ui = FakeUI(strict=False)

        with pytest.raises(GitOperationError):
            move_branch_core(
                git=git,
                github=FakeGitHub(),
                config=config,
                ui=ui,
                branch_name="feature",
                new_parent="feature",
            )

    def test_no_op_when_already_parented_correctly(self):
        """Moving to the current parent is a no-op."""
        git = FakeGit(branches=["main", "feature"], current_branch="main")
        config = FakeConfig(stack={"feature": {"parent": "main"}})
        ui = FakeUI(strict=False)

        result = move_branch_core(
            git=git,
            github=FakeGitHub(),
            config=config,
            ui=ui,
            branch_name="feature",
            new_parent="main",
        )

        assert result.no_op is True
        assert result.rebases == []
        assert git.rebase_onto_calls == []

    def test_branch_not_tracked_raises(self):
        """Moving an untracked branch is an error."""
        git = FakeGit(branches=["main", "feature"], current_branch="main")
        config = FakeConfig()  # nothing tracked
        ui = FakeUI(strict=False)

        with pytest.raises(BranchNotFoundError) as exc_info:
            move_branch_core(
                git=git,
                github=FakeGitHub(),
                config=config,
                ui=ui,
                branch_name="feature",
                new_parent="main",
            )
        assert "not tracked" in str(exc_info.value)

    def test_branch_not_in_git_raises(self):
        """Moving a nonexistent git branch is an error."""
        git = FakeGit(branches=["main"], current_branch="main")
        config = FakeConfig(stack={"feature": {"parent": "main"}})
        ui = FakeUI(strict=False)

        with pytest.raises(BranchNotFoundError):
            move_branch_core(
                git=git,
                github=FakeGitHub(),
                config=config,
                ui=ui,
                branch_name="feature",
                new_parent="main",
            )

    def test_untracked_new_parent_is_allowed(self):
        """An untracked git branch (e.g., main) can serve as the new parent.

        Matches `pq new` semantics — the parent only needs to exist in git, not
        in the panqake stack, since main/master are usually not formally tracked.
        """
        git = FakeGit(branches=["main", "a", "b", "other"], current_branch="main")
        config = FakeConfig(stack={"a": {"parent": "main"}, "b": {"parent": "a"}})
        ui = FakeUI(strict=False)

        result = move_branch_core(
            git=git,
            github=FakeGitHub(),
            config=config,
            ui=ui,
            branch_name="b",
            new_parent="other",
        )

        assert result.no_op is False
        assert config.get_parent_branch("b") == "other"

    def test_root_branch_cannot_be_moved(self):
        """A root branch (no parent) cannot be reparented."""
        git = FakeGit(branches=["main"], current_branch="main")
        config = FakeConfig(stack={"main": {"parent": ""}})
        ui = FakeUI(strict=False)

        with pytest.raises(GitOperationError) as exc_info:
            move_branch_core(
                git=git,
                github=FakeGitHub(),
                config=config,
                ui=ui,
                branch_name="main",
                new_parent="main",
            )
        assert "root branch" in str(exc_info.value)

    def test_conflict_on_branch_returns_partial_result(self):
        """A conflict during the primary rebase leaves git mid-rebase and is recorded."""
        git = FakeGit(branches=["main", "a", "b"], current_branch="main")
        git.fail_rebase = True
        config = FakeConfig(stack={"a": {"parent": "main"}, "b": {"parent": "a"}})
        ui = FakeUI(strict=False)

        result = move_branch_core(
            git=git,
            github=FakeGitHub(),
            config=config,
            ui=ui,
            branch_name="b",
            new_parent="main",
        )

        assert isinstance(result, MoveResult)
        assert len(result.rebases) == 1
        assert result.rebases[0].rebased is False
        assert result.rebases[0].error is not None
        # Metadata was already updated before the rebase attempt
        assert config.get_parent_branch("b") == "main"
        # User stays on the conflicted branch — no restore attempt
        assert result.returned_to is None

    def test_conflict_on_descendant_stops_chain(self):
        """A conflict mid-chain records the failure and stops processing further descendants."""
        git = FakeGit(branches=["main", "a", "b", "c", "d"], current_branch="main")
        git._commit_hashes = {"b": "sha-b-old", "c": "sha-c-old"}

        # Make the first rebase succeed, second succeed, third fail
        original_rebase = git.rebase_onto
        call_count = {"n": 0}

        def selective_rebase(branch, new_base, abort_on_conflict=True, upstream=None):
            call_count["n"] += 1
            if call_count["n"] == 3:
                from panqake.ports import RebaseConflictError

                git.rebase_onto_calls.append((branch, new_base, upstream, False))
                raise RebaseConflictError(f"Rebase conflict in branch '{branch}'")
            return original_rebase(
                branch, new_base, abort_on_conflict=abort_on_conflict, upstream=upstream
            )

        git.rebase_onto = selective_rebase  # type: ignore[assignment]

        config = FakeConfig(
            stack={
                "a": {"parent": "main"},
                "b": {"parent": "a"},
                "c": {"parent": "b"},
                "d": {"parent": "c"},
            }
        )
        ui = FakeUI(strict=False)

        result = move_branch_core(
            git=git,
            github=FakeGitHub(),
            config=config,
            ui=ui,
            branch_name="b",
            new_parent="main",
        )

        # b succeeded, c succeeded, d failed → 3 entries (b, c, d)
        # Actually: b succeeded, c failed → only 2 entries (depending on order)
        # Our selective_rebase fails on call 3, which is the second descendant
        succeeded = [r for r in result.rebases if r.rebased]
        failed = [r for r in result.rebases if not r.rebased]
        assert len(failed) == 1
        # First two rebases (b and one descendant) succeeded
        assert len(succeeded) == 2

    def test_worktree_branch_uses_worktree_rebase(self):
        """A branch in a worktree gets rebased via the worktree-aware helper."""
        git = FakeGit(branches=["main", "a", "b"], current_branch="main")
        git.worktrees["b"] = "/path/to/wt"
        config = FakeConfig(
            stack={
                "a": {"parent": "main"},
                "b": {"parent": "a", "worktree": "/path/to/wt"},
            }
        )
        ui = FakeUI(strict=False)

        move_branch_core(
            git=git,
            github=FakeGitHub(),
            config=config,
            ui=ui,
            branch_name="b",
            new_parent="main",
        )

        # The fourth tuple element indicates worktree-aware rebase
        worktree_calls = [c for c in git.rebase_onto_calls if c[3]]
        assert any(c[0] == "b" for c in worktree_calls)

    def test_pr_base_updated_when_branch_has_pr(self):
        """When the moved branch has an open PR, its base is updated on GitHub."""
        git = FakeGit(branches=["main", "a", "b"], current_branch="main")
        config = FakeConfig(stack={"a": {"parent": "main"}, "b": {"parent": "a"}})
        github = FakeGitHub(branches_with_pr={"b"})
        ui = FakeUI(strict=False)

        result = move_branch_core(
            git=git,
            github=github,
            config=config,
            ui=ui,
            branch_name="b",
            new_parent="main",
        )

        assert github.update_pr_base_calls == [("b", "main")]
        assert result.pr_base_update is not None
        assert result.pr_base_update.updated is True

    def test_warns_when_gh_not_installed(self):
        """If gh is missing, the move proceeds with a warning."""
        git = FakeGit(branches=["main", "a", "b"], current_branch="main")
        config = FakeConfig(stack={"a": {"parent": "main"}, "b": {"parent": "a"}})
        github = FakeGitHub(cli_installed=False)
        ui = FakeUI(strict=False)

        result = move_branch_core(
            git=git,
            github=github,
            config=config,
            ui=ui,
            branch_name="b",
            new_parent="main",
        )

        assert any("GitHub CLI" in w for w in result.warnings)
        assert result.pr_base_update is None
        # Move still succeeded
        assert config.get_parent_branch("b") == "main"
        assert all(r.rebased for r in result.rebases)

    def test_restores_original_branch_on_success(self):
        """User is returned to where they started after a successful move."""
        git = FakeGit(branches=["main", "a", "b", "other"], current_branch="other")
        config = FakeConfig(
            stack={
                "a": {"parent": "main"},
                "b": {"parent": "a"},
                "other": {"parent": "main"},
            }
        )
        ui = FakeUI(strict=False)

        result = move_branch_core(
            git=git,
            github=FakeGitHub(),
            config=config,
            ui=ui,
            branch_name="b",
            new_parent="main",
        )

        assert result.returned_to == "other"
        assert git.current_branch == "other"

    def test_prompts_for_new_parent_when_not_provided(self):
        """When new_parent is None, the UI is prompted with tracked branches."""
        git = FakeGit(branches=["main", "a", "b", "feature"], current_branch="main")
        config = FakeConfig(
            stack={
                "a": {"parent": "main"},
                "b": {"parent": "a"},
                "feature": {"parent": "main"},
            }
        )
        ui = FakeUI(select_branch_responses=["feature"])

        result = move_branch_core(
            git=git,
            github=FakeGitHub(),
            config=config,
            ui=ui,
            branch_name="b",
            new_parent=None,
        )

        assert result.new_parent == "feature"
        assert len(ui.select_branch_calls) == 1
