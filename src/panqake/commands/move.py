"""Command for moving a branch to a new parent (reparenting).

Updates stack metadata, optionally updates an open PR's base on GitHub, then
rebases the branch and all of its descendants onto the new parent. On a rebase
conflict, git is left mid-rebase so the user can resolve and continue manually
with `git rebase --continue`, then run `pq update` to finish the chain.
"""

from panqake.ports import (
    BranchNotFoundError,
    BranchRebaseResult,
    ConfigPort,
    GitHubPort,
    GitOperationError,
    GitPort,
    JsonUI,
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
from panqake.utils.types import BranchName


def _rebase_branch(
    git: GitPort,
    config: ConfigPort,
    branch: BranchName,
    new_base: BranchName,
    upstream: BranchName | None,
) -> None:
    """Rebase a branch onto a new base, picking worktree-aware variant when needed."""
    if config.get_worktree_path(branch):
        git.rebase_onto_in_worktree(
            branch, new_base, abort_on_conflict=False, upstream=upstream
        )
    else:
        git.rebase_onto(branch, new_base, abort_on_conflict=False, upstream=upstream)


def _rebase_descendants(
    git: GitPort,
    config: ConfigPort,
    parent: BranchName,
    parent_old_sha: BranchName | None,
) -> list[BranchRebaseResult]:
    """Recursively rebase descendants after their parent has been rewritten.

    For each child of `parent`, replays commits in (parent_old_sha..child] onto
    the new tip of `parent`. Stops on the first conflict — including conflicts
    raised deeper in the subtree, so we don't leave git mid-rebase while
    attempting to checkout the next sibling.
    """
    results: list[BranchRebaseResult] = []
    for child in config.get_child_branches(parent):
        child_old_sha = git.get_commit_hash(child)
        try:
            _rebase_branch(git, config, child, parent, upstream=parent_old_sha)
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
        sub_results = _rebase_descendants(git, config, child, child_old_sha)
        results.extend(sub_results)
        if any(not r.rebased for r in sub_results):
            return results
    return results


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
    branch_old_sha = git.get_commit_hash(branch_name)

    # Update stack metadata first so a mid-rebase abort still leaves a consistent
    # view of the graph for the user to recover via `pq update`.
    config.add_to_stack(branch_name, new_parent, config.get_worktree_path(branch_name))

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
        _rebase_branch(git, config, branch_name, new_parent, upstream=old_parent)
    except RebaseConflictError as e:
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

    rebases.append(
        BranchRebaseResult(branch=branch_name, new_parent=new_parent, rebased=True)
    )
    rebases.extend(_rebase_descendants(git, config, branch_name, branch_old_sha))

    had_conflict = any(not r.rebased for r in rebases)

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
                    "`pq update` to finish rebasing any remaining descendants."
                )
            else:
                ui.print_success(
                    f"Moved {format_branch(result.branch)} → "
                    f"{format_branch(result.new_parent)}"
                )
                rebased_count = sum(1 for r in result.rebases if r.rebased)
                if rebased_count > 1:
                    ui.print_info(f"Rebased {rebased_count - 1} descendant branch(es).")
                if result.pr_base_update and result.pr_base_update.updated:
                    ui.print_info(
                        f"Updated PR base for {format_branch(result.branch)} → "
                        f"{format_branch(result.new_parent)}"
                    )
                ui.print_info("Run `pq submit` to force-push the rewritten branches.")
        return result

    result = run_command(ui, core, json_output=json_output, command="move")
    if json_output and result is not None:
        emit_json_success("move", result)
