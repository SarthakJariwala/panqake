"""Command for renaming a branch while maintaining stack relationships."""

import sys
from typing import Optional

from panqake.utils.git import get_current_branch, rename_branch
from panqake.utils.questionary_prompt import (
    BranchNameValidator,
    print_formatted_text,
    prompt_input,
)
from panqake.utils.stack import Stacks
from panqake.utils.status import status


def rename(old_name: Optional[str] = None, new_name: Optional[str] = None):
    """Rename a branch while maintaining its stack relationships.

    This command renames a Git branch and updates all stack references to ensure
    parent-child relationships are preserved in the stack configuration.

    Args:
        old_name: The current name of the branch to rename. If not provided,
                 the current branch will be used.
        new_name: The new name for the branch. If not provided, user will be prompted.
    """
    # Get the branch to rename (current branch if not specified)
    if not old_name:
        old_name = get_current_branch()
        if not old_name:
            print_formatted_text(
                "[warning]Could not determine the current branch.[/warning]"
            )
            sys.exit(1)

    # If no new branch name specified, prompt for it
    if not new_name:
        validator = BranchNameValidator()
        new_name = prompt_input(
            f"Enter new name for branch '{old_name}': ", validator=validator
        )

    with status("Analyzing branch for rename...") as s:
        # First, check if the branch is tracked by panqake
        s.update("Checking if branch is tracked by panqake...")
        stacks = Stacks()
        is_tracked = stacks.branch_exists(old_name)

        if not is_tracked:
            s.pause_and_print(
                f"[warning]Warning: Branch '{old_name}' is not tracked by panqake.[/warning]"
            )
            s.pause_and_print(
                "[info]Only renaming the Git branch, no stack relationships to update.[/info]"
            )

            # Just rename the Git branch and exit
            if rename_branch(old_name, new_name):
                sys.exit(0)
            else:
                sys.exit(1)

        # Rename the Git branch first
        s.update("Renaming Git branch...")
        if not rename_branch(old_name, new_name):
            s.pause_and_print(
                f"[error]Failed to rename Git branch from '{old_name}' to '{new_name}'.[/error]"
            )
            sys.exit(1)

        # Update stack references
        s.update("Updating stack references...")

        if stacks.rename_branch(old_name, new_name):
            s.pause_and_print(
                f"[success]Successfully updated stack references for '{new_name}'.[/success]"
            )
        else:
            s.pause_and_print(
                f"[warning]Warning: Failed to update stack references for '{new_name}'.[/warning]"
            )
            s.pause_and_print(
                f"[warning]Stack references may be inconsistent. Consider running 'pq untrack {new_name}' and 'pq track {new_name}' to fix.[/warning]"
            )
