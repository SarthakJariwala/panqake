"""Command for deleting a branch and relinking the stack."""

from panqake.ports import (
    BranchNotFoundError,
    CannotDeleteCurrentBranchError,
    ConfigPort,
    DeleteResult,
    GitOperationError,
    GitPort,
    InWorktreeBeingDeletedError,
    RealConfig,
    RealGit,
    RealUI,
    UIPort,
    UserCancelledError,
    run_command,
)
from panqake.utils.types import BranchName


def delete_branch_core(
    git: GitPort,
    config: ConfigPort,
    ui: UIPort,
    branch_name: BranchName | None = None,
    current_dir: str | None = None,
) -> DeleteResult:
    """Core logic for deleting a branch and relinking the stack.

    Args:
        git: Git operations port
        config: Stack configuration port
        ui: User interaction port
        branch_name: Branch to delete (prompts if None)
        current_dir: Current working directory (for worktree detection)

    Returns:
        DeleteResult with deletion details

    Raises:
        BranchNotFoundError: If branch doesn't exist
        CannotDeleteCurrentBranchError: If trying to delete current branch
        InWorktreeBeingDeletedError: If in the worktree being deleted
        RebaseConflictError: If rebase conflicts during child relinking
        UserCancelledError: If user cancels the operation
    """
    current_branch = git.get_current_branch()
    if not current_branch:
        raise GitOperationError("Could not determine current branch")

    if not branch_name:
        branches = git.list_all_branches()
        eligible = [b for b in branches if b != current_branch]
        eligible = [b for b in eligible if b not in ("main", "master")]
        if not eligible:
            return DeleteResult(
                deleted_branch=None,
                parent_branch=None,
                relinked_children=[],
                worktree_removed=False,
                removed_from_stack=False,
                status="skipped",
                skip_reason="no_eligible_branches",
            )
        selected = ui.prompt_select_branch(
            branches,
            "Select branch to delete:",
            current_branch=current_branch,
            exclude_protected=True,
            enable_search=True,
        )
        if not selected:
            raise UserCancelledError()
        branch_name = selected

    git.validate_branch(branch_name)

    if branch_name == current_branch:
        raise CannotDeleteCurrentBranchError(
            "Cannot delete the current branch. Please checkout another branch first."
        )

    parent_branch = config.get_parent_branch(branch_name)
    child_branches = config.get_child_branches(branch_name)

    if parent_branch and not git.branch_exists(parent_branch):
        raise BranchNotFoundError(f"Parent branch '{parent_branch}' does not exist")

    ui.print_info(f"Branch to delete: {branch_name}")
    if parent_branch:
        ui.print_info(f"Parent branch: {parent_branch}")
    if child_branches:
        ui.print_info("Child branches that will be relinked:")
        for child in child_branches:
            ui.print_muted(f"  {child}")

    if not ui.prompt_confirm("Are you sure you want to delete this branch?"):
        raise UserCancelledError()

    worktree_path = config.get_worktree_path(branch_name)
    worktree_removed = False

    if worktree_path and current_dir:
        if current_dir.rstrip("/") == worktree_path.rstrip("/"):
            git_worktree_path = git.get_worktree_path(branch_name)
            repo_root = git_worktree_path or ""
            raise InWorktreeBeingDeletedError(worktree_path, repo_root)

    relinked_children: list[BranchName] = []
    for child in child_branches:
        git.checkout_branch(child)
        if parent_branch:
            git.rebase_onto(child, parent_branch, abort_on_conflict=True)
            config.add_to_stack(child, parent_branch)
        relinked_children.append(child)

    if branch_name != current_branch:
        git.checkout_branch(current_branch)

    if worktree_path:
        try:
            git.remove_worktree(worktree_path, force=True)
            worktree_removed = True
        except Exception:
            pass
        config.set_worktree_path(branch_name, "")

    git.delete_local_branch(branch_name, force=True)

    removed_from_stack = config.remove_from_stack(branch_name)

    return DeleteResult(
        deleted_branch=branch_name,
        parent_branch=parent_branch,
        relinked_children=relinked_children,
        worktree_removed=worktree_removed,
        removed_from_stack=removed_from_stack,
        status="deleted",
    )


def delete_branch(branch_name: BranchName | None = None) -> None:
    """Delete a branch and relink the stack."""
    from pathlib import Path

    git = RealGit()
    config = RealConfig()
    ui = RealUI()
    current_dir = str(Path.cwd().resolve())

    def _run() -> DeleteResult:
        return delete_branch_core(git, config, ui, branch_name, current_dir)

    result = run_command(ui, _run)
    if result is None:
        return

    if result.status == "skipped":
        if result.skip_reason == "no_eligible_branches":
            ui.print_info("No branches available to delete.")
        return

    if result.removed_from_stack:
        ui.print_success(
            f"Deleted branch '{result.deleted_branch}' and relinked the stack"
        )
    else:
        ui.print_error(
            f"Branch '{result.deleted_branch}' was deleted but not found in stack metadata."
        )
