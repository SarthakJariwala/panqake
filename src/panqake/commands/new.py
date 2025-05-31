"""Command for creating a new branch in the stack."""

import sys

from panqake.utils.config import add_to_stack
from panqake.utils.git import (
    branch_exists,
    create_branch,
    get_current_branch,
    list_all_branches,
    validate_branch,
)
from panqake.utils.questionary_prompt import (
    BranchNameValidator,
    format_branch,
    print_formatted_text,
    prompt_input,
)
from panqake.utils.status import status
from panqake.utils.types import BranchName


def create_new_branch(
    branch_name: BranchName | None = None, base_branch: BranchName | None = None
) -> None:
    """Create a new branch in the stack."""
    # If no branch name specified, prompt for it
    if not branch_name:
        validator = BranchNameValidator()
        branch_name = prompt_input("Enter new branch name: ", validator=validator)

    # If no base branch specified, use current branch but offer selection
    current = get_current_branch()
    if not base_branch:
        base_branch = current
        branches = list_all_branches()
        if branches:
            base_branch = prompt_input(
                f"Enter base branch [default: {current or ''}]: ",
                completer=branches,
                default=current or "",
            )

    with status("Creating new branch...") as s:
        # Check if the new branch already exists
        s.update("Checking if branch name is available...")
        if branch_exists(branch_name):
            s.pause_and_print(
                f"[warning]Error: Branch '{branch_name}' already exists[/warning]"
            )
            sys.exit(1)

        # Check if the base branch exists
        s.update("Validating base branch...")
        if base_branch:
            validate_branch(base_branch)
        else:
            s.pause_and_print("[danger]Error: Base branch is required[/danger]")
            sys.exit(1)

        # Create the new branch
        s.update(f"Creating branch '{branch_name}' from '{base_branch}'...")
        create_branch(branch_name, base_branch)

        # Record the dependency information
        s.update("Adding branch to stack metadata...")
        add_to_stack(branch_name, base_branch)

    print_formatted_text(
        f"[success]Success! Created new branch '{branch_name}' in the stack[/success]"
    )
    print_formatted_text(f"[info]Parent branch: {format_branch(base_branch)}[/info]")
