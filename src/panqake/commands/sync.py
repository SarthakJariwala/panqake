"""Command for syncing branches with remote repository changes."""

import sys

from panqake.utils.branch_operations import (
    fetch_latest_from_remote,
    return_to_branch,
    update_branch_with_conflict_detection,
)
from panqake.utils.config import (
    get_child_branches,
    get_parent_branch,
    remove_from_stack,
)
from panqake.utils.git import (
    checkout_branch,
    get_current_branch,
    run_git_command,
)
from panqake.utils.questionary_prompt import (
    print_formatted_text,
    prompt_confirm,
)


def get_merged_branches(into_branch="main"):
    """Get list of branches that have been merged into the specified branch."""
    merged_result = run_git_command(["branch", "--merged", into_branch])
    if not merged_result:
        return []

    merged_branches = []
    for branch in merged_result.splitlines():
        branch = branch.strip()
        # Remove the * prefix from current branch
        if branch.startswith("* "):
            branch = branch[2:]

        # Skip the branch itself and empty entries
        if branch and branch != into_branch:
            merged_branches.append(branch)

    return merged_branches


def handle_merged_branches(main_branch):
    """Handle merged branches by prompting user for deletion."""
    merged_branches = get_merged_branches(main_branch)
    branches_to_delete = []
    deleted_branches = []

    # Only prompt to delete branches that have main as their parent
    for branch in merged_branches:
        parent = get_parent_branch(branch)
        if parent == main_branch:
            branches_to_delete.append(branch)

    # Ask user if they want to delete merged branches
    success = True
    if branches_to_delete:
        for branch in branches_to_delete:
            print_formatted_text(
                f"[info]{branch} is merged into {main_branch}. Delete it?[/info]"
            )
            if prompt_confirm(""):
                # Delete the branch
                delete_result = run_git_command(["branch", "-D", branch])
                if delete_result is not None:
                    print_formatted_text(f"[success]Deleted branch {branch}[/success]")
                    # Remove from stacks config
                    remove_from_stack(branch)
                    deleted_branches.append(branch)
                else:
                    print_formatted_text(
                        f"[warning]Failed to delete branch {branch}[/warning]"
                    )
                    success = False

    return success, deleted_branches


def update_branches_with_conflict_handling(branch_name, current_branch):
    """Update branches with special conflict handling.

    Args:
        branch_name: Starting branch (typically main)
        current_branch: Original branch user was on

    Returns:
        Tuple of (success_flag, list_of_failed_branches)
    """
    failed_branches = []
    children = get_child_branches(branch_name)

    if not children:
        return True, failed_branches

    success = True
    for child in children:
        # Update this branch using the utility function
        child_success, error_msg = update_branch_with_conflict_detection(
            child, branch_name, abort_on_conflict=True
        )

        if not child_success:
            print_formatted_text(f"[warning]{error_msg}[/warning]")
            failed_branches.append(child)
            success = False
            # Stop at first conflict
            break

        # If this branch was successful, try to update its children
        child_success, child_failed = update_branches_with_conflict_handling(
            child, current_branch
        )
        if not child_success:
            failed_branches.extend(child_failed)
            success = False
            # We already have conflicts, no need to continue
            break

    return success, failed_branches


def handle_branch_updates(main_branch, current_branch):
    """Handle updating child branches with conflict detection."""
    children = get_child_branches(main_branch)
    failed_branches = []

    if not children:
        return True, failed_branches

    update_success, failed_branches = update_branches_with_conflict_handling(
        main_branch, current_branch
    )

    if not update_success:
        print_formatted_text(
            "[warning]All branches updated cleanly, except for:[/warning]"
        )
        for branch in failed_branches:
            print_formatted_text(f"[warning]▸ {branch}[/warning]")
        print_formatted_text(
            "[info]You can fix these conflicts with panqake update.[/info]"
        )

    return update_success, failed_branches


def sync_with_remote(main_branch="main"):
    """Sync local branches with remote repository changes."""
    # 1. Save current branch
    current_branch = get_current_branch()
    if not current_branch:
        print_formatted_text(
            "[warning]Error: Unable to determine current branch[/warning]"
        )
        sys.exit(1)

    # 2. Fetch & pull from remote
    print_formatted_text("[info]Pulling main from remote...[/info]")
    if not fetch_latest_from_remote(main_branch, current_branch):
        checkout_branch(current_branch)
        sys.exit(1)

    # 3. Handle merged branches
    print_formatted_text(
        "[info]Checking if any branches have been merged/closed and can be deleted...[/info]"
    )
    merged_success, deleted_branches = handle_merged_branches(main_branch)

    # 4. Update child branches with special conflict handling
    update_success, failed_branches = handle_branch_updates(main_branch, current_branch)

    # 5. Return to original branch or fallback to main if it was deleted
    return_to_branch(current_branch, main_branch, deleted_branches)

    if not failed_branches:
        print_formatted_text("[success]Sync completed successfully[/success]")
