"""Command for merging PRs and managing branches after merge.

Uses dependency injection for testability.
Core logic is pure - no sys.exit, no direct filesystem/git calls.
"""

from panqake.ports import (
    ChildUpdateResult,
    ConfigPort,
    GitHubCLINotFoundError,
    GitHubPort,
    GitPort,
    MergeMethod,
    MergeResult,
    PRBaseUpdateError,
    PRBaseUpdateResult,
    PRMergeError,
    RealConfig,
    RealGit,
    RealGitHub,
    RealUI,
    RebaseConflictError,
    UIPort,
    run_command,
)
from panqake.utils.questionary_prompt import format_branch
from panqake.utils.selection import select_from_options
from panqake.utils.types import BranchName


def update_pr_base_for_direct_children(
    branch: BranchName,
    new_base: BranchName,
    config: ConfigPort,
    github: GitHubPort,
) -> list[PRBaseUpdateResult]:
    """Update PR base references for direct child branches.

    Must be done before deleting the parent branch to avoid closing child PRs.
    """
    results: list[PRBaseUpdateResult] = []
    children = config.get_child_branches(branch)

    for child in children:
        had_pr = github.branch_has_pr(child)
        if not had_pr:
            results.append(
                PRBaseUpdateResult(
                    branch=child,
                    new_base=new_base,
                    had_pr=False,
                    updated=False,
                )
            )
            continue

        try:
            github.update_pr_base(child, new_base)
            results.append(
                PRBaseUpdateResult(
                    branch=child,
                    new_base=new_base,
                    had_pr=True,
                    updated=True,
                )
            )
        except PRBaseUpdateError as e:
            results.append(
                PRBaseUpdateResult(
                    branch=child,
                    new_base=new_base,
                    had_pr=True,
                    updated=False,
                    error=str(e),
                )
            )

    return results


def update_child_branches_core(
    merged_branch: BranchName,
    new_parent: BranchName,
    git: GitPort,
    config: ConfigPort,
) -> list[ChildUpdateResult]:
    """Update child branches after a parent branch has been merged.

    Rebases direct children onto the new parent, then recursively updates grandchildren.
    Stops on first conflict.
    """
    results: list[ChildUpdateResult] = []
    children = config.get_child_branches(merged_branch)

    for child in children:
        config.add_to_stack(child, new_parent)

        try:
            git.rebase_onto(child, new_parent, abort_on_conflict=True)
            results.append(
                ChildUpdateResult(
                    branch=child,
                    new_parent=new_parent,
                    rebased=True,
                )
            )

            grandchild_results = update_child_branches_core(
                merged_branch=child,
                new_parent=child,
                git=git,
                config=config,
            )
            results.extend(grandchild_results)

        except RebaseConflictError as e:
            results.append(
                ChildUpdateResult(
                    branch=child,
                    new_parent=new_parent,
                    rebased=False,
                    error=str(e),
                )
            )
            break

    return results


def cleanup_local_branch_core(
    branch: BranchName,
    parent_branch: BranchName,
    git: GitPort,
    config: ConfigPort,
) -> tuple[bool, bool, list[str]]:
    """Delete the local branch after successful merge.

    Returns:
        Tuple of (local_deleted, removed_from_stack, warnings)
    """
    warnings: list[str] = []
    local_deleted = False
    removed_from_stack = False

    if not git.branch_exists(branch):
        return True, True, warnings

    worktree_path = config.get_worktree_path(branch)
    if worktree_path:
        try:
            git.remove_worktree(worktree_path, force=True)
            config.set_worktree_path(branch, "")
        except Exception as e:
            warnings.append(f"Failed to remove worktree at '{worktree_path}': {e}")
            return False, False, warnings

    current = git.get_current_branch()
    if current == branch:
        try:
            git.checkout_branch(parent_branch)
        except Exception as e:
            warnings.append(f"Failed to checkout {parent_branch}: {e}")
            return False, False, warnings

    try:
        git.delete_local_branch(branch, force=True)
        local_deleted = True
    except Exception as e:
        warnings.append(f"Failed to delete local branch '{branch}': {e}")

    if local_deleted:
        removed_from_stack = config.remove_from_stack(branch)

    return local_deleted, removed_from_stack, warnings


