"""Command for updating branches in the stack."""

import sys

from panqake.utils.branch_operations import (
    push_updated_branches,
    report_update_conflicts,
    return_to_branch,
    update_branches_and_handle_conflicts,
)
from panqake.utils.git import (
    get_current_branch,
)
from panqake.utils.questionary_prompt import (
    format_branch,
    print_formatted_text,
    prompt_confirm,
)
from panqake.utils.stack import Stacks


def validate_branch(branch_name):
    """Validate branch exists and get current branch using Stack utility."""
    # If no branch specified, use current branch
    if not branch_name:
        branch_name = get_current_branch()

    # Check if target branch exists using Stacks utility
    with Stacks() as stacks:
        if not stacks.branch_exists(branch_name):
            print_formatted_text(
                f"[warning]Error: Branch '{branch_name}' does not exist[/warning]"
            )
            sys.exit(1)

    return branch_name, get_current_branch()


def get_affected_branches(branch_name):
    """Get affected branches and ask for confirmation."""
    with Stacks() as stacks:
        affected_branches = stacks.get_all_descendants(branch_name)

    # Show summary and ask for confirmation
    if affected_branches:
        print_formatted_text("[info]The following branches will be updated:[/info]")
        for branch in affected_branches:
            print_formatted_text(f"  {format_branch(branch)}")

        if not prompt_confirm("Do you want to proceed with the update?"):
            print_formatted_text("[info]Update cancelled.[/info]")
            return None
    else:
        print_formatted_text(
            f"[info]No child branches found for {format_branch(branch_name)}.[/info]"
        )
        return None

    return affected_branches


def update_branch_and_children(branch, current_branch):
    """Update all child branches using a non-recursive approach.

    Args:
        branch: The branch to update children for
        current_branch: The original branch the user was on

    Returns:
        Tuple of (list of successfully updated branches, list of branches with conflicts)
    """

    return update_branches_and_handle_conflicts(branch, current_branch)


def update_branches(branch_name=None, skip_push=False):
    """Update branches in the stack after changes and optionally push to remote.

    Args:
        branch_name: The branch to update children for, or None to use current branch
        skip_push: If True, don't push changes to remote after updating

    Returns:
        Tuple of (success_flag, error_message) or None
    """
    branch_name, current_branch = validate_branch(branch_name)

    affected_branches = get_affected_branches(branch_name)
    if affected_branches is None:
        return True, None  # No affected branches is not an error

    # Start the update process
    print_formatted_text(
        f"[info]Starting stack update from branch[/info] {format_branch(branch_name)}..."
    )

    # Track successfully updated branches and branches with conflicts
    updated_branches, conflict_branches = update_branch_and_children(
        branch_name, current_branch
    )

    # Push to remote if requested
    if not skip_push:
        push_updated_branches(updated_branches, skip_push)

    # Return to the original branch using our utility function
    if not return_to_branch(current_branch):
        return False, f"Failed to return to branch '{current_branch}'"

    # Report success
    if skip_push:
        print_formatted_text("[success]Stack update complete (local only).")
    else:
        print_formatted_text("[success]Stack update complete.[/success]")

    # Report overall success based on conflicts
    return report_update_conflicts(conflict_branches)
