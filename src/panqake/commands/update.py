"""Command for updating branches in the stack."""

import sys

from panqake.utils.branch_operations import (
    return_to_branch,
    update_branch_with_conflict_detection,
)
from panqake.utils.git import (
    checkout_branch,
    get_current_branch,
    is_branch_pushed_to_remote,
    push_branch_to_remote,
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
    updated_branches = []
    conflict_branches = []

    with Stacks() as stacks:
        # Get all descendants in depth-first order
        all_branches_to_update = []
        branches_to_process = [(branch, None)]  # (branch, parent) pairs

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
    if not skip_push and updated_branches:
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

            try:
                checkout_branch(branch)
            except SystemExit:
                print_formatted_text(
                    f"[warning]Failed to checkout branch '{branch}' for pushing[/warning]"
                )
                continue

            # Always use force-with-lease for safety since we've rebased
            success = push_branch_to_remote(branch, force=True)

            if not success:
                print_formatted_text(
                    f"[warning]Failed to push branch '{branch}' to remote[/warning]"
                )
            else:
                successfully_pushed.append(branch)
                print_formatted_text(
                    f"[success]Branch {format_branch(branch)} pushed to remote[/success]"
                )

    # Return to the original branch using our utility function
    if not return_to_branch(current_branch):
        return False, f"Failed to return to branch '{current_branch}'"

    # Report success
    if skip_push:
        print_formatted_text("[success]Stack update complete (local only).")
    else:
        print_formatted_text("[success]Stack update complete.[/success]")

    # Report overall success based on conflicts
    if conflict_branches:
        print_formatted_text(
            "[warning]The following branches had conflicts during stack update:[/warning]"
        )
        for branch in conflict_branches:
            print_formatted_text(f"  [warning]{format_branch(branch)}[/warning]")
        print_formatted_text(
            "[info]Please resolve conflicts in these branches and run 'pq update <branch>' again[/info]"
        )
        return False, "Some branches had conflicts during update"

    return True, None
