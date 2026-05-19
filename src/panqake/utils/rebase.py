"""Shared subtree-rebase helper used by `pq move` and `pq move --continue`.

Centralizes the `git rebase --onto NEW_BASE OLD_SHA BRANCH` walk so the
recovery path can resume with the same semantics as the success path,
and so the pre-rebase SHA of each branch is persisted to `stacks.json`
before its rebase starts (allowing a second resume if a deeper conflict
hits).
"""

from panqake.ports import (
    BranchRebaseResult,
    ConfigPort,
    GitPort,
    RebaseConflictError,
)
from panqake.utils.types import BranchName


def _rebase_branch(
    git: GitPort,
    branch: BranchName,
    new_base: BranchName,
    upstream: BranchName | None,
) -> None:
    """Rebase a branch onto a new base, picking the worktree-aware variant.

    Uses git's actual worktree state rather than panqake stack metadata, since
    stored worktree paths can be stale (e.g., after a worktree was removed
    outside of panqake) and routing through the worktree path without an
    explicit checkout would rewrite the wrong branch. `abort_on_conflict=False`
    leaves git mid-rebase so the user can resolve and continue.
    """
    if git.is_branch_worktree(branch):
        git.rebase_onto_in_worktree(
            branch, new_base, abort_on_conflict=False, upstream=upstream
        )
    else:
        git.rebase_onto(branch, new_base, abort_on_conflict=False, upstream=upstream)


def rebase_subtree(
    git: GitPort,
    config: ConfigPort,
    parent: BranchName,
    parent_old_sha: str,
) -> list[BranchRebaseResult]:
    """Recursively rebase descendants of `parent` after its tip was rewritten.

    For each child of `parent`, replays commits in `(parent_old_sha..child]`
    onto the new tip of `parent`. Before each child's rebase starts, the
    child's current SHA is written to its `pending_rebase_from` metadata so
    that a conflict deeper in the subtree can be resumed via
    `pq move --continue`. On success, the field is cleared.

    Stops on the first conflict (including conflicts raised deeper in the
    subtree); leaves git mid-rebase and the relevant `pending_rebase_from`
    fields populated for recovery.
    """
    results: list[BranchRebaseResult] = []
    for child in config.get_child_branches(parent):
        child_old_sha = git.get_commit_hash(child) or ""
        config.set_pending_rebase_from(child, child_old_sha)
        try:
            _rebase_branch(git, child, parent, upstream=parent_old_sha or None)
        except RebaseConflictError as e:
            results.append(
                BranchRebaseResult(
                    branch=child, new_parent=parent, rebased=False, error=str(e)
                )
            )
            return results
        results.append(
            BranchRebaseResult(branch=child, new_parent=parent, rebased=True)
        )
        sub_results = rebase_subtree(git, config, child, child_old_sha)
        results.extend(sub_results)
        if any(not r.rebased for r in sub_results):
            return results
        config.clear_pending_rebase_from(child)
    return results
