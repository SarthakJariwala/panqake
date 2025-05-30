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
    validate_branch,
)
from panqake.utils.questionary_prompt import (
    format_branch,
    print_formatted_text,
    prompt_confirm,
)
from panqake.utils.selection import select_branch_excluding_current
from panqake.utils.status import status
from panqake.utils.types import BranchName


def validate_branch_for_deletion(branch_name: BranchName) -> BranchName:
    """Validate that a branch can be deleted."""
    current_branch = get_current_branch()
    if not current_branch:
        print_formatted_text(
            "[danger]Error: Could not determine current branch[/danger]"
        )
        sys.exit(1)

    # Check if target branch exists
    validate_branch(branch_name)

    # Check if target branch is the current branch
    if branch_name == current_branch:
        print_formatted_text(
            "[warning]Error: Cannot delete the current branch. Please checkout another branch first.[/warning]"
        )
        sys.exit(1)

    return current_branch


def get_branch_relationships(
    branch_name: BranchName,
) -> tuple[BranchName | None, list[BranchName]]:
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


def display_deletion_info(
    branch_name: BranchName,
    parent_branch: BranchName | None,
    child_branches: list[BranchName],
) -> bool:
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


def relink_child_branches(
    child_branches: list[BranchName],
    parent_branch: BranchName | None,
    current_branch: BranchName,
    branch_name: BranchName,
) -> bool:
    """Relink child branches to the parent branch."""
    if not child_branches:
        return True

    with status(f"Relinking child branches to parent '{parent_branch}'...") as s:
        for child in child_branches:
            s.update(f"Processing child branch {child}...")

            checkout_branch(child)

            # Rebase onto the grandparent branch
            if parent_branch:
                s.update(f"Rebasing {child} onto {parent_branch}...")
                rebase_result = run_git_command(
                    ["rebase", "--autostash", parent_branch]
                )
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


def delete_branch(branch_name: BranchName | None = None) -> None:
    """Delete a branch and relink the stack."""
    # If no branch name specified, prompt for it
    if not branch_name:
        selected_branch = select_branch_excluding_current(
            "Select branch to delete:", exclude_protected=True, enable_search=True
        )

        if not selected_branch:
            print_formatted_text(
                "[warning]No branches available for deletion.[/warning]"
            )
            return

        branch_name = selected_branch

    current_branch = validate_branch_for_deletion(branch_name)
    parent_branch, child_branches = get_branch_relationships(branch_name)

    if not display_deletion_info(branch_name, parent_branch, child_branches):
        return

    with status(f"Deleting branch '{branch_name}' from the stack...") as s:
        # Process child branches
        if child_branches:
            s.update("Processing child branches...")
            relink_child_branches(
                child_branches, parent_branch, current_branch, branch_name
            )

        # Return to original branch if it's not the one being deleted
        if branch_name != current_branch:
            s.update(f"Returning to {current_branch}...")
            checkout_branch(current_branch)

        # Delete the branch
        s.update(f"Deleting branch {branch_name}...")
        delete_result = run_git_command(["branch", "-D", branch_name])
        if delete_result is None:
            print_formatted_text(
                f"[warning]Error: Failed to delete branch '{branch_name}'[/warning]"
            )
            sys.exit(1)

        # Remove from stack metadata
        stack_removal = remove_from_stack(branch_name)

    if stack_removal:
        print_formatted_text(
            f"[success]Success! Deleted branch '{branch_name}' and relinked the stack[/success]"
        )
    else:
        print_formatted_text(
            f"[warning]Branch '{branch_name}' was deleted but not found in stack metadata.[/warning]"
        )
