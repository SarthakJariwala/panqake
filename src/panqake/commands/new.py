"""Command for creating a new branch in the stack."""

import sys

from panqake.utils.git import get_current_branch, branch_exists, run_git_command
from panqake.utils.config import add_to_stack


def create_new_branch(branch_name, base_branch=None):
    """Create a new branch in the stack."""
    # If no base branch specified, use current branch
    if not base_branch:
        base_branch = get_current_branch()

    # Check if the new branch already exists
    if branch_exists(branch_name):
        print(f"Error: Branch '{branch_name}' already exists")
        sys.exit(1)

    # Check if the base branch exists
    if base_branch and not branch_exists(base_branch):
        print(f"Error: Base branch '{base_branch}' does not exist")
        sys.exit(1)

    print(f"Creating new branch '{branch_name}' based on '{base_branch}'...")

    # Create the new branch
    result = run_git_command(["checkout", "-b", branch_name, base_branch])
    if result is None:
        print("Error: Failed to create new branch")
        sys.exit(1)

    # Record the dependency information
    add_to_stack(branch_name, base_branch)

    print(f"Success! Created new branch '{branch_name}' in the stack")
    print(f"Parent branch: {base_branch}")
