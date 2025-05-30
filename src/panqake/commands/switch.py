"""Command for switching between Git branches."""

import sys

from panqake.commands.list import list_branches
from panqake.utils.git import checkout_branch, get_current_branch, list_all_branches
from panqake.utils.questionary_prompt import print_formatted_text
from panqake.utils.selection import select_branch_excluding_current
from panqake.utils.status import status


def switch_branch(branch_name=None):
    """Switch to another git branch using interactive selection.

    Args:
        branch_name: Optional branch name to switch to directly.
                    If not provided, shows an interactive selection.
    """
    # Get all available branches
    branches = list_all_branches()

    if not branches:
        print_formatted_text("[warning]No branches found in repository[/warning]")
        sys.exit(1)

    current = get_current_branch()

    # If branch name is provided, switch directly
    if branch_name:
        if branch_name not in branches:
            print_formatted_text(
                f"[warning]Error: Branch '{branch_name}' does not exist[/warning]"
            )
            sys.exit(1)

        if branch_name == current:
            print_formatted_text(f"[info]Already on branch '{branch_name}'[/info]")
            return

        with status(f"Switching to branch '{branch_name}'..."):
            checkout_branch(branch_name)
        return

    # First show the branch hierarchy
    list_branches()
    print_formatted_text("")  # Add a blank line for better readability

    # Use shared utility for branch selection
    selected = select_branch_excluding_current(
        "Select a branch to switch to:", exclude_protected=False, enable_search=True
    )

    # If no selection made or no branches available
    if not selected:
        print_formatted_text(
            "[warning]No other branches available to switch to[/warning]"
        )
        return

    if selected:
        with status(f"Switching to branch '{selected}'..."):
            checkout_branch(selected)
        print_formatted_text("")
        # Show the branch hierarchy again
        list_branches()
