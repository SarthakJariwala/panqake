"""Tests for move.py command module using dependency injection."""

import pytest

from panqake.commands.move import move_branch_core, move_continue_core
from panqake.ports import (
    BranchNotFoundError,
    GitOperationError,
    MoveContinueResult,
    MoveResult,
    RebaseConflictError,
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

    def test_conflict_in_subtree_stops_sibling_processing(self):
        """A conflict deep in one subtree must stop processing of sibling subtrees.

        Tree: main -> b -> c -> d, plus b -> e. Move b to feature.
        Rebase d conflicts. The bug-fix ensures we don't continue on to e while
        git is mid-rebase from d.
        """
        git = FakeGit(
            branches=["main", "a", "b", "c", "d", "e", "feature"],
            current_branch="main",
        )

        original_rebase = git.rebase_onto

        def failing_rebase_for_d(
            branch, new_base, abort_on_conflict=True, upstream=None
        ):
            if branch == "d":
                from panqake.ports import RebaseConflictError

                git.rebase_onto_calls.append((branch, new_base, upstream, False))
                raise RebaseConflictError(f"Rebase conflict in branch '{branch}'")
            return original_rebase(
                branch, new_base, abort_on_conflict=abort_on_conflict, upstream=upstream
            )

        git.rebase_onto = failing_rebase_for_d  # type: ignore[assignment]

        config = FakeConfig(
            stack={
                "a": {"parent": "main"},
                "b": {"parent": "a"},
                "c": {"parent": "b"},
                "d": {"parent": "c"},
                "e": {"parent": "b"},
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

        # b and c rebased, d failed, e must NOT be attempted
        rebased_branches = [r.branch for r in result.rebases if r.rebased]
        failed_branches = [r.branch for r in result.rebases if not r.rebased]
        assert "e" not in rebased_branches
        assert "e" not in failed_branches
        assert "d" in failed_branches
        # No rebase attempt on e
        assert all(c[0] != "e" for c in git.rebase_onto_calls)

    def test_non_conflict_failure_rolls_back_metadata(self):
        """A non-conflict rebase failure (e.g., checkout fails) rolls back metadata.

        Stack parent is mutated before the rebase to keep the recovery path clean
        for conflicts, but a non-conflict failure means the branch was NEVER
        rebased onto the new parent — so leaving the stack pointing at the new
        parent would lie. Verify metadata and PR base are restored.
        """
        git = FakeGit(branches=["main", "a", "b"], current_branch="main")

        def failing_rebase(branch, new_base, abort_on_conflict=True, upstream=None):
            raise GitOperationError(f"Failed to checkout branch '{branch}'")

        git.rebase_onto = failing_rebase  # type: ignore[assignment]

        config = FakeConfig(stack={"a": {"parent": "main"}, "b": {"parent": "a"}})
        github = FakeGitHub(branches_with_pr={"b"})
        ui = FakeUI(strict=False)

        with pytest.raises(GitOperationError):
            move_branch_core(
                git=git,
                github=github,
                config=config,
                ui=ui,
                branch_name="b",
                new_parent="main",
            )

        # Metadata rolled back to original parent
        assert config.get_parent_branch("b") == "a"
        # PR base rolled back too (best-effort)
        assert github.update_pr_base_calls[-1] == ("b", "a")

    def test_stale_worktree_metadata_uses_regular_rebase(self):
        """Stale worktree metadata must not route to the worktree rebase path.

        The worktree-aware rebase doesn't checkout the target branch — it relies
        on the branch's worktree directory. If stack metadata says a branch has
        a worktree but git disagrees (e.g., the worktree was removed outside
        panqake), routing through that path would rebase whichever branch is
        checked out in the current directory rather than the requested one.
        """
        git = FakeGit(branches=["main", "a", "b"], current_branch="main")
        # NOTE: git.worktrees is intentionally empty — git's actual state says
        # `b` is NOT in a worktree.
        config = FakeConfig(
            stack={
                "a": {"parent": "main"},
                # Stale metadata: stack still records a worktree path
                "b": {"parent": "a", "worktree": "/stale/worktree/path"},
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

        # The 4th tuple element marks worktree-aware rebases. b should NOT
        # have used the worktree path despite the stale metadata.
        b_rebases = [c for c in git.rebase_onto_calls if c[0] == "b"]
        assert b_rebases == [("b", "main", "a", False)]

    def test_validates_old_parent_exists_in_git(self):
        """If the tracked parent has been deleted from git, fail early.

        Otherwise the rebase would die with an opaque 'invalid upstream'
        error reported as a misleading conflict, AFTER metadata has been
        mutated.
        """
        git = FakeGit(branches=["main", "b"], current_branch="main")
        # `a` is tracked as b's parent but doesn't exist in git
        config = FakeConfig(stack={"a": {"parent": "main"}, "b": {"parent": "a"}})
        github = FakeGitHub(branches_with_pr={"b"})
        ui = FakeUI(strict=False)

        with pytest.raises(BranchNotFoundError) as exc_info:
            move_branch_core(
                git=git,
                github=github,
                config=config,
                ui=ui,
                branch_name="b",
                new_parent="main",
            )
        assert "stale" in str(exc_info.value).lower()

        # Nothing should have been mutated
        assert config.get_parent_branch("b") == "a"
        assert github.update_pr_base_calls == []
        assert git.rebase_onto_calls == []

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
        """When new_parent is None, the UI is prompted with eligible branches."""
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

    def test_prompt_includes_main_and_excludes_descendants(self):
        """The interactive prompt offers untracked trunks (main) and hides descendants."""
        git = FakeGit(
            branches=["main", "trunk", "a", "b", "c", "feature"],
            current_branch="main",
        )
        config = FakeConfig(
            stack={
                "a": {"parent": "main"},
                "b": {"parent": "a"},
                "c": {"parent": "b"},
                "feature": {"parent": "main"},
            }
        )
        ui = FakeUI(select_branch_responses=["main"])

        move_branch_core(
            git=git,
            github=FakeGitHub(),
            config=config,
            ui=ui,
            branch_name="b",
            new_parent=None,
        )

        offered = ui.select_branch_calls[0][0]
        assert "main" in offered  # untracked trunk is selectable
        assert "trunk" in offered  # other untracked branch is selectable
        assert "feature" in offered  # sibling stack is selectable
        assert "b" not in offered  # the branch being moved is excluded
        assert "c" not in offered  # descendants would create a cycle


class TestMoveConflictPersistsPendingRebase:
    """Verify that a conflicted move persists enough state to resume safely.

    Regression for P1: previously, a move that conflicted before descendants
    were rebased left descendants based on the moved branch's pre-rebase
    SHA, and the recommended `pq update` recovery used a plain rebase that
    replayed commits from the *old parent's* history into descendants.
    """

    def test_conflict_on_moved_branch_persists_old_sha(self):
        """When the moved branch's own rebase conflicts, persist its old SHA."""
        git = FakeGit(branches=["main", "a", "b", "c"], current_branch="main")
        git._commit_hashes = {"b": "sha-b-old", "c": "sha-c-old"}
        git.fail_rebase = True

        config = FakeConfig(
            stack={
                "a": {"parent": "main"},
                "b": {"parent": "a"},
                "c": {"parent": "b"},
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

        assert isinstance(result, MoveResult)
        assert result.rebases[0].rebased is False
        # The moved branch's old SHA must be persisted so the resume flow
        # knows what `--onto` upstream to use when rebasing descendants.
        assert config.get_pending_rebase_from("b") == "sha-b-old"

    def test_conflict_on_descendant_persists_its_old_sha(self):
        """A conflict deeper in the chain persists *that* branch's old SHA."""
        git = FakeGit(branches=["main", "a", "b", "c", "d"], current_branch="main")
        git._commit_hashes = {
            "b": "sha-b-old",
            "c": "sha-c-old",
            "d": "sha-d-old",
        }

        original_rebase = git.rebase_onto

        def fail_on_d(branch, new_base, abort_on_conflict=True, upstream=None):
            if branch == "d":
                git.rebase_onto_calls.append((branch, new_base, upstream, False))
                raise RebaseConflictError(f"Rebase conflict in branch '{branch}'")
            return original_rebase(
                branch, new_base, abort_on_conflict=abort_on_conflict, upstream=upstream
            )

        git.rebase_onto = fail_on_d  # type: ignore[assignment]

        config = FakeConfig(
            stack={
                "a": {"parent": "main"},
                "b": {"parent": "a"},
                "c": {"parent": "b"},
                "d": {"parent": "c"},
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

        # d's pre-rebase SHA is persisted so a continue can resume at d
        # with the right upstream.
        assert config.get_pending_rebase_from("d") == "sha-d-old"

    def test_successful_move_clears_pending_state(self):
        """After a fully successful move, no pending_rebase_from remains."""
        git = FakeGit(branches=["main", "a", "b", "c"], current_branch="main")
        git._commit_hashes = {"b": "sha-b-old", "c": "sha-c-old"}

        config = FakeConfig(
            stack={
                "a": {"parent": "main"},
                "b": {"parent": "a"},
                "c": {"parent": "b"},
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

        assert config.get_pending_rebase_from("b") is None
        assert config.get_pending_rebase_from("c") is None


class TestMoveContinueCore:
    """Tests for the `pq move --continue` resume command."""

    def test_no_pending_state_is_no_op(self):
        """With no persisted pending state, continue is a no-op."""
        git = FakeGit(branches=["main", "a"], current_branch="main")
        config = FakeConfig(stack={"a": {"parent": "main"}})
        ui = FakeUI(strict=False)

        result = move_continue_core(git=git, config=config, ui=ui)

        assert isinstance(result, MoveContinueResult)
        assert result.no_op is True
        assert result.rebases == []

    def test_refuses_while_git_mid_rebase(self):
        """If git is still mid-rebase, refuse with a clear message."""
        git = FakeGit(branches=["main", "a"], current_branch="main")
        git.rebase_in_progress = True
        config = FakeConfig(
            stack={"a": {"parent": "main", "pending_rebase_from": "sha"}}
        )
        ui = FakeUI(strict=False)

        with pytest.raises(GitOperationError) as exc_info:
            move_continue_core(git=git, config=config, ui=ui)
        assert "mid-rebase" in str(exc_info.value)

    def test_refuses_when_resume_root_still_at_old_sha(self):
        """If the user never ran `git rebase --continue`, refuse."""
        git = FakeGit(branches=["main", "a"], current_branch="main")
        git._commit_hashes = {"a": "sha-a-old"}
        config = FakeConfig(
            stack={"a": {"parent": "main", "pending_rebase_from": "sha-a-old"}}
        )
        ui = FakeUI(strict=False)

        with pytest.raises(GitOperationError) as exc_info:
            move_continue_core(git=git, config=config, ui=ui)
        assert "pre-move SHA" in str(exc_info.value)

    def test_resumes_descendants_with_onto_old_sha(self):
        """Regression for the corruption bug.

        Setup: `pq move b main` conflicted on b. User resolved and ran
        `git rebase --continue` so b is now at a new SHA. Descendant c is
        still based on b's old SHA. `pq move --continue` MUST rebase c
        with `git rebase --onto b <b's old SHA> c` — not a plain rebase.
        """
        git = FakeGit(branches=["main", "a", "b", "c"], current_branch="b")
        git._commit_hashes = {"b": "sha-b-new", "c": "sha-c-old"}
        config = FakeConfig(
            stack={
                "a": {"parent": "main"},
                # `pq move b main` already updated parent metadata.
                "b": {"parent": "main", "pending_rebase_from": "sha-b-old"},
                "c": {"parent": "b"},
            }
        )
        ui = FakeUI(strict=False)

        result = move_continue_core(git=git, config=config, ui=ui)

        assert result.resumed_branch == "b"
        assert any(r.branch == "c" and r.rebased for r in result.rebases)

        # The critical assertion: c was rebased with upstream=b's OLD SHA,
        # not None. Without this, descendants are rebased with a plain
        # `git rebase b c`, which would replay commits from b's old
        # history (including commits from its old parent) into c.
        c_calls = [call for call in git.rebase_onto_calls if call[0] == "c"]
        assert len(c_calls) == 1
        branch, new_base, upstream, _ = c_calls[0]
        assert new_base == "b"
        assert upstream == "sha-b-old"

        # Pending state is cleared on success.
        assert config.get_pending_rebase_from("b") is None
        assert config.get_pending_rebase_from("c") is None

    def test_resume_with_descendant_conflict_persists_new_state(self):
        """If the resume itself conflicts on a deeper descendant, that
        descendant's own pre-rebase SHA must be persisted so a second
        `pq move --continue` picks up at the right place.
        """
        git = FakeGit(branches=["main", "b", "c", "d"], current_branch="b")
        git._commit_hashes = {
            "b": "sha-b-new",
            "c": "sha-c-old",
            "d": "sha-d-old",
        }

        original_rebase = git.rebase_onto

        def fail_on_d(branch, new_base, abort_on_conflict=True, upstream=None):
            if branch == "d":
                git.rebase_onto_calls.append((branch, new_base, upstream, False))
                raise RebaseConflictError(f"Rebase conflict in branch '{branch}'")
            return original_rebase(
                branch, new_base, abort_on_conflict=abort_on_conflict, upstream=upstream
            )

        git.rebase_onto = fail_on_d  # type: ignore[assignment]

        config = FakeConfig(
            stack={
                "b": {"parent": "main", "pending_rebase_from": "sha-b-old"},
                "c": {"parent": "b"},
                "d": {"parent": "c"},
            }
        )
        ui = FakeUI(strict=False)

        result = move_continue_core(git=git, config=config, ui=ui)

        failed = [r for r in result.rebases if not r.rebased]
        assert len(failed) == 1
        assert failed[0].branch == "d"

        # b's state stays set (its subtree isn't done yet), AND d now has
        # its own pre-rebase SHA persisted so a second resume can run
        # `git rebase --onto c <d's old SHA> d` after the user fixes d.
        assert config.get_pending_rebase_from("b") == "sha-b-old"
        assert config.get_pending_rebase_from("d") == "sha-d-old"

    def test_resume_root_is_topmost_pending(self):
        """When multiple pending entries exist, resume from the topmost."""
        git = FakeGit(branches=["main", "b", "c"], current_branch="main")
        git._commit_hashes = {"b": "sha-b-new", "c": "sha-c-new"}
        config = FakeConfig(
            stack={
                # b is an ancestor of c; resume should pick b.
                "b": {"parent": "main", "pending_rebase_from": "sha-b-old"},
                "c": {"parent": "b", "pending_rebase_from": "sha-c-old"},
            }
        )
        ui = FakeUI(strict=False)

        result = move_continue_core(git=git, config=config, ui=ui)

        assert result.resumed_branch == "b"
