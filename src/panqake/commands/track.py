"""Command for tracking existing Git branches in the panqake stack."""

import sys

from panqake.utils.config import add_to_stack
from panqake.utils.git import get_current_branch, get_potential_parents
from panqake.utils.questionary_prompt import print_formatted_text
from panqake.utils.selection import select_parent_branch
from panqake.utils.status import status


def track(branch_name=None):
    """Track an existing Git branch in the panqake stack.

    This command allows tracking branches that were created outside of panqake
    (e.g., using vanilla git commands) by adding them to the stack tracking.
    The user will be prompted to select a parent branch from potential parents
    found in the branch's Git history.

    Args:
        branch_name: Optional branch name to track. If not provided, the current branch is used.
    """
    # Get the branch to track (current branch if not specified)
    if not branch_name:
        branch_name = get_current_branch()
        if not branch_name:
            print_formatted_text(
                "[warning]Could not determine the current branch.[/warning]"
            )
            sys.exit(1)

    print_formatted_text(
        f"[info]Tracking branch: [branch]{branch_name}[/branch][/info]"
    )

    with status("Analyzing branch history for potential parents...") as s:
        # Get potential parent branches from Git history
        s.update("Searching Git history for parent candidates...")
        potential_parents = get_potential_parents(branch_name)

        if not potential_parents:
            s.pause_and_print(
                f"[warning]No potential parent branches found in the history of '{branch_name}'.[/warning]"
            )
            s.pause_and_print(
                "[warning]Please ensure the branch you want to track has a suitable parent in its history.[/warning]"
            )
            sys.exit(1)

    # Prompt user to select a parent branch
    selected_parent = select_parent_branch(potential_parents)

    if not selected_parent:
        print_formatted_text("[warning]No parent branch selected. Aborting.[/warning]")
        sys.exit(1)

    # Add the branch to the stack with the selected parent
    with status("Adding branch to stack metadata..."):
        add_to_stack(branch_name, selected_parent)

    print_formatted_text(
        f"[success]Successfully added branch '{branch_name}' to the stack "
        f"with parent '{selected_parent}'.[/success]"
    )
