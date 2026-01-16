"""Command for syncing branches with remote repository changes.

Uses dependency injection for testability.
Core logic is pure - no sys.exit, no direct filesystem/git calls.
"""

from panqake.ports import (
    BranchNotFoundError,
    ConfigPort,
    GitOperationError,
    GitPort,
    RebaseConflictError,
    RealConfig,
    RealGit,
    RealUI,
    SyncResult,
    UIPort,
    run_command,
)
from panqake.utils.questionary_prompt import format_branch
from panqake.utils.types import BranchName


def fetch_and_pull_main_core(
    git: GitPort,
    ui: UIPort,
    main_branch: BranchName,
) -> str | None:
    """Fetch from remote and pull the main branch.

    Args:
        git: Git operations interface
        ui: User interaction interface
        main_branch: The main branch to pull

    Returns:
        The commit hash after pulling, or None on failure

    Raises:
        GitOperationError: If fetch or pull fails
    """
    git.fetch_from_remote()
    git.checkout_branch(main_branch)
    git.pull_branch(main_branch)

    commit_hash = git.get_commit_hash(main_branch)
    if commit_hash:
        ui.print_success(f"{main_branch} fast-forwarded to {commit_hash[:8]}")
    return commit_hash


def get_mergeable_branches_core(
    git: GitPort,
    config: ConfigPort,
    main_branch: BranchName,
) -> list[BranchName]:
    """Get branches that are merged into main and can be deleted.

    Only returns branches whose parent is main_branch.

    Args:
        git: Git operations interface
        config: Stack configuration interface
        main_branch: The main branch to check against

    Returns:
        List of branch names that can be deleted
    """
    merged_branches = git.get_merged_branches(main_branch)
    deletable: list[BranchName] = []

    for branch in merged_branches:
        parent = config.get_parent_branch(branch)
        if parent == main_branch:
            deletable.append(branch)

    return deletable


def handle_merged_branches_core(
    git: GitPort,
    config: ConfigPort,
    ui: UIPort,
    main_branch: BranchName,
) -> list[BranchName]:
    """Handle merged branches by prompting user for deletion.

    Args:
        git: Git operations interface
        config: Stack configuration interface
        ui: User interaction interface
        main_branch: The main branch to check against

    Returns:
        List of branch names that were deleted

    Raises:
        UserCancelledError: If user cancels a confirmation prompt
    """
    branches_to_delete = get_mergeable_branches_core(git, config, main_branch)
    deleted_branches: list[BranchName] = []

    for branch in branches_to_delete:
        if ui.prompt_confirm(
            f"{format_branch(branch)} is merged into {main_branch}. Delete it?"
        ):
            git.delete_local_branch(branch, force=True)
            removed = config.remove_from_stack(branch)
            if not removed:
                ui.print_info(f"Branch {branch} not found in stack metadata")
            deleted_branches.append(branch)
            ui.print_success(f"Deleted branch {branch}")

    return deleted_branches


def update_branch_with_conflict_detection_core(
    git: GitPort,
    branch: BranchName,
    parent: BranchName,
) -> tuple[bool, str | None]:
    """Update a single branch by rebasing onto its parent.

    Args:
        git: Git operations interface
        branch: The branch to update
        parent: The parent branch to rebase onto

    Returns:
        Tuple of (success, error_message)
    """
    try:
        if git.is_branch_worktree(branch):
            git.rebase_onto_in_worktree(branch, parent, abort_on_conflict=True)
        else:
            git.rebase_onto(branch, parent, abort_on_conflict=True)
        return True, None
    except RebaseConflictError as e:
        return False, str(e)


def update_all_branches_core(
    git: GitPort,
    config: ConfigPort,
    ui: UIPort,
    main_branch: BranchName,
) -> tuple[list[BranchName], list[BranchName]]:
    """Update all child branches in the stack.

    Args:
        git: Git operations interface
        config: Stack configuration interface
        ui: User interaction interface
        main_branch: Starting branch to update children from

    Returns:
        Tuple of (updated_branches, conflict_branches)
    """
    updated_branches: list[BranchName] = []
    conflict_branches: list[BranchName] = []

    # Build list of all branches to update with their parents (depth-first)
    branches_to_process: list[tuple[BranchName, BranchName | None]] = [
        (main_branch, None)
    ]
    all_branches_to_update: list[tuple[BranchName, BranchName]] = []

    while branches_to_process:
        current, parent = branches_to_process.pop(0)

        if parent is not None:
            all_branches_to_update.append((current, parent))

        children = config.get_child_branches(current)
        for child in children:
            branches_to_process.append((child, current))

    # Process all branches in order
    for child, parent in all_branches_to_update:
        # Skip branches whose parents had conflicts
        if parent in conflict_branches:
            ui.print_error(
                f"Skipping {format_branch(child)} as its parent "
                f"{format_branch(parent)} had conflicts"
            )
            conflict_branches.append(child)
            continue

        success, error_msg = update_branch_with_conflict_detection_core(
            git, child, parent
        )

        if success:
            ui.print_success(
                f"Updated {format_branch(child)} on {format_branch(parent)}"
            )
            updated_branches.append(child)
        else:
            ui.print_error(f"{error_msg}")
            ui.print_error(
                f"Run 'pq update {child}' after resolving conflicts "
                "to continue updating the stack"
            )
            conflict_branches.append(child)

    return updated_branches, conflict_branches


