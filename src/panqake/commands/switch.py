"""Command for switching between Git branches."""

import sys

from panqake.commands.list import list_branches
from panqake.utils.git import checkout_branch, get_current_branch, list_all_branches
from panqake.utils.questionary_prompt import print_formatted_text, prompt_select


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

        checkout_branch(branch_name)
        return

    # First show the branch hierarchy
    list_branches()
    print_formatted_text("")  # Add a blank line for better readability

    # Format branches for display, excluding the current branch
    choices = []
    for branch in branches:
        if branch != current:  # Skip the current branch
            branch_item = {"display": branch, "value": branch}
            choices.append(branch_item)

    # If no branches left after excluding current branch
    if not choices:
        print_formatted_text(
            "[warning]No other branches available to switch to[/warning]"
        )
        return

    # Show interactive branch selection using the prompt_select function
    selected = prompt_select(
        "Select a branch to switch to:",
        choices,
    )

    if selected:
        checkout_branch(selected)
        print_formatted_text("")
        # Show the branch hierarchy again
        list_branches()
