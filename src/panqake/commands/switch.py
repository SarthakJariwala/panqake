"""Command for switching between Git branches."""

import sys

import questionary

from panqake.utils.git import get_current_branch, list_all_branches, run_git_command
from panqake.utils.questionary_prompt import print_formatted_text


def switch_branch(branch_name=None):
    """Switch to another git branch using interactive selection.

    Args:
        branch_name: Optional branch name to switch to directly.
                    If not provided, shows an interactive selection.
    """
    # Get all available branches
    branches = list_all_branches()

    if not branches:
        print_formatted_text("<warning>No branches found in repository</warning>")
        sys.exit(1)

    current = get_current_branch()

    # If branch name is provided, switch directly
    if branch_name:
        if branch_name not in branches:
            print_formatted_text(
                f"<warning>Error: Branch '{branch_name}' does not exist</warning>"
            )
            sys.exit(1)

        if branch_name == current:
            print_formatted_text(f"<info>Already on branch '{branch_name}'</info>")
            return

        _checkout_branch(branch_name)
        return

    # Format branches for display, marking the current branch
    choices = []
    for branch in branches:
        is_current = branch == current
        if is_current:
            # Add a special marker for the current branch
            choices.append(
                questionary.Choice(
                    title=f"* {branch} (current)",
                    value=branch,
                    disabled="current branch",
                )
            )
        else:
            choices.append(branch)

    # Show interactive branch selection
    selected = questionary.select(
        "Select a branch to switch to:",
        choices=choices,
    ).ask()

    if selected:
        if selected == current:
            print_formatted_text(f"<info>Already on branch '{selected}'</info>")
            return

        _checkout_branch(selected)


def _checkout_branch(branch_name):
    """Checkout to the specified branch."""
    print_formatted_text(f"<info>Switching to branch '{branch_name}'...</info>")
    result = run_git_command(["checkout", branch_name])

    if result is not None:
        print_formatted_text(
            f"<success>Successfully switched to branch '{branch_name}'</success>"
        )
    else:
        print_formatted_text("<danger>Failed to switch branches</danger>")
        sys.exit(1)
