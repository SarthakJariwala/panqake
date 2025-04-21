"""Command for listing branches in the stack."""

import sys

from panqake.utils.config import get_child_branches, get_parent_branch
from panqake.utils.git import branch_exists, get_current_branch


def find_stack_root(branch):
    """Find the root of the stack for a given branch."""
    parent = get_parent_branch(branch)

    if not parent:
        return branch
    else:
        return find_stack_root(parent)


def print_branch_tree(branch, indent="", is_last_sibling=True):
    """Recursively print the branch tree."""
    current_branch = get_current_branch()
    is_current = branch == current_branch

    # Determine the connector for the current branch
    if indent:  # Not the root
        connector = "└── " if is_last_sibling else "├── "
    else:  # Root branch
        connector = ""

    # Format and print the current branch line
    prefix = f"{indent}{connector}"
    if is_current:
        # Apply branch styling using ANSI codes
        branch_display = f"* {branch}"
        # Print prefix first, then styled branch with ANSI codes
        print(f"{prefix}\033[92m{branch_display}\033[0m")
    else:
        # Non-current branches use default terminal text color
        print(f"{prefix}{branch}")

    # Prepare the indentation for children
    # Add a vertical bar if this branch is not the last sibling, otherwise add spaces
    child_indent = indent + ("    " if is_last_sibling else "│   ")

    # Get children of this branch
    children = get_child_branches(branch)
    num_children = len(children)

    if children:
        for i, child in enumerate(children):
            is_last_child = i == num_children - 1
            print_branch_tree(child, child_indent, is_last_child)


def list_branches(branch_name=None):
    """List the branch stack."""
    # If no branch specified, use current branch
    if not branch_name:
        branch_name = get_current_branch()

    # Check if target branch exists
    if not branch_exists(branch_name):
        # Use standard print with ANSI codes for warning style (yellow)
        print(f"\033[93mError: Branch '{branch_name}' does not exist\033[0m")
        sys.exit(1)

    # Find the root of the stack for the target branch
    root_branch = find_stack_root(branch_name)

    # Use standard print with ANSI codes for info style (cyan)
    print(f"\033[96mBranch stack (current: {get_current_branch()})\033[0m")

    # Initial call starts with no indent and assumes the root is the 'last sibling' conceptually
    print_branch_tree(root_branch, indent="", is_last_sibling=True)
