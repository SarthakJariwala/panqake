"""Command for listing branches in the stack."""

import sys

from panqake.utils.config import get_child_branches, get_parent_branch
from panqake.utils.git import branch_exists, get_current_branch
from panqake.utils.questionary_prompt import format_branch, print_formatted_text


def find_stack_root(branch):
    """Find the root of the stack for a given branch."""
    parent = get_parent_branch(branch)

    if not parent:
        return branch
    else:
        return find_stack_root(parent)


def print_branch_tree(branch, indent="", is_last_sibling=True):
    """Recursively print the branch tree using Rich markup."""
    current_branch_name = get_current_branch()
    is_current = branch == current_branch_name

    # Determine the connector for the current branch
    if indent:  # Not the root
        connector = "└── " if is_last_sibling else "├── "
    else:  # Root branch
        connector = ""

    # Format the branch name using the updated format_branch function
    branch_display = format_branch(branch, current=is_current)

    # Print the line using print_formatted_text
    print_formatted_text(f"{indent}{connector}{branch_display}")

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
        print_formatted_text(
            f"[warning]Error: Branch '{branch_name}' does not exist[/warning]"
        )
        sys.exit(1)

    # Find the root of the stack for the target branch
    root_branch = find_stack_root(branch_name)

    current = get_current_branch()
    print_formatted_text(
        f"[info]Branch stack (current: {format_branch(current, current=True)})[/info]"
    )

    # Initial call starts with no indent and assumes the root is the 'last sibling' conceptually
    print_branch_tree(root_branch, indent="", is_last_sibling=True)
