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
        new_name = prompt_input(f"Enter new name for branch '{old_name}': ", validator=validator)
    
    # First, check if the branch is tracked by panqake
    stacks = Stacks()
    is_tracked = stacks.branch_exists(old_name)
    
    if not is_tracked:
        print_formatted_text(
            f"[warning]Warning: Branch '{old_name}' is not tracked by panqake.[/warning]"
        )
        print_formatted_text(
            "[info]Only renaming the Git branch, no stack relationships to update.[/info]"
        )
        
        # Just rename the Git branch
        if rename_branch(old_name, new_name):
            sys.exit(0)
        else:
            sys.exit(1)
    
    # Rename in Git first
    if not rename_branch(old_name, new_name):
        print_formatted_text(
            f"[danger]Failed to rename branch '{old_name}' to '{new_name}'.[/danger]"
        )
        sys.exit(1)
    
    # Update stack references
    print_formatted_text(
        "[info]Updating branch references in stack configuration...[/info]"
    )
    
    if stacks.rename_branch(old_name, new_name):
        print_formatted_text(
            f"[success]Successfully updated stack references for '{new_name}'.[/success]"
        )
    else:
        print_formatted_text(
            f"[warning]Warning: Failed to update stack references for '{new_name}'.[/warning]"
        )
        print_formatted_text(
            f"[warning]Stack references may be inconsistent. Consider running 'pq untrack {new_name}' and 'pq track {new_name}' to fix.[/warning]"
        )