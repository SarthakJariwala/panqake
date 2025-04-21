"""Command for deleting a branch and relinking the stack."""

import sys

from panqake.utils.config import (
    add_to_stack,
    get_child_branches,
    get_parent_branch,
    remove_from_stack,
)
from panqake.utils.git import branch_exists, get_current_branch, run_git_command


def delete_branch(branch_name):
    """Delete a branch and relink the stack."""
    current_branch = get_current_branch()

    # Check if target branch exists
    if not branch_exists(branch_name):
        print(f"Error: Branch '{branch_name}' does not exist")
        sys.exit(1)

    # Check if target branch is the current branch
    if branch_name == current_branch:
        print(
            "Error: Cannot delete the current branch. Please checkout another branch first."
        )
        sys.exit(1)

    # Get parent and children of the target branch
    parent_branch = get_parent_branch(branch_name)
    child_branches = get_child_branches(branch_name)

    # Ensure parent branch exists
    if parent_branch and not branch_exists(parent_branch):
        print(f"Error: Parent branch '{parent_branch}' does not exist")
        sys.exit(1)

    print(f"Deleting branch '{branch_name}' from the stack...")

    # Process each child branch
    if child_branches:
        print(f"Relinking child branches to parent '{parent_branch}'...")

        for child in child_branches:
            print(f"Processing child branch: {child}")

            # Checkout the child branch
            checkout_result = run_git_command(["checkout", child])
            if checkout_result is None:
                print(f"Error: Failed to checkout branch '{child}'")
                run_git_command(["checkout", current_branch])
                sys.exit(1)

            # Rebase onto the grandparent branch
            if parent_branch:
                rebase_result = run_git_command(["rebase", parent_branch])
                if rebase_result is None:
                    print(
                        f"Error: Rebase conflict detected in branch '{child}'"
                    )
                    print(
                        "Please resolve conflicts and run 'git rebase --continue'"
                    )
                    print(
                        f"Then run 'panqake delete {branch_name}' again to retry"
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
        print(f"Error: Failed to delete branch '{branch_name}'")
        sys.exit(1)

    # Remove from stack metadata
    remove_from_stack(branch_name)

    print(f"Success! Deleted branch '{branch_name}' and relinked the stack")
