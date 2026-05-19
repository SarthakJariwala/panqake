"""Command for moving a branch to a new parent (reparenting).

Updates stack metadata, optionally updates an open PR's base on GitHub, then
rebases the branch and all of its descendants onto the new parent. On a rebase
conflict, git is left mid-rebase and the branch's pre-rebase SHA is persisted
in `stacks.json` so the user can resolve, `git rebase --continue`, then run
`pq move --continue` to finish the chain with the same `--onto OLD_SHA`
semantics as the success path.
"""

from panqake.ports import (
    BranchNotFoundError,
    BranchRebaseResult,
    ConfigPort,
    GitHubPort,
    GitOperationError,
    GitPort,
    JsonUI,
    MoveContinueResult,
    MoveResult,
    PRBaseUpdateError,
    PRBaseUpdateResult,
    RealConfig,
    RealGit,
    RealGitHub,
    RealUI,
    RebaseConflictError,
    UIPort,
    emit_json_success,
    run_command,
)
from panqake.utils.questionary_prompt import format_branch
from panqake.utils.rebase import rebase_subtree
from panqake.utils.types import BranchName


def _collect_descendants(config: ConfigPort, branch: BranchName) -> set[BranchName]:
    """Return all branches in the subtree rooted at `branch` (excluding `branch`)."""
    descendants: set[BranchName] = set()
    to_visit = list(config.get_child_branches(branch))
    while to_visit:
        current = to_visit.pop()
        if current in descendants:
            continue
        descendants.add(current)
        to_visit.extend(config.get_child_branches(current))
    return descendants


def _would_create_cycle(
    config: ConfigPort, branch: BranchName, new_parent: BranchName
) -> bool:
    """Check whether reparenting `branch` to `new_parent` would create a cycle."""
    if new_parent == branch:
        return True
    return new_parent in _collect_descendants(config, branch)


