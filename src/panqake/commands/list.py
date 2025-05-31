"""Command for listing branches in the stack."""

import sys

from panqake.utils.config import get_parent_branch
from panqake.utils.git import get_current_branch, validate_branch
from panqake.utils.questionary_prompt import format_branch, print_formatted_text
from panqake.utils.stack import Stacks


def find_stack_root(branch):
    """Find the root of the stack for a given branch."""
    parent = get_parent_branch(branch)

    if not parent:
        return branch
    else:
        return find_stack_root(parent)


def list_branches(branch_name=None):
    """List the branch stack."""
    # Validate branch exists and get current branch if none specified
    branch_name = validate_branch(branch_name)

    # Find the root of the stack for the target branch
    root_branch = find_stack_root(branch_name)

    current = get_current_branch()
    if not current:
        print_formatted_text(
            "[danger]Error: Could not determine current branch[/danger]"
        )
        sys.exit(1)

    print_formatted_text(
        f"[info]Branch stack (current: {format_branch(current, current=True)})[/info]"
    )

    # Use the Stacks.visualize_tree method to generate the tree
    stacks = Stacks()
    tree_output = stacks.visualize_tree(root=root_branch, current_branch=current)

    print_formatted_text(tree_output)
