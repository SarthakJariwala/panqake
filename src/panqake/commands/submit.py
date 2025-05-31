"""Command for updating remote branches and pull requests."""

import sys

from panqake.commands.pr import create_pr_for_branch
from panqake.utils.config import get_parent_branch
from panqake.utils.git import (
    is_force_push_needed,
    is_last_commit_amended,
    push_branch_to_remote,
    validate_branch,
)
from panqake.utils.github import (
    branch_has_pr,
    check_github_cli_installed,
    get_pr_url,
)
from panqake.utils.questionary_prompt import (
    format_branch,
    print_formatted_text,
    prompt_confirm,
)
from panqake.utils.status import status


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

    with status("Analyzing branch status...") as s:
        # Check if the last commit was amended
        s.update("Checking for amended commits...")
        is_amended = is_last_commit_amended()

        # Determine if force push is needed
        needs_force = is_amended

        # If we didn't detect an amended commit, check if a non-fast-forward issue would occur
        if not needs_force:
            s.update("Checking if force push is needed...")
            needs_force = is_force_push_needed(branch_name)
            if needs_force:
                s.pause_and_print(
                    "[info]Detected non-fast-forward update. Force push with lease will be used.[/info]"
                )

        # Push the branch to remote
        push_type = "force push with lease" if needs_force else "push"
        s.update(f"Performing {push_type} to remote...")
        success = push_branch_to_remote(branch_name, force_with_lease=needs_force)

    if success:
        if branch_has_pr(branch_name):
            print_formatted_text(
                f"[success]PR for {format_branch(branch_name)} has been updated[/success]"
            )
            # Display PR URL if available
            pr_url = get_pr_url(branch_name)
            if pr_url:
                print_formatted_text(f"[info]Pull request URL: {pr_url}[/info]")
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
