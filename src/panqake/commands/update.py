"""Command for updating branches in the stack."""

import sys

from panqake.utils.git import get_current_branch, branch_exists, run_git_command
from panqake.utils.config import get_child_branches


def update_branches(branch_name=None):
    """Update branches in the stack after changes."""
    # If no branch specified, use current branch
    if not branch_name:
        branch_name = get_current_branch()

    # Check if target branch exists
    if not branch_exists(branch_name):
        print(f"Error: Branch '{branch_name}' does not exist")
        sys.exit(1)

    # Store current branch to return to it later
    current_branch = get_current_branch()

    def update_branch_and_children(branch):
        """Recursively update child branches."""
        children = get_child_branches(branch)

        if children:
            for child in children:
                print(f"Updating branch '{child}' based on changes to '{branch}'...")

                # Checkout the child branch
                checkout_result = run_git_command(["checkout", child])
                if checkout_result is None:
                    print(f"Error: Failed to checkout branch '{child}'")
                    run_git_command(["checkout", current_branch])
                    sys.exit(1)

                # Rebase onto the parent branch
                rebase_result = run_git_command(["rebase", branch])
                if rebase_result is None:
                    print(f"Error: Rebase conflict detected in branch '{child}'")
                    print("Please resolve conflicts and run 'git rebase --continue'")
                    print(
                        f"Then run 'panqake update {child}' to continue updating the stack"
                    )
                    sys.exit(1)

                # Continue with children of this branch
                update_branch_and_children(child)

    # Start the update process
    print(f"Starting stack update from branch '{branch_name}'...")
    update_branch_and_children(branch_name)

    # Return to the original branch
    run_git_command(["checkout", current_branch])
    print(f"Stack update complete. Returned to branch '{current_branch}'")
