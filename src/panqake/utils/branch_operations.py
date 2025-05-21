"""Utility functions for common branch operations used across commands."""

from panqake.utils.git import (
    branch_exists,
    checkout_branch,
    has_unpushed_changes,
    is_branch_pushed_to_remote,
    push_branch_to_remote,
    run_git_command,
)
from panqake.utils.questionary_prompt import (
    format_branch,
    print_formatted_text,
)
from panqake.utils.stack import Stacks


def update_branch_with_conflict_detection(branch, parent, abort_on_conflict=True):
    """Update a branch with conflict detection.

    Args:
        branch: The branch to update
        parent: The parent branch to rebase onto
        abort_on_conflict: Whether to abort the rebase on conflict

    Returns:
        Tuple of (success_flag, error_message)
    """
    # Checkout the branch
    try:
        checkout_branch(branch)
    except SystemExit:
        return False, f"Failed to checkout branch '{branch}'"

    # Rebase onto parent branch
    rebase_result = run_git_command(["rebase", "--autostash", parent])
    if rebase_result is None:
        # Conflict detected
        if abort_on_conflict:
            run_git_command(["rebase", "--abort"])
            return False, f"Rebase conflict detected in branch '{branch}'"
        else:
            error_msg = (
                f"Rebase conflict detected in branch '{branch}'. "
                f"Please resolve conflicts and run 'pq rebase --continue'"
            )
            return False, error_msg

    print_formatted_text(
        f"[success]Updated {format_branch(branch)} on {format_branch(parent)}.[/success]"
    )
    return True, None


def fetch_latest_from_remote(branch_name, current_branch=None):
    """Fetch the latest changes for a branch from remote.

    Args:
        branch_name: The branch to fetch updates for
        current_branch: The branch to return to if there's an error

    Returns:
        True if successful, False otherwise
    """
    print_formatted_text("[info]Fetching latest changes from remote...[/info]")

    # Fetch from remote
    fetch_result = run_git_command(["fetch", "origin"])
    if fetch_result is None:
        print_formatted_text("[warning]Error: Failed to fetch from remote[/warning]")
        return False

    # Checkout the branch if it's not already checked out
    try:
        checkout_branch(branch_name)
    except SystemExit:
        return False

    # Pull latest changes
    pull_result = run_git_command(["pull", "origin", branch_name])
    if pull_result is None:
        print_formatted_text(
            f"[warning]Error: Failed to pull from origin/{branch_name}[/warning]"
        )
        if current_branch:
            checkout_branch(current_branch)
        return False

    # Get the commit hash to show in the output
    commit_hash = run_git_command(["rev-parse", "HEAD"])
    if commit_hash:
        commit_hash = commit_hash.strip()
        print_formatted_text(
            f"[success]{branch_name} fast-forwarded to {commit_hash}.[/success]"
        )

    return True


def return_to_branch(target_branch, fallback_branch=None, deleted_branches=None):
    """Return to the target branch or fallback branch if target was deleted.

    Args:
        target_branch: The branch to return to
        fallback_branch: The fallback branch if target doesn't exist
        deleted_branches: List of branches that were deleted

    Returns:
        True if successful, False otherwise
    """
    deleted_branches = deleted_branches or []

    # Check if the target branch still exists and wasn't deleted
    if branch_exists(target_branch) and target_branch not in deleted_branches:
        print_formatted_text(
            f"[info]Returning to {format_branch(target_branch)}...[/info]"
        )
        try:
            checkout_branch(target_branch)
            return True
        except SystemExit:
            return False
        return True
    elif fallback_branch and branch_exists(fallback_branch):
        # If target branch no longer exists, go to fallback branch
        msg = (
            f"[info]Branch {format_branch(target_branch)} no longer exists, "
            f"returning to {format_branch(fallback_branch)}...[/info]"
        )
        print_formatted_text(msg)
        try:
            checkout_branch(fallback_branch)
            return True
        except SystemExit:
            print_formatted_text(
                f"[warning]Error: Failed to checkout {fallback_branch}[/warning]"
            )
            return False
        return True
    else:
        print_formatted_text(
            "[warning]Error: Unable to find a valid branch to return to[/warning]"
        )
        return False