def move_branch_core(
    git: GitPort,
    github: GitHubPort,
    config: ConfigPort,
    ui: UIPort,
    branch_name: BranchName | None = None,
    new_parent: BranchName | None = None,
) -> MoveResult:
    """Move a branch to a new parent, rebasing its subtree onto the new tip.

    Pure core logic — instantiate ports and call from a wrapper.
    """
    if not branch_name:
        branch_name = git.get_current_branch()
        if not branch_name:
            raise BranchNotFoundError("Could not determine the current branch")

    git.validate_branch(branch_name)

    if not config.branch_exists(branch_name):
        raise BranchNotFoundError(
            f"Branch '{branch_name}' is not tracked by panqake. "
            f"Run `pq track {branch_name}` first."
        )

    old_parent = config.get_parent_branch(branch_name)
    if not old_parent:
        raise GitOperationError(
            f"Cannot move root branch '{branch_name}': it has no parent."
        )

    # Validate the tracked parent actually exists in git. If it doesn't (e.g.,
    # the parent was deleted or renamed outside panqake), the `--onto OLD_PARENT`
    # form of git rebase would fail with an opaque "invalid upstream" error
    # that gets surfaced as a misleading conflict — fail early instead.
    if not git.branch_exists(old_parent):
        raise BranchNotFoundError(
            f"Tracked parent '{old_parent}' of branch '{branch_name}' does not "
            f"exist in git. The stack metadata is stale; retrack '{branch_name}' "
            f"with `pq track {branch_name}` against an existing parent first."
        )

    if not new_parent:
        excluded = _collect_descendants(config, branch_name) | {branch_name}
        candidates = [b for b in git.list_all_branches() if b not in excluded]
        selected = ui.prompt_select_branch(
            candidates,
            f"Select new parent for '{branch_name}':",
            current_branch=branch_name,
            enable_search=True,
        )
        if not selected:
            from panqake.ports import UserCancelledError

            raise UserCancelledError()
        new_parent = selected

    git.validate_branch(new_parent)

    if _would_create_cycle(config, branch_name, new_parent):
        raise GitOperationError(
            f"Cannot move '{branch_name}' onto '{new_parent}': "
            f"would create a cycle (new parent is a descendant of the branch)."
        )

    warnings: list[str] = []

    if new_parent == old_parent:
        ui.print_info(
            f"Branch {format_branch(branch_name)} is already parented to "
            f"{format_branch(new_parent)}; nothing to do."
        )
        return MoveResult(
            branch=branch_name,
            old_parent=old_parent,
            new_parent=new_parent,
            rebases=[],
            pr_base_update=None,
            returned_to=git.get_current_branch(),
            warnings=warnings,
            no_op=True,
        )

    original_branch = git.get_current_branch()
    branch_old_sha = git.get_commit_hash(branch_name) or ""

    # Update stack metadata first so a mid-rebase abort still leaves a consistent
    # view of the graph for the user to recover via `pq move --continue`.
    config.add_to_stack(branch_name, new_parent, config.get_worktree_path(branch_name))

    # Persist the pre-rebase SHA before any rebase that could conflict. If the
    # rebase fails, descendants are still based on this SHA and `pq move
    # --continue` will use it as the `--onto` upstream so commits from the
    # old parent's history don't get replayed into descendants.
    config.set_pending_rebase_from(branch_name, branch_old_sha)

    pr_base_update: PRBaseUpdateResult | None = None
    if github.is_cli_installed():
        if github.branch_has_pr(branch_name):
            try:
                github.update_pr_base(branch_name, new_parent)
                pr_base_update = PRBaseUpdateResult(
                    branch=branch_name,
                    new_base=new_parent,
                    had_pr=True,
                    updated=True,
                )
            except PRBaseUpdateError as e:
                pr_base_update = PRBaseUpdateResult(
                    branch=branch_name,
                    new_base=new_parent,
                    had_pr=True,
                    updated=False,
                    error=str(e),
                )
                warnings.append(f"Failed to update PR base for '{branch_name}': {e}")
    else:
        warnings.append(
            "GitHub CLI not installed; skipping PR base update. "
            "Update the PR base manually if needed."
        )

    rebases: list[BranchRebaseResult] = []
    try:
        if git.is_branch_worktree(branch_name):
            git.rebase_onto_in_worktree(
                branch_name, new_parent, abort_on_conflict=False, upstream=old_parent
            )
        else:
            git.rebase_onto(
                branch_name, new_parent, abort_on_conflict=False, upstream=old_parent
            )
    except RebaseConflictError as e:
        # Conflict left in place; metadata + PR base reflect the new parent and
        # pending_rebase_from is persisted so `pq move --continue` can resume
        # with the same --onto OLD_SHA semantics as the success path.
        rebases.append(
            BranchRebaseResult(
                branch=branch_name,
                new_parent=new_parent,
                rebased=False,
                error=str(e),
            )
        )
        return MoveResult(
            branch=branch_name,
            old_parent=old_parent,
            new_parent=new_parent,
            rebases=rebases,
            pr_base_update=pr_base_update,
            returned_to=None,
            warnings=warnings,
        )
    except Exception:
        # Non-conflict failure (e.g., checkout failed before rebase started).
        # Roll back metadata + PR base so the user isn't left with a stack
        # that points to a parent the branch was never actually rebased onto.
        config.clear_pending_rebase_from(branch_name)
        config.add_to_stack(
            branch_name, old_parent, config.get_worktree_path(branch_name)
        )
        if pr_base_update and pr_base_update.updated:
            try:
                github.update_pr_base(branch_name, old_parent)
            except PRBaseUpdateError:
                pass
        raise

    rebases.append(
        BranchRebaseResult(branch=branch_name, new_parent=new_parent, rebased=True)
    )
    rebases.extend(rebase_subtree(git, config, branch_name, branch_old_sha))

    had_conflict = any(not r.rebased for r in rebases)

    if not had_conflict:
        # Subtree rebased successfully — clear the moved branch's pending state.
        config.clear_pending_rebase_from(branch_name)

    returned_to: BranchName | None = None
    if not had_conflict and original_branch:
        current_now = git.get_current_branch()
        if current_now != original_branch and git.branch_exists(original_branch):
            try:
                git.checkout_branch(original_branch)
                returned_to = original_branch
            except Exception:
                pass

    return MoveResult(
        branch=branch_name,
        old_parent=old_parent,
        new_parent=new_parent,
        rebases=rebases,
        pr_base_update=pr_base_update,
        returned_to=returned_to,
        warnings=warnings,
    )


