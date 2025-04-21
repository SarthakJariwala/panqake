"""Command for deleting a branch and relinking the stack."""

import sys

from prompt_toolkit import print_formatted_text as print_ft
from prompt_toolkit.formatted_text import HTML

from panqake.utils.config import (
    add_to_stack,
    get_child_branches,
    get_parent_branch,
    remove_from_stack,
)
from panqake.utils.git import branch_exists, get_current_branch, run_git_command
from panqake.utils.prompt import format_branch, prompt_confirm


def delete_branch(branch_name):
    """Delete a branch and relink the stack."""
    current_branch = get_current_branch()

    # Check if target branch exists
    if not branch_exists(branch_name):
        print_ft(
            HTML(f"<warning>Error: Branch '{branch_name}' does not exist</warning>")
        )
        sys.exit(1)

    # Check if target branch is the current branch
    if branch_name == current_branch:
        print_ft(
            HTML(
                "<warning>Error: Cannot delete the current branch. Please checkout another branch first.</warning>"
            )
        )
        sys.exit(1)

    # Get parent and children of the target branch
    parent_branch = get_parent_branch(branch_name)
    child_branches = get_child_branches(branch_name)

    # Ensure parent branch exists
    if parent_branch and not branch_exists(parent_branch):
        print_ft(
            HTML(
                f"<warning>Error: Parent branch '{parent_branch}' does not exist</warning>"
            )
        )
        sys.exit(1)

    # Show summary and ask for confirmation
    print_ft(
        HTML(
            f"<info>Branch to delete:</info> {format_branch(branch_name, danger=True)}"
        )
    )
    if parent_branch:
        print_ft(HTML(f"<info>Parent branch:</info> {format_branch(parent_branch)}"))
    if child_branches:
        print_ft(HTML("<info>Child branches that will be relinked:</info>"))
        for child in child_branches:
            print_ft(HTML(f"  {format_branch(child)}"))

    # Confirm deletion
    if not prompt_confirm(
        "Are you sure you want to delete this branch?", default=False
    ):
        print_ft(HTML("<info>Branch deletion cancelled.</info>"))
        return

    print_ft(HTML(f"<info>Deleting branch '{branch_name}' from the stack...</info>"))

    # Process each child branch
    if child_branches:
        print_ft(
            HTML(
                f"<info>Relinking child branches to parent '{parent_branch}'...</info>"
            )
        )

        for child in child_branches:
            print_ft(
                HTML(f"<info>Processing child branch:</info> {format_branch(child)}")
            )

            # Checkout the child branch
            checkout_result = run_git_command(["checkout", child])
            if checkout_result is None:
                print_ft(
                    HTML(
                        f"<warning>Error: Failed to checkout branch '{child}'</warning>"
                    )
                )
                run_git_command(["checkout", current_branch])
                sys.exit(1)

            # Rebase onto the grandparent branch
            if parent_branch:
                rebase_result = run_git_command(["rebase", parent_branch])
                if rebase_result is None:
                    print_ft(
                        HTML(
                            f"<warning>Error: Rebase conflict detected in branch '{child}'</warning>"
                        )
                    )
                    print_ft(
                        HTML(
                            "<warning>Please resolve conflicts and run 'git rebase --continue'</warning>"
                        )
                    )
                    print_ft(
                        HTML(
                            f"<warning>Then run 'panqake delete {branch_name}' again to retry</warning>"
                        )
                    )
                    sys.exit(1)

                # Update stack metadata
                add_to_stack(child, parent_branch)

    # Return to original branch if it's not the one being deleted
    if branch_name != current_branch:
        run_git_command(["checkout", current_branch])

    # Delete the branch
    delete_result = run_git_command(["branch", "-D", branch_name])
    if delete_result is None:
        print_ft(
            HTML(f"<warning>Error: Failed to delete branch '{branch_name}'</warning>")
        )
        sys.exit(1)

    # Remove from stack metadata
    remove_from_stack(branch_name)

    print_ft(
        HTML(
            f"<success>Success! Deleted branch '{branch_name}' and relinked the stack</success>"
        )
    )
