"""Command for untracking a branch from the panqake stack."""

import sys

from panqake.utils.config import remove_from_stack
from panqake.utils.git import get_current_branch
from panqake.utils.questionary_prompt import print_formatted_text


def untrack(branch_name=None):
    """Remove a branch from the panqake stack (does not delete the branch in git)."""
    if not branch_name:
        branch_name = get_current_branch()
        if not branch_name:
            print_formatted_text(
                "[warning]Could not determine the current branch.[/warning]"
            )
            sys.exit(1)

    print_formatted_text(
        f"[info]Untracking branch: [branch]{branch_name}[/branch][/info]"
    )
    if remove_from_stack(branch_name):
        print_formatted_text(
            f"Successfully removed branch '{branch_name}' from the stack."
        )
    else:
        print_formatted_text(
            f"[warning]Branch '{branch_name}' was not found in the stack.[/warning]"
        )