def push_updated_branches_core(
    git: GitPort,
    ui: UIPort,
    updated_branches: list[BranchName],
) -> tuple[list[BranchName], list[BranchName]]:
    """Push successfully updated branches to remote.

    Args:
        git: Git operations interface
        ui: User interaction interface
        updated_branches: List of branch names to push

    Returns:
        Tuple of (pushed_branches, skipped_branches)
    """
    if not updated_branches:
        return [], []

    pushed_branches: list[BranchName] = []
    skipped_branches: list[BranchName] = []

    for branch in updated_branches:
        # Skip branches that don't exist on remote yet
        if not git.is_branch_pushed_to_remote(branch):
            ui.print_info(
                f"Skipping push for {format_branch(branch)} "
                "as it doesn't exist on remote yet"
            )
            skipped_branches.append(branch)
            continue

        # Check if the branch has unpushed changes
        if not git.has_unpushed_changes(branch):
            ui.print_info(
                f"Skipping push for {format_branch(branch)} "
                "as it's already in sync with remote"
            )
            skipped_branches.append(branch)
            continue

        # For worktree branches, verify they're on the correct branch
        if git.is_branch_worktree(branch):
            skipped_branches.append(branch)
            continue

        try:
            git.checkout_branch(branch)
            git.push_branch(branch, force_with_lease=True)
            pushed_branches.append(branch)
            ui.print_success(f"Branch {format_branch(branch)} pushed to remote")
        except GitOperationError as e:
            ui.print_error(f"Failed to push branch '{branch}': {e}")
            skipped_branches.append(branch)

    return pushed_branches, skipped_branches


def return_to_branch_core(
    git: GitPort,
    ui: UIPort,
    target_branch: BranchName,
    fallback_branch: BranchName,
    deleted_branches: list[BranchName],
) -> BranchName | None:
    """Return to the target branch or fallback if target was deleted.

    Args:
        git: Git operations interface
        ui: User interaction interface
        target_branch: The branch to return to
        fallback_branch: The fallback branch if target doesn't exist
        deleted_branches: List of branches that were deleted

    Returns:
        The branch that was switched to, or None if switch failed
    """
    if git.branch_exists(target_branch) and target_branch not in deleted_branches:
        try:
            git.checkout_branch(target_branch)
            return target_branch
        except GitOperationError:
            pass

    if git.branch_exists(fallback_branch):
        ui.print_info(
            f"Branch {format_branch(target_branch)} no longer exists, "
            f"returning to {format_branch(fallback_branch)}"
        )
        try:
            git.checkout_branch(fallback_branch)
            return fallback_branch
        except GitOperationError:
            pass

    ui.print_error("Unable to find a valid branch to return to")
    return None


def sync_core(
    git: GitPort,
    config: ConfigPort,
    ui: UIPort,
    main_branch: BranchName = "main",
    skip_push: bool = False,
) -> SyncResult:
    """Sync local branches with remote repository changes.

    This is the pure core logic that can be tested without mocking.

    Args:
        git: Git operations interface
        config: Stack configuration interface
        ui: User interaction interface
        main_branch: Base branch to sync with (default: main)
        skip_push: If True, don't push changes to remote after updating

    Returns:
        SyncResult with details of the sync operation

    Raises:
        BranchNotFoundError: If current branch cannot be determined
        GitOperationError: If git operations fail
        UserCancelledError: If user cancels a prompt
    """
    # 1. Save current branch
    original_branch = git.get_current_branch()
    if not original_branch:
        raise BranchNotFoundError("Could not determine current branch")

    deleted_branches: list[BranchName] = []
    updated_branches: list[BranchName] = []
    conflict_branches: list[BranchName] = []
    pushed_branches: list[BranchName] = []
    skipped_push_branches: list[BranchName] = []
    returned_to: BranchName | None = None

    try:
        # 2. Fetch & pull from remote
        fetch_and_pull_main_core(git, ui, main_branch)

        # 3. Handle merged branches
        deleted_branches = handle_merged_branches_core(git, config, ui, main_branch)

        # 4. Update child branches with conflict handling
        children = config.get_child_branches(main_branch)
        if children:
            updated_branches, conflict_branches = update_all_branches_core(
                git, config, ui, main_branch
            )

            if conflict_branches:
                ui.print_error("All branches updated cleanly, except for:")
                for branch in conflict_branches:
                    ui.print_error(f"▸ {branch}")
                ui.print_info("You can fix these conflicts with panqake update.")

        # 5. Push to remote if requested
        if not skip_push and updated_branches:
            pushed_branches, skipped_push_branches = push_updated_branches_core(
                git, ui, updated_branches
            )

    finally:
        # 6. Return to original branch or fallback to main if it was deleted
        returned_to = return_to_branch_core(
            git, ui, original_branch, main_branch, deleted_branches
        )

    # 7. Report success
    if skip_push:
        ui.print_success("Sync completed successfully (local only)")
    else:
        ui.print_success("Sync completed successfully")

    return SyncResult(
        main_branch=main_branch,
        original_branch=original_branch,
        returned_to=returned_to,
        deleted_branches=deleted_branches,
        updated_branches=updated_branches,
        conflict_branches=conflict_branches,
        pushed_branches=pushed_branches,
        skipped_push_branches=skipped_push_branches,
        skip_push=skip_push,
    )


def sync_with_remote(main_branch: str = "main", skip_push: bool = False) -> None:
    """CLI entrypoint that wraps core logic with real implementations.

    This thin wrapper:
    1. Instantiates real dependencies
    2. Calls the core logic
    3. Handles printing output
    4. Converts exceptions to sys.exit via run_command
    """
    git = RealGit()
    config = RealConfig()
    ui = RealUI()

    def core() -> None:
        sync_core(
            git=git,
            config=config,
            ui=ui,
            main_branch=main_branch,
            skip_push=skip_push,
        )

    run_command(ui, core)
