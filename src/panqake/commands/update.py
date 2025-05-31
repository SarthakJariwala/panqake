"""Command for updating branches in the stack."""

from panqake.utils.branch_operations import (
    push_updated_branches,
    report_update_conflicts,
    return_to_branch,
    update_branches_and_handle_conflicts,
)
from panqake.utils.git import (
    get_current_branch,
    validate_branch,
)
from panqake.utils.questionary_prompt import (
    format_branch,
    print_formatted_text,
    prompt_confirm,
)
from panqake.utils.stack import Stacks
from panqake.utils.status import status
from panqake.utils.types import BranchName


def validate_branch_for_update(
    branch_name: BranchName | None,
) -> tuple[BranchName, BranchName | None]:
    """Validate branch exists and get current branch for update operation."""
    # Validate branch exists and get current branch if none specified
    validated_branch = validate_branch(branch_name)
    return validated_branch, get_current_branch()


def get_affected_branches(branch_name: BranchName) -> list[BranchName] | None:
    """Get affected branches and ask for confirmation."""
    with Stacks() as stacks:
        affected_branches = stacks.get_all_descendants(branch_name)

    # Show summary and ask for confirmation
    if affected_branches:
        print_formatted_text("[info]The following branches will be updated:[/info]")
        for branch in affected_branches:
            print_formatted_text(f"  {format_branch(branch)}")

        if not prompt_confirm("Do you want to proceed with the update?"):
            print_formatted_text("[info]Update cancelled.[/info]")
            return None
    else:
        print_formatted_text(
            f"[info]No child branches found for {format_branch(branch_name)}.[/info]"
        )
        return None

    return affected_branches


def update_branch_and_children(
    branch: BranchName, current_branch: BranchName | None
) -> tuple[list[BranchName], list[BranchName]]:
    """Update all child branches using a non-recursive approach.

    Args:
        branch: The branch to update children for
        current_branch: The original branch the user was on

    Returns:
        Tuple of (list of successfully updated branches, list of branches with conflicts)
    """

    if not current_branch:
        print_formatted_text(
            "[danger]Error: Could not determine current branch[/danger]"
        )
        return [], []
    return update_branches_and_handle_conflicts(branch, current_branch)


def update_branches(
    branch_name: BranchName | None = None, skip_push: bool = False
) -> tuple[bool, str | None]:
    """Update branches in the stack after changes and optionally push to remote.

    Args:
        branch_name: The branch to update children for, or None to use current branch
        skip_push: If True, don't push changes to remote after updating

    Returns:
        Tuple of (success_flag, error_message) or None
    """
    branch_name, current_branch = validate_branch_for_update(branch_name)

    affected_branches = get_affected_branches(branch_name)
    if affected_branches is None:
        return True, None  # No affected branches is not an error

    # Track successfully updated branches and branches with conflicts
    with status(f"Starting stack update from {branch_name}..."):
        updated_branches, conflict_branches = update_branch_and_children(
            branch_name, current_branch
        )

    # Push to remote if requested
    if not skip_push:
        push_updated_branches(updated_branches)

    # Return to the original branch using our utility function
    if current_branch and not return_to_branch(current_branch):
        return False, f"Failed to return to branch '{current_branch}'"

    # Report success
    if skip_push:
        print_formatted_text("[success]Stack update complete (local only).")
    else:
        print_formatted_text("[success]Stack update complete.[/success]")

    # Report overall success based on conflicts
    return report_update_conflicts(conflict_branches)