def move_branch(
    branch_name: BranchName | None = None,
    new_parent: BranchName | None = None,
    *,
    json_output: bool = False,
) -> None:
    """CLI entrypoint that wraps core logic with real implementations."""
    git = RealGit()
    github = RealGitHub()
    config = RealConfig()
    ui = JsonUI() if json_output else RealUI()

    def core() -> MoveResult:
        result = move_branch_core(
            git=git,
            github=github,
            config=config,
            ui=ui,
            branch_name=branch_name,
            new_parent=new_parent,
        )

        if not json_output and not result.no_op:
            for warning in result.warnings:
                ui.print_error(f"Warning: {warning}")

            failed = [r for r in result.rebases if not r.rebased]
            if failed:
                conflicted = failed[0]
                ui.print_error(
                    f"Rebase conflict on {format_branch(conflicted.branch)}: "
                    f"{conflicted.error or 'unknown error'}"
                )
                ui.print_info(
                    "The stack metadata has been updated, but git is mid-rebase. "
                    "Resolve the conflicts, run `git rebase --continue`, then "
                    "`pq move --continue` to finish rebasing any remaining "
                    "descendants of the moved subtree."
                )
            else:
                ui.print_success(
                    f"Moved {format_branch(result.branch)} → "
                    f"{format_branch(result.new_parent)}"
                )
                rebased_branches = [r.branch for r in result.rebases if r.rebased]
                if len(rebased_branches) > 1:
                    ui.print_info(
                        f"Rebased {len(rebased_branches) - 1} descendant branch(es)."
                    )
                if result.pr_base_update and result.pr_base_update.updated:
                    ui.print_info(
                        f"Updated PR base for {format_branch(result.branch)} → "
                        f"{format_branch(result.new_parent)}"
                    )
                if len(rebased_branches) == 1:
                    ui.print_info(
                        f"Force-push the rewritten branch with: "
                        f"`pq submit {rebased_branches[0]}`"
                    )
                else:
                    ui.print_info("Force-push the rewritten branches with:")
                    for b in rebased_branches:
                        ui.print_info(f"  pq submit {b}")
        return result

    result = run_command(ui, core, json_output=json_output, command="move")
    if json_output and result is not None:
        emit_json_success("move", result)


def _find_resume_root(
    config: ConfigPort, pending: list[BranchName]
) -> BranchName | None:
    """Pick the topmost branch with pending_rebase_from set.

    A branch is the resume root iff none of its tracked ancestors are also
    in the pending set, so we always resume from the highest affected
    branch first (and recursion handles its descendants).
    """
    pending_set = set(pending)
    for branch in pending:
        current = config.get_parent_branch(branch)
        is_root = True
        while current:
            if current in pending_set:
                is_root = False
                break
            current = config.get_parent_branch(current)
        if is_root:
            return branch
    return None


