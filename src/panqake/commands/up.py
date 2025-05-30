"""Command for navigating to parent branch in stack."""

import sys

from panqake.utils.git import checkout_branch, get_current_branch
from panqake.utils.questionary_prompt import print_formatted_text
from panqake.utils.stack import Stacks
from panqake.utils.status import status


def up() -> None:
    """Navigate to the parent branch in the stack.

    If the current branch has no parent (e.g., main/master),
    informs the user and exits.
    """
    current_branch = get_current_branch()
    if not current_branch:
        print_formatted_text(
            "[danger]Error: Could not determine current branch[/danger]"
        )
        sys.exit(1)

    # Get the parent branch using the Stacks utility
    with Stacks() as stacks:
        parent = stacks.get_parent(current_branch)

        if not parent:
            print_formatted_text(
                f"[warning]Branch '{current_branch}' has no parent branch[/warning]"
            )
            sys.exit(1)

        print_formatted_text(f"[info]Moving up to parent branch: '{parent}'[/info]")
        with status(f"Switching to parent branch '{parent}'..."):
            checkout_branch(parent)
