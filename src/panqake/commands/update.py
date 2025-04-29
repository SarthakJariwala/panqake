"""Command for updating branches in the stack."""

import sys

from panqake.utils.branch_operations import (
    return_to_branch,
    update_branch_with_conflict_detection,
)
from panqake.utils.config import get_child_branches
from panqake.utils.git import (
    branch_exists,
    checkout_branch,
    get_current_branch,
    push_branch_to_remote,
)
from panqake.utils.github import (
    branch_has_pr,
    check_github_cli_installed,
)
from panqake.utils.questionary_prompt import (
    format_branch,
    print_formatted_text,
    prompt_confirm,
)


def collect_all_children(branch, result=None):
    """Recursively collect all child branches."""
    if result is None:
        result = []

    children = get_child_branches(branch)
    for child in children:
        if child not in result:
            result.append(child)
            collect_all_children(child, result)

    return result


def validate_branch(branch_name):
    """Validate branch exists and get current branch."""
    # If no branch specified, use current branch
    if not branch_name:
        branch_name = get_current_branch()

    # Check if target branch exists
    if not branch_exists(branch_name):
        print_formatted_text(
            f"[warning]Error: Branch '{branch_name}' does not exist[/warning]"
        )
        sys.exit(1)

    return branch_name, get_current_branch()


def get_affected_branches(branch_name):
    """Get affected branches and ask for confirmation."""
    affected_branches = collect_all_children(branch_name)

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


def update_branch_and_children(branch, current_branch, updated_branches=None):
    """Recursively update child branches.

    Args:
        branch: The branch to update children for
        current_branch: The original branch the user was on
        updated_branches: List to track successfully updated branches

    Returns:
        List of successfully updated branches
    """
    if updated_branches is None:
        updated_branches = []

    children = get_child_branches(branch)

    if children:
        for child in children:
            print_formatted_text(
                f"[info]Updating branch[/info] {format_branch(child)} "
                f"[info]based on changes to[/info] {format_branch(branch)}..."
            )

            # Use utility function to update the branch with conflict detection
            success, error_msg = update_branch_with_conflict_detection(
                child, branch, abort_on_conflict=False
            )

            if not success:
                print_formatted_text(f"[warning]{error_msg}[/warning]")
                print_formatted_text(
                    f"[warning]Then run 'pq update {child}' to continue updating the stack[/warning]"
                )
                sys.exit(1)

            # Add to successfully updated branches
            updated_branches.append(child)

            # Continue with children of this branch
            update_branch_and_children(child, current_branch, updated_branches)

    return updated_branches


def update_branches(branch_name=None, skip_push=False):
    """Update branches in the stack after changes and optionally push to remote.

    Args:
        branch_name: The branch to update children for, or None to use current branch
        skip_push: If True, don't push changes to remote after updating
    """
    branch_name, current_branch = validate_branch(branch_name)

    affected_branches = get_affected_branches(branch_name)
    if affected_branches is None:
        return

    # Start the update process
    print_formatted_text(
        f"[info]Starting stack update from branch[/info] {format_branch(branch_name)}..."
    )

    # Track successfully updated branches
    updated_branches = update_branch_and_children(branch_name, current_branch)

    # Push to remote if requested (new functionality)
    if not skip_push and updated_branches:
        print_formatted_text("[info]Pushing updated branches to remote...[/info]")

        # Check for GitHub CLI if we want to display PR info
        has_github_cli = check_github_cli_installed()
        if not has_github_cli:
            print_formatted_text(
                "[info]GitHub CLI not installed. Will push to remote but can't update PR info.[/info]"
            )

        # Push each branch that was successfully updated
        for branch in updated_branches:
            # Always use force-with-lease for safety since we've rebased
            checkout_branch(branch)

            success = push_branch_to_remote(branch, force=True)

            if success:
                if has_github_cli and branch_has_pr(branch):
                    print_formatted_text(
                        f"[success]PR for {format_branch(branch)} has been updated[/success]"
                    )
                else:
                    print_formatted_text(
                        f"[success]Branch {format_branch(branch)} pushed to remote[/success]"
                    )

    # Return to the original branch using our utility function
    return_to_branch(current_branch)

    if skip_push:
        print_formatted_text(
            f"[success]Stack update complete (local only). Returned to branch {format_branch(current_branch)}[/success]"
        )
    else:
        print_formatted_text(
            "[success]Stack update complete (local and remote).[/success]"
        )
        print_formatted_text(f"[success]Returned to branch {current_branch}[/success]")