def move_continue_core(
    git: GitPort,
    config: ConfigPort,
    ui: UIPort,
) -> MoveContinueResult:
    """Resume a previously conflicted `pq move`.

    Picks up where the original move left off using the persisted
    `pending_rebase_from` SHAs so descendants are reattached with the
    same `--onto OLD_SHA` semantics the success path uses.
    """
    if git.is_rebase_in_progress():
        raise GitOperationError(
            "Git is still mid-rebase. Run `git rebase --continue` or "
            "`git rebase --abort` first, then re-run `pq move --continue`."
        )

    pending = config.get_branches_with_pending_rebase()
    if not pending:
        ui.print_info("No move in progress; nothing to continue.")
        return MoveContinueResult(
            resumed_branch=None,
            rebases=[],
            returned_to=git.get_current_branch(),
            no_op=True,
        )

    resume_root = _find_resume_root(config, pending)
    if resume_root is None:
        # Should be unreachable given pending is non-empty, but guard anyway.
        raise GitOperationError(
            "Found pending rebase state but could not determine a resume root."
        )

    old_sha = config.get_pending_rebase_from(resume_root) or ""
    current_sha = git.get_commit_hash(resume_root)
    if not current_sha:
        raise GitOperationError(
            f"Branch '{resume_root}' does not have a commit hash; cannot resume."
        )
    if current_sha == old_sha:
        raise GitOperationError(
            f"Branch '{resume_root}' is still at its pre-move SHA — the "
            "original rebase was not completed. Run `git rebase --continue` "
            "to finish it before re-running `pq move --continue`."
        )

    original_branch = git.get_current_branch()
    # The resume root itself was rewritten by `git rebase --continue` and
    # needs to be force-pushed. Surface it in the result so callers (CLI
    # and JSON consumers) include it in `pq submit` instructions.
    resume_root_parent = config.get_parent_branch(resume_root) or ""
    rebases: list[BranchRebaseResult] = [
        BranchRebaseResult(
            branch=resume_root,
            new_parent=resume_root_parent,
            rebased=True,
        )
    ]
    rebases.extend(rebase_subtree(git, config, resume_root, old_sha))
    had_conflict = any(not r.rebased for r in rebases)

    if not had_conflict:
        config.clear_pending_rebase_from(resume_root)

    returned_to: BranchName | None = None
    if not had_conflict and original_branch and git.branch_exists(original_branch):
        try:
            git.checkout_branch(original_branch)
            returned_to = original_branch
        except Exception:
            pass

    return MoveContinueResult(
        resumed_branch=resume_root,
        rebases=rebases,
        returned_to=returned_to,
    )


def move_continue(*, json_output: bool = False) -> None:
    """CLI entrypoint to resume a conflicted move."""
    git = RealGit()
    config = RealConfig()
    ui = JsonUI() if json_output else RealUI()

    def core() -> MoveContinueResult:
        result = move_continue_core(git=git, config=config, ui=ui)

        if not json_output and not result.no_op:
            failed = [r for r in result.rebases if not r.rebased]
            if failed:
                conflicted = failed[0]
                ui.print_error(
                    f"Rebase conflict on {format_branch(conflicted.branch)}: "
                    f"{conflicted.error or 'unknown error'}"
                )
                ui.print_info(
                    "Resolve the conflicts, run `git rebase --continue`, then "
                    "`pq move --continue` again to finish rebasing the "
                    "remaining descendants."
                )
            else:
                rebased = [r.branch for r in result.rebases if r.rebased]
                descendant_count = max(len(rebased) - 1, 0)
                if descendant_count:
                    ui.print_success(
                        f"Resumed move from {format_branch(result.resumed_branch)}; "
                        f"rebased {descendant_count} descendant branch(es)."
                    )
                else:
                    ui.print_success(
                        f"Resumed move from "
                        f"{format_branch(result.resumed_branch)}; "
                        "no descendants needed rebasing."
                    )
                if rebased:
                    ui.print_info("Force-push the rewritten branches with:")
                    for b in rebased:
                        ui.print_info(f"  pq submit {b}")
        return result

    result = run_command(ui, core, json_output=json_output, command="move-continue")
    if json_output and result is not None:
        emit_json_success("move-continue", result)
