"""Command for listing branches in the stack."""

import sys

from panqake.utils.config import get_child_branches, get_parent_branch
from panqake.utils.git import branch_exists, get_current_branch
from panqake.utils.questionary_prompt import print_formatted_text


def find_stack_root(branch):
    """Find the root of the stack for a given branch."""
    parent = get_parent_branch(branch)

    if not parent:
        return branch
    else:
        return find_stack_root(parent)


def print_branch_tree(branch, prefix="", is_last=True):
    """Recursively print the branch tree."""
    current_branch = get_current_branch()
    is_current = branch == current_branch

    # Format the branch with prefix
    if is_current:
        branch_display = f"{prefix} * {branch}"
    else:
        branch_display = f"{prefix}   {branch}"

    # Print with appropriate style
    if is_current:
        print_formatted_text(f"<branch>{branch_display}</branch>")
    else:
        print(branch_display)

    # Get children of this branch
    children = get_child_branches(branch)

    if children:
        for i, child in enumerate(children):
            is_child_last = i == len(children) - 1

            if is_child_last:
                # Last child gets a different connector
                child_prefix = f"{prefix}  └──"
            else:
                # Not the last child
                child_prefix = f"{prefix}  ├──"

            print_branch_tree(child, child_prefix, is_child_last)


def list_branches(branch_name=None):
    """List the branch stack."""
    # If no branch specified, use current branch
    if not branch_name:
        branch_name = get_current_branch()

    # Check if target branch exists
    if not branch_exists(branch_name):
        print_formatted_text(
            f"<warning>Error: Branch '{branch_name}' does not exist</warning>"
        )
        sys.exit(1)

    # Find the root of the stack for the target branch
    root_branch = find_stack_root(branch_name)

    print_formatted_text(f"<info>Branch stack (current: {get_current_branch()})</info>")
    print_branch_tree(root_branch)
