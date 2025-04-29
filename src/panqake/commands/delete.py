"""Command for deleting a branch and relinking the stack."""

import sys

from panqake.utils.config import (
    add_to_stack,
    get_child_branches,
    get_parent_branch,
    remove_from_stack,
)
from panqake.utils.git import (
    branch_exists,
    checkout_branch,
    get_current_branch,
    run_git_command,
)
from panqake.utils.questionary_prompt import (
    format_branch,
    print_formatted_text,
    prompt_confirm,
)


def validate_branch_for_deletion(branch_name):
    """Validate that a branch can be deleted."""
    current_branch = get_current_branch()

    # Check if target branch exists
    if not branch_exists(branch_name):
        print_formatted_text(
            f"[warning]Error: Branch '{branch_name}' does not exist[/warning]"
        )
        sys.exit(1)

    # Check if target branch is the current branch
    if branch_name == current_branch:
        print_formatted_text(
            "[warning]Error: Cannot delete the current branch. Please checkout another branch first.[/warning]"
        )
        sys.exit(1)

    return current_branch


def get_branch_relationships(branch_name):
    """Get parent and child branches and validate parent exists."""
    parent_branch = get_parent_branch(branch_name)
    child_branches = get_child_branches(branch_name)

    # Ensure parent branch exists
    if parent_branch and not branch_exists(parent_branch):
        print_formatted_text(
            f"[warning]Error: Parent branch '{parent_branch}' does not exist[/warning]"
        )
        sys.exit(1)

    return parent_branch, child_branches


def display_deletion_info(branch_name, parent_branch, child_branches):
    """Display deletion information and ask for confirmation."""
    print_formatted_text(
        f"[info]Branch to delete:[/info] {format_branch(branch_name, danger=True)}"
    )
    if parent_branch:
        print_formatted_text(
            f"[info]Parent branch:[/info] {format_branch(parent_branch)}"
        )
    if child_branches:
        print_formatted_text("[info]Child branches that will be relinked:[/info]")
        for child in child_branches:
            print_formatted_text(f"  {format_branch(child)}")

    # Confirm deletion
    if not prompt_confirm("Are you sure you want to delete this branch?"):
        print_formatted_text("[info]Branch deletion cancelled.[/info]")
        return False

    return True


def relink_child_branches(child_branches, parent_branch, current_branch, branch_name):
    """Relink child branches to the parent branch."""
    if not child_branches:
        return True

    print_formatted_text(
        f"[info]Relinking child branches to parent '{parent_branch}'...[/info]"
    )

    for child in child_branches:
        print_formatted_text(
            f"[info]Processing child branch:[/info] {format_branch(child)}"
        )

        # Checkout the child branch
        checkout_branch(child)

        # Rebase onto the grandparent branch
        if parent_branch:
            rebase_result = run_git_command(["rebase", parent_branch])
            if rebase_result is None:
                print_formatted_text(
                    f"[warning]Error: Rebase conflict detected in branch '{child}'[/warning]"
                )
                print_formatted_text(
                    "[warning]Please resolve conflicts and run 'git rebase --continue'[/warning]"
                )
                print_formatted_text(
                    f"[warning]Then run 'panqake delete {branch_name}' again to retry[/warning]"
                )
                sys.exit(1)

            # Update stack metadata
            add_to_stack(child, parent_branch)

    return True


def delete_branch(branch_name):
    """Delete a branch and relink the stack."""
    current_branch = validate_branch_for_deletion(branch_name)
    parent_branch, child_branches = get_branch_relationships(branch_name)

    if not display_deletion_info(branch_name, parent_branch, child_branches):
        return

    print_formatted_text(
        f"[info]Deleting branch '{branch_name}' from the stack...[/info]"
    )

    # Process child branches
    relink_child_branches(child_branches, parent_branch, current_branch, branch_name)

    # Return to original branch if it's not the one being deleted
    if branch_name != current_branch:
        checkout_branch(current_branch)

    # Delete the branch
    delete_result = run_git_command(["branch", "-D", branch_name])
    if delete_result is None:
        print_formatted_text(
            f"[warning]Error: Failed to delete branch '{branch_name}'[/warning]"
        )
        sys.exit(1)

    # Remove from stack metadata
    remove_from_stack(branch_name)

    print_formatted_text(
        f"[success]Success! Deleted branch '{branch_name}' and relinked the stack[/success]"
    )