def merge_branch_core(
    git: GitPort,
    github: GitHubPort,
    config: ConfigPort,
    ui: UIPort,
    branch_name: BranchName | None = None,
    merge_method: MergeMethod = "squash",
    delete_branch: bool = True,
    update_children: bool = True,
) -> MergeResult:
    """Merge a PR and manage the branch stack after merge.

    This is the pure core logic that can be tested without mocking.

    Args:
        git: Git operations interface
        github: GitHub CLI operations interface
        config: Stack configuration interface
        ui: User interaction interface
        branch_name: Target branch (uses current branch if None)
        merge_method: The merge method (squash, rebase, or merge)
        delete_branch: Whether to delete the branch after merge
        update_children: Whether to update child branches

    Returns:
        MergeResult with details of the merge operation

    Raises:
        GitHubCLINotFoundError: If GitHub CLI is not installed
        BranchNotFoundError: If branch doesn't exist
        PRMergeError: If merge fails
        UserCancelledError: If user cancels
    """
    if not github.is_cli_installed():
        raise GitHubCLINotFoundError(
            "GitHub CLI (gh) is required but not installed. "
            "Please install GitHub CLI: https://cli.github.com"
        )

    if not branch_name:
        branch_name = git.get_current_branch()
        if not branch_name:
            from panqake.ports import BranchNotFoundError

            raise BranchNotFoundError("Could not determine current branch")

    git.validate_branch(branch_name)
    original_branch = git.get_current_branch()

    parent_branch = config.get_parent_branch(branch_name)
    if not parent_branch:
        parent_branch = "main"

    warnings: list[str] = []
    pr_base_updates: list[PRBaseUpdateResult] = []
    child_updates: list[ChildUpdateResult] = []
    remote_deleted = False
    local_deleted = False
    removed_from_stack = False
    returned_to: BranchName | None = None

    try:
        git.fetch_from_remote()

        if not github.branch_has_pr(branch_name):
            raise PRMergeError(f"Branch '{branch_name}' does not have an open PR")

        checks_passed, failed_checks = github.get_pr_checks_status(branch_name)
        if not checks_passed:
            ui.print_error("Not all required checks have passed for this PR.")
            ui.print_error("Failed checks:")
            for check in failed_checks:
                ui.print_error(f"  - {check}")
            if not ui.prompt_confirm("Do you want to proceed with the merge anyway?"):
                from panqake.ports import UserCancelledError

                raise UserCancelledError()

        if update_children:
            pr_base_updates = update_pr_base_for_direct_children(
                branch_name, parent_branch, config, github
            )
            for result in pr_base_updates:
                if result.error:
                    warnings.append(
                        f"Failed to update PR base for '{result.branch}': {result.error}"
                    )

        ui.print_info(
            f"Merging PR: {format_branch(parent_branch)} ← {format_branch(branch_name)}"
        )
        github.merge_pr(branch_name, merge_method)
        ui.print_success("PR merged successfully")

        if delete_branch:
            try:
                git.delete_remote_branch(branch_name)
                remote_deleted = True
                ui.print_success(f"Remote branch '{branch_name}' deleted")
            except Exception as e:
                warnings.append(f"Failed to delete remote branch: {e}")

        if update_children:
            child_updates = update_child_branches_core(
                branch_name, parent_branch, git, config
            )
            for result in child_updates:
                if result.rebased:
                    ui.print_success(f"Updated {format_branch(result.branch)}")
                else:
                    warnings.append(
                        f"Failed to update '{result.branch}': {result.error}"
                    )

        if delete_branch:
            local_deleted, removed_from_stack, cleanup_warnings = (
                cleanup_local_branch_core(branch_name, parent_branch, git, config)
            )
            warnings.extend(cleanup_warnings)
            if local_deleted:
                ui.print_success(f"Local branch '{branch_name}' deleted")

    finally:
        if original_branch and original_branch != branch_name:
            if git.branch_exists(original_branch):
                try:
                    git.checkout_branch(original_branch)
                    returned_to = original_branch
                except Exception:
                    pass

        if not returned_to:
            try:
                git.checkout_branch(parent_branch)
                returned_to = parent_branch
            except Exception:
                pass

    if warnings:
        for warning in warnings:
            ui.print_error(f"Warning: {warning}")

    return MergeResult(
        branch=branch_name,
        parent_branch=parent_branch,
        original_branch=original_branch,
        merge_method=merge_method,
        checks_passed=checks_passed,
        failed_checks=failed_checks,
        pr_base_updates=pr_base_updates,
        child_updates=child_updates,
        remote_branch_deleted=remote_deleted,
        local_branch_deleted=local_deleted,
        removed_from_stack=removed_from_stack,
        returned_to=returned_to,
        warnings=warnings,
    )


def get_merge_method() -> MergeMethod:
    """Get the merge method from user selection."""
    merge_methods = ["squash", "rebase", "merge"]
    result = select_from_options(
        merge_methods, "Select merge method:", default="squash"
    )
    if result in ("squash", "rebase", "merge"):
        return result  # type: ignore[return-value]
    return "squash"


def merge_branch(
    branch_name: BranchName | None = None,
    delete_branch: bool = True,
    update_children: bool = True,
) -> None:
    """CLI entrypoint that wraps core logic with real implementations.

    This thin wrapper:
    1. Instantiates real dependencies
    2. Prompts for merge method
    3. Calls the core logic
    4. Handles printing output
    5. Converts exceptions to sys.exit via run_command
    """
    git = RealGit()
    github = RealGitHub()
    config = RealConfig()
    ui = RealUI()

    def core() -> None:
        # Resolve branch name
        resolved_branch = branch_name
        if not resolved_branch:
            resolved_branch = git.get_current_branch()
            if not resolved_branch:
                from panqake.ports import BranchNotFoundError

                raise BranchNotFoundError("Could not determine current branch")

        parent_branch = config.get_parent_branch(resolved_branch)
        if not parent_branch:
            parent_branch = "main"

        ui.print_info(
            f"Preparing to merge PR: {format_branch(parent_branch)} ← {format_branch(resolved_branch)}"
        )

        merge_method = get_merge_method()

        if not ui.prompt_confirm("Do you want to proceed with the merge?"):
            ui.print_info("Merge cancelled.")
            return

        result = merge_branch_core(
            git=git,
            github=github,
            config=config,
            ui=ui,
            branch_name=resolved_branch,
            merge_method=merge_method,
            delete_branch=delete_branch,
            update_children=update_children,
        )

        ui.print_success("Merge and branch management completed.")

        if result.child_updates:
            updated = [r for r in result.child_updates if r.rebased]
            failed = [r for r in result.child_updates if not r.rebased]
            if updated:
                ui.print_info(f"Updated {len(updated)} child branch(es)")
            if failed:
                ui.print_error(f"Failed to update {len(failed)} child branch(es)")
                ui.print_info("You may need to resolve conflicts manually.")

    run_command(ui, core)
