"""Command for updating branches in the stack.

Uses dependency injection for testability.
Core logic is pure - no sys.exit, no direct filesystem/git calls.
"""

from dataclasses import dataclass

from panqake.ports import (
    BranchNotFoundError,
    ConfigPort,
    GitPort,
    RebaseConflictError,
    RealConfig,
    RealGit,
    RealUI,
    UIPort,
    run_command,
)
from panqake.utils.questionary_prompt import format_branch
from panqake.utils.types import BranchName


@dataclass(frozen=True)
class UpdateResult:
    """Result of updating branches in a stack."""

    starting_branch: BranchName
    original_branch: BranchName
    returned_to: BranchName | None
    affected_branches: list[BranchName]
    updated_branches: list[BranchName]
    conflict_branches: list[BranchName]
    pushed_branches: list[BranchName]
    skipped_push_branches: list[BranchName]
    skip_push: bool


def get_affected_branches_core(
    config: ConfigPort,
    branch_name: BranchName,
) -> list[BranchName]:
    """Get all descendant branches that will be affected by update.

    Args:
        config: Stack configuration interface
        branch_name: The branch to get descendants for

    Returns:
        List of branch names that are descendants
    """
    affected: list[BranchName] = []
    branches_to_process: list[BranchName] = [branch_name]

    while branches_to_process:
        current = branches_to_process.pop(0)
        children = config.get_child_branches(current)
        for child in children:
            affected.append(child)
            branches_to_process.append(child)

    return affected


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
    starting_branch: BranchName,
) -> tuple[list[BranchName], list[BranchName]]:
    """Update all child branches in the stack.

    Args:
        git: Git operations interface
        config: Stack configuration interface
        ui: User interaction interface
        starting_branch: Starting branch to update children from

    Returns:
        Tuple of (updated_branches, conflict_branches)
    """
    updated_branches: list[BranchName] = []
    conflict_branches: list[BranchName] = []

    # Build list of all branches to update with their parents (depth-first)
    branches_to_process: list[tuple[BranchName, BranchName | None]] = [
        (starting_branch, None)
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
    from panqake.ports import GitOperationError

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

        # For worktree branches, skip (can't checkout)
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
) -> BranchName | None:
    """Return to the target branch.

    Args:
        git: Git operations interface
        ui: User interaction interface
        target_branch: The branch to return to

    Returns:
        The branch that was switched to, or None if switch failed
    """
    from panqake.ports import GitOperationError

    if git.branch_exists(target_branch):
        try:
            git.checkout_branch(target_branch)
            return target_branch
        except GitOperationError:
            ui.print_error(f"Failed to return to branch '{target_branch}'")
            return None

    ui.print_error(f"Branch '{target_branch}' no longer exists")
    return None


def update_core(
    git: GitPort,
    config: ConfigPort,
    ui: UIPort,
    branch_name: BranchName | None = None,
    skip_push: bool = False,
) -> UpdateResult:
    """Update branches in the stack after changes.

    This is the pure core logic that can be tested without mocking.

    Args:
        git: Git operations interface
        config: Stack configuration interface
        ui: User interaction interface
        branch_name: The branch to update children for, or None for current
        skip_push: If True, don't push changes to remote after updating

    Returns:
        UpdateResult with details of the update operation

    Raises:
        BranchNotFoundError: If branch cannot be determined or doesn't exist
        UserCancelledError: If user cancels confirmation prompt
    """
    # 1. Validate branch and get current branch
    original_branch = git.get_current_branch()
    if not original_branch:
        raise BranchNotFoundError("Could not determine current branch")

    if branch_name is None:
        branch_name = original_branch

    git.validate_branch(branch_name)

    # 2. Get affected branches
    affected_branches = get_affected_branches_core(config, branch_name)

    if not affected_branches:
        ui.print_info(f"No child branches found for {format_branch(branch_name)}.")
        return UpdateResult(
            starting_branch=branch_name,
            original_branch=original_branch,
            returned_to=original_branch,
            affected_branches=[],
            updated_branches=[],
            conflict_branches=[],
            pushed_branches=[],
            skipped_push_branches=[],
            skip_push=skip_push,
        )

    # 3. Show summary and ask for confirmation
    ui.print_info("The following branches will be updated:")
    for branch in affected_branches:
        ui.print_info(f"  {format_branch(branch)}")

    if not ui.prompt_confirm("Do you want to proceed with the update?"):
        ui.print_info("Update cancelled.")
        return UpdateResult(
            starting_branch=branch_name,
            original_branch=original_branch,
            returned_to=original_branch,
            affected_branches=affected_branches,
            updated_branches=[],
            conflict_branches=[],
            pushed_branches=[],
            skipped_push_branches=[],
            skip_push=skip_push,
        )

    # 4. Update all branches
    updated_branches, conflict_branches = update_all_branches_core(
        git, config, ui, branch_name
    )

    # 5. Push to remote if requested
    pushed_branches: list[BranchName] = []
    skipped_push_branches: list[BranchName] = []

    if not skip_push and updated_branches:
        pushed_branches, skipped_push_branches = push_updated_branches_core(
            git, ui, updated_branches
        )

    # 6. Return to original branch
    returned_to = return_to_branch_core(git, ui, original_branch)

    # 7. Report completion
    if skip_push:
        ui.print_success("Stack update complete (local only).")
    else:
        ui.print_success("Stack update complete.")

    # 8. Report conflicts if any
    if conflict_branches:
        ui.print_error("The following branches had conflicts:")
        for branch in conflict_branches:
            ui.print_error(f"  {format_branch(branch)}")
        ui.print_info(
            "Please resolve conflicts in these branches and run "
            "'pq update <branch>' again"
        )

    return UpdateResult(
        starting_branch=branch_name,
        original_branch=original_branch,
        returned_to=returned_to,
        affected_branches=affected_branches,
        updated_branches=updated_branches,
        conflict_branches=conflict_branches,
        pushed_branches=pushed_branches,
        skipped_push_branches=skipped_push_branches,
        skip_push=skip_push,
    )


def update_branches(
    branch_name: BranchName | None = None, skip_push: bool = False
) -> None:
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
        update_core(
            git=git,
            config=config,
            ui=ui,
            branch_name=branch_name,
            skip_push=skip_push,
        )

    run_command(ui, core)
