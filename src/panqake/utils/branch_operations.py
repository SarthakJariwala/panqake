"""Utility functions for common branch operations used across commands."""

from panqake.utils.git import (
    branch_exists,
    checkout_branch,
    run_git_command,
)
from panqake.utils.questionary_prompt import (
    format_branch,
    print_formatted_text,
)


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
    rebase_result = run_git_command(["rebase", parent])
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
