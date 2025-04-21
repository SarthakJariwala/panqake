"""Command for updating branches in the stack."""

import sys

from panqake.utils.config import get_child_branches
from panqake.utils.git import branch_exists, get_current_branch, run_git_command
from panqake.utils.questionary_prompt import (
    format_branch,
    print_formatted_text,
    prompt_confirm,
)


def collect_all_children(branch, result=None):
    """Recursively collect all child branches."""
    if result is None:
        result = []

    children = get_child_branches(branch)
    for child in children:
        if child not in result:
            result.append(child)
            collect_all_children(child, result)

    return result


def validate_branch(branch_name):
    """Validate branch exists and get current branch."""
    # If no branch specified, use current branch
    if not branch_name:
        branch_name = get_current_branch()

    # Check if target branch exists
    if not branch_exists(branch_name):
        print_formatted_text(
            f"<warning>Error: Branch '{branch_name}' does not exist</warning>"
        )
        sys.exit(1)

    return branch_name, get_current_branch()


def get_affected_branches(branch_name):
    """Get affected branches and ask for confirmation."""
    affected_branches = collect_all_children(branch_name)

    # Show summary and ask for confirmation
    if affected_branches:
        print_formatted_text("<info>The following branches will be updated:</info>")
        for branch in affected_branches:
            print_formatted_text(f"  {format_branch(branch)}")

        if not prompt_confirm("Do you want to proceed with the update?"):
            print_formatted_text("<info>Update cancelled.</info>")
            return None
    else:
        print_formatted_text(
            f"<info>No child branches found for {format_branch(branch_name)}.</info>"
        )
        return None

    return affected_branches


def update_branch_and_children(branch, current_branch):
    """Recursively update child branches."""
    children = get_child_branches(branch)

    if children:
        for child in children:
            print_formatted_text(
                f"<info>Updating branch</info> {format_branch(child)} "
                f"<info>based on changes to</info> {format_branch(branch)}..."
            )

            # Checkout the child branch
            checkout_result = run_git_command(["checkout", child])
            if checkout_result is None:
                print_formatted_text(
                    f"<warning>Error: Failed to checkout branch '{child}'</warning>"
                )
                run_git_command(["checkout", current_branch])
                sys.exit(1)

            # Rebase onto the parent branch
            rebase_result = run_git_command(["rebase", branch])
            if rebase_result is None:
                print_formatted_text(
                    f"<warning>Error: Rebase conflict detected in branch '{child}'</warning>"
                )
                print_formatted_text(
                    "<warning>Please resolve conflicts and run 'git rebase --continue'</warning>"
                )
                print_formatted_text(
                    f"<warning>Then run 'panqake update {child}' to continue updating the stack</warning>"
                )
                sys.exit(1)

            # Continue with children of this branch
            update_branch_and_children(child, current_branch)


def update_branches(branch_name=None):
    """Update branches in the stack after changes."""
    branch_name, current_branch = validate_branch(branch_name)

    affected_branches = get_affected_branches(branch_name)
    if affected_branches is None:
        return

    # Start the update process
    print_formatted_text(
        f"<info>Starting stack update from branch</info> {format_branch(branch_name)}..."
    )
    update_branch_and_children(branch_name, current_branch)

    # Return to the original branch
    run_git_command(["checkout", current_branch])
    print_formatted_text(
        f"<success>Stack update complete. Returned to branch {format_branch(current_branch)}</success>"
    )
