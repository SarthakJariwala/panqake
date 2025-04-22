"""Command for updating remote branches and pull requests."""

import shutil
import subprocess
import sys

from panqake.utils.git import branch_exists, get_current_branch
from panqake.utils.questionary_prompt import (
    format_branch,
    print_formatted_text,
    prompt_confirm,
)


def branch_has_pr(branch):
    """Check if a branch already has a PR."""
    try:
        subprocess.run(
            ["gh", "pr", "view", branch],
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        return True
    except subprocess.CalledProcessError:
        return False


def validate_branch(branch_name):
    """Validate branch exists and get current branch."""
    # If no branch specified, use current branch
    if not branch_name:
        branch_name = get_current_branch()

    # Check if target branch exists
    if not branch_exists(branch_name):
        print_formatted_text(
            f"<warning>Error: Branch '{branch_name}' does not exist</warning>"
        )
        sys.exit(1)

    return branch_name


def push_branch_to_remote(branch, force=False):
    """Push a branch to the remote."""
    try:
        print_formatted_text("<info>Pushing branch to origin...</info>")
        print_formatted_text(f"<branch>{branch}</branch>")
        print("")

        push_cmd = ["push", "-u", "origin", branch]
        if force:
            push_cmd.insert(1, "--force-with-lease")
            print_formatted_text(
                "<info>Using force-with-lease for safer force push</info>"
            )

        subprocess.run(
            ["git"] + push_cmd,
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )

        print_formatted_text("<success>Successfully pushed to origin</success>")
        print_formatted_text(f"<branch>{branch}</branch>")
        print("")
        return True
    except subprocess.CalledProcessError as e:
        error_message = e.stderr.decode("utf-8") if e.stderr else "Unknown error"
        print_formatted_text(
            f"<warning>Failed to push branch to origin: {error_message}</warning>"
        )
        return False


def update_pull_request(branch_name=None):
    """Update a remote branch and its associated PR."""
    # Check for GitHub CLI
    if not shutil.which("gh"):
        print_formatted_text(
            "<warning>Error: GitHub CLI (gh) is required but not installed.</warning>"
        )
        print_formatted_text(
            "<info>Please install GitHub CLI: https://cli.github.com</info>"
        )
        sys.exit(1)

    branch_name = validate_branch(branch_name)

    # Check if branch has a PR
    has_pr = branch_has_pr(branch_name)

    # Ask for confirmation for force push
    print_formatted_text("<info>This will update the remote branch</info>")
    print_formatted_text(f"<branch>{branch_name}</branch>")
    print("")
    if has_pr:
        print_formatted_text(
            "<info>The associated PR will also be updated for branch:</info>"
        )
        print_formatted_text(f"<branch>{branch_name}</branch>")
        print("")

    if not prompt_confirm("Do you want to proceed?"):
        print_formatted_text("<info>Update cancelled.</info>")
        return

    # Force push is needed when amending commits
    needs_force = prompt_confirm(
        "Did you amend or rewrite commits (requiring force push with lease)?",
    )

    # Push the branch to remote
    success = push_branch_to_remote(branch_name, force=needs_force)

    if success:
        if has_pr:
            print_formatted_text(
                f"<success>PR for {format_branch(branch_name)} has been updated</success>"
            )
        else:
            print_formatted_text(
                f"<info>Branch {format_branch(branch_name)} updated on remote. No PR exists yet.</info>"
            )
            print_formatted_text("<info>To create a PR, run:</info> ")
            print_formatted_text("<command>pq pr</command>")
            print("")
