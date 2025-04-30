"""Command for updating remote branches and pull requests."""

import sys

from panqake.commands.pr import create_pr_for_branch
from panqake.utils.config import get_parent_branch
from panqake.utils.git import (
    push_branch_to_remote,
    validate_branch,
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


def update_pull_request(branch_name=None):
    """Update a remote branch and its associated PR."""
    # Check for GitHub CLI
    if not check_github_cli_installed():
        print_formatted_text(
            "[warning]Error: GitHub CLI (gh) is required but not installed.[/warning]"
        )
        print_formatted_text(
            "[info]Please install GitHub CLI: https://cli.github.com[/info]"
        )
        sys.exit(1)

    branch_name = validate_branch(branch_name)

    # Check if branch has a PR
    has_pr = branch_has_pr(branch_name)

    # Ask for confirmation for force push
    print_formatted_text(
        f"[info]Updating remote branch [branch]{branch_name}[/branch][/info]"
    )
    if has_pr:
        print_formatted_text(
            f"[info]The associated PR will also be updated for branch: [branch]{branch_name}[/branch][/info]"
        )

    # Force push is needed when amending commits
    needs_force = prompt_confirm(
        "Approve force push with lease? (Required if you amended or rewrote commits)"
    )

    # Push the branch to remote
    success = push_branch_to_remote(branch_name, force=needs_force)

    if success:
        if has_pr:
            print_formatted_text(
                f"[success]PR for {format_branch(branch_name)} has been updated[/success]"
            )
        else:
            print_formatted_text(
                f"[info]Branch {format_branch(branch_name)} updated on remote. No PR exists yet.[/info]"
            )
            if prompt_confirm("Do you want to create a PR?"):
                # Create a PR if the user confirms
                parent = get_parent_branch(branch_name)
                create_pr_for_branch(branch_name, parent)
            else:
                print_formatted_text("[info]To create a PR, run: pq pr[/info]")