def update_branches_and_handle_conflicts(branch_name, current_branch):
    """Update all branches in the stack using a non-recursive approach.

    Args:
        branch_name: Starting branch to update children from
        current_branch: Original branch user was on

    Returns:
        Tuple of (list of successfully updated branches, list of branches with conflicts)
    """
    updated_branches = []
    conflict_branches = []

    with Stacks() as stacks:
        # Get all descendants in depth-first order
        all_branches_to_update = []
        branches_to_process = [(branch_name, None)]  # (branch, parent) pairs

        # Build a list of all branches to update with their parents
        while branches_to_process:
            current, parent = branches_to_process.pop(0)

            # Skip the starting branch itself
            if parent is not None:
                all_branches_to_update.append((current, parent))

            # Add all children with current as their parent
            children = stacks.get_children(current)
            for child in children:
                branches_to_process.append((child, current))

        # Process all branches in order
        for child, parent in all_branches_to_update:
            print_formatted_text(
                f"[info]Updating branch[/info] {format_branch(child)} "
                f"[info]based on changes to[/info] {format_branch(parent)}..."
            )

            # Skip branches whose parents had conflicts
            if parent in conflict_branches:
                print_formatted_text(
                    f"[warning]Skipping {format_branch(child)} as its parent {format_branch(parent)} had conflicts[/warning]"
                )
                conflict_branches.append(child)
                continue

            # Use utility function to update the branch with conflict detection
            success, error_msg = update_branch_with_conflict_detection(
                child, parent, abort_on_conflict=True
            )

            if not success:
                print_formatted_text(f"[warning]{error_msg}[/warning]")
                print_formatted_text(
                    f"[warning]Run 'pq update {child}' after resolving conflicts to continue updating the stack[/warning]"
                )
                conflict_branches.append(child)
            else:
                updated_branches.append(child)

    return updated_branches, conflict_branches


def push_updated_branches(updated_branches):
    """Push successfully updated branches to remote.

    Args:
        updated_branches: List of branch names to push

    Returns:
        List of successfully pushed branches
    """
    if not updated_branches:
        return []

    print_formatted_text("[info]Pushing updated branches to remote...[/info]")

    # Push each branch that was successfully updated
    successfully_pushed = []
    for branch in updated_branches:
        # Skip branches that don't exist on remote yet
        if not is_branch_pushed_to_remote(branch):
            print_formatted_text(
                f"[info]Skipping push for {format_branch(branch)} as it doesn't exist on remote yet[/info]"
            )
            continue

        # Check if the branch has unpushed changes
        if not has_unpushed_changes(branch):
            print_formatted_text(
                f"[info]Skipping push for {format_branch(branch)} as it's already in sync with remote[/info]"
            )
            continue

        try:
            checkout_branch(branch)
        except SystemExit:
            print_formatted_text(
                f"[warning]Failed to checkout branch '{branch}' for pushing[/warning]"
            )
            continue

        # Always use force-with-lease for safety since we've rebased
        success = push_branch_to_remote(branch, force_with_lease=True)

        if not success:
            print_formatted_text(
                f"[warning]Failed to push branch '{branch}' to remote[/warning]"
            )
        else:
            successfully_pushed.append(branch)
            print_formatted_text(
                f"[success]Branch {format_branch(branch)} pushed to remote[/success]"
            )

    return successfully_pushed


def report_update_conflicts(conflict_branches):
    """Report branches with conflicts after an update operation.

    Args:
        conflict_branches: List of branch names that had conflicts

    Returns:
        Tuple of (success_flag, error_message)
    """
    if not conflict_branches:
        return True, None

    print_formatted_text("[warning]The following branches had conflicts:[/warning]")
    for branch in conflict_branches:
        print_formatted_text(f"  [warning]{format_branch(branch)}[/warning]")
    print_formatted_text(
        "[info]Please resolve conflicts in these branches and run 'pq update <branch>' again[/info]"
    )
    return False, "Some branches had conflicts"
