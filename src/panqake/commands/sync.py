"""Command for syncing branches with remote repository changes."""

import sys

from panqake.utils.branch_operations import (
    fetch_latest_from_remote,
    push_updated_branches,
    report_update_conflicts,
    return_to_branch,
    update_branches_and_handle_conflicts,
)
from panqake.utils.config import (
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
from panqake.utils.stack import Stacks
from panqake.utils.status import status


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
    with status(f"Checking for merged branches into {main_branch}..."):
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
                with status(f"Deleting branch {branch}..."):
                    # Delete the branch
                    delete_result = run_git_command(["branch", "-D", branch])
                    if delete_result is not None:
                        # Remove from stacks config
                        stack_removal = remove_from_stack(branch)
                        if not stack_removal:
                            print_formatted_text(
                                f"[warning]Branch {branch} not found in stack metadata[/warning]"
                            )
                        deleted_branches.append(branch)
                    else:
                        success = False

                if delete_result is not None:
                    print_formatted_text(f"[success]Deleted branch {branch}[/success]")
                else:
                    print_formatted_text(
                        f"[warning]Failed to delete branch {branch}[/warning]"
                    )

    return success, deleted_branches


def update_branches_with_conflict_handling(branch_name, current_branch):
    """Update branches with special conflict handling.

    Args:
        branch_name: Starting branch (typically main)
        current_branch: Original branch user was on

    Returns:
        Tuple of (list of successfully updated branches, list of branches with conflicts)
    """
    with Stacks() as stacks:
        children = stacks.get_children(branch_name)
        if not children:
            return [], []

    return update_branches_and_handle_conflicts(branch_name, current_branch)


def handle_branch_updates(main_branch, current_branch):
    """Handle updating child branches with conflict detection.

    Args:
        main_branch: The main branch to start updates from
        current_branch: The original branch the user was on

    Returns:
        Tuple of (updated_branches, conflict_branches)
    """
    with Stacks() as stacks:
        children = stacks.get_children(main_branch)
        if not children:
            return [], []

    updated_branches, conflict_branches = update_branches_with_conflict_handling(
        main_branch, current_branch
    )

    if conflict_branches:
        print_formatted_text(
            "[warning]All branches updated cleanly, except for:[/warning]"
        )
        for branch in conflict_branches:
            print_formatted_text(f"[warning]▸ {branch}[/warning]")
        print_formatted_text(
            "[info]You can fix these conflicts with panqake update.[/info]"
        )

    return updated_branches, conflict_branches


def sync_with_remote(main_branch="main", skip_push=False):
    """Sync local branches with remote repository changes and optionally push to remote.

    Args:
        main_branch: Base branch to sync with (default: main)
        skip_push: If True, don't push changes to remote after updating

    Returns:
        Tuple of (success_flag, error_message) or None
    """
    # 1. Save current branch
    current_branch = get_current_branch()
    if not current_branch:
        print_formatted_text(
            "[warning]Error: Unable to determine current branch[/warning]"
        )
        sys.exit(1)

    # 2. Fetch & pull from remote
    if not fetch_latest_from_remote(main_branch, current_branch):
        checkout_branch(current_branch)
        sys.exit(1)

    # 3. Handle merged branches
    merged_success, deleted_branches = handle_merged_branches(main_branch)

    # 4. Update child branches with special conflict handling
    updated_branches, conflict_branches = handle_branch_updates(
        main_branch, current_branch
    )

    # 5. Push to remote if requested
    if not skip_push:
        push_updated_branches(updated_branches)

    # 6. Return to original branch or fallback to main if it was deleted
    return_to_branch(current_branch, main_branch, deleted_branches)

    # 7. Report success
    if skip_push:
        print_formatted_text(
            "[success]Sync completed successfully (local only)[/success]"
        )
    else:
        print_formatted_text("[success]Sync completed successfully[/success]")

    # 8. Report overall success based on conflicts
    return report_update_conflicts(conflict_branches)
