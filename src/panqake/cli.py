#!/usr/bin/env python3
"""
Panqake - Git Branch Stacking Utility
A Python implementation of git-stacking workflow management
"""

import sys

import rich_click as click

from panqake.commands.delete import delete_branch
from panqake.commands.list import list_branches
from panqake.commands.merge import merge_branch
from panqake.commands.modify import modify_commit
from panqake.commands.new import create_new_branch
from panqake.commands.pr import create_pull_requests
from panqake.commands.submit import update_pull_request
from panqake.commands.switch import switch_branch
from panqake.commands.sync import sync_with_remote
from panqake.commands.track import track
from panqake.commands.update import update_branches
from panqake.utils.config import init_panqake
from panqake.utils.git import is_git_repo, run_git_command
from panqake.utils.questionary_prompt import print_formatted_text

# Define known commands for passthrough handling
KNOWN_COMMANDS = [
    "new",
    "list",
    "ls",  # Alias for list
    "update",
    "delete",
    "pr",
    "switch",
    "co",  # Alias for switch
    "track",
    "modify",
    "submit",
    "merge",
    "sync",
    "--help",
    "-h",
]


@click.group(
    context_settings={
        "help_option_names": ["-h", "--help"],
        "ignore_unknown_options": True,
    }
)
def cli():
    """Panqake - Git Branch Stacking Utility"""
    pass


@cli.command()
@click.argument("branch_name", required=False)
@click.argument("base_branch", required=False)
def new(branch_name, base_branch):
    """Create a new branch in the stack.

    BRANCH_NAME: Name of the new branch

    BASE_BRANCH: Parent branch
    """
    create_new_branch(branch_name, base_branch)


@cli.command(name="list")
@click.argument("branch_name", required=False)
def list_command(branch_name):
    """List the branch stack.

    BRANCH_NAME: Optional branch to start from
    """
    list_branches(branch_name)


@cli.command(name="ls")
@click.argument("branch_name", required=False)
def ls_command(branch_name):
    """Alias for 'list' - List the branch stack.

    BRANCH_NAME: Optional branch to start from
    """
    list_branches(branch_name)


@cli.command()
@click.argument("branch_name", required=False)
@click.option(
    "--no-push",
    is_flag=True,
    help="Don't push changes to remote after updating branches",
)
def update(branch_name, no_push):
    """Update branches after changes and push to remote.

    BRANCH_NAME: Optional branch to start updating from
    """
    update_branches(branch_name, skip_push=no_push)


@cli.command()
@click.argument("branch_name")
def delete(branch_name):
    """Delete a branch and relink the stack.

    BRANCH_NAME: Name of the branch to delete
    """
    delete_branch(branch_name)


@cli.command()
@click.argument("branch_name", required=False)
def pr(branch_name):
    """Create PRs for the branch stack.

    BRANCH_NAME: Optional branch to start from
    """
    create_pull_requests(branch_name)


@cli.command()
@click.argument("branch_name", required=False)
def switch(branch_name):
    """Interactively switch between branches.

    BRANCH_NAME: Optional branch to switch to
    """
    switch_branch(branch_name)


@cli.command(name="co")
@click.argument("branch_name", required=False)
def co_command(branch_name):
    """Alias for 'switch' - Interactively switch between branches.

    BRANCH_NAME: Optional branch to switch to
    """
    switch_branch(branch_name)


@cli.command(name="track")
@click.argument("branch_name", required=False)
def track_branch(branch_name):
    """Track an existing Git branch in the panqake stack.

    BRANCH_NAME: Optional name of branch to track
    """
    track(branch_name)


@cli.command()
@click.option(
    "-c", "--commit", is_flag=True, help="Create a new commit instead of amending"
)
@click.option("-m", "--message", help="Commit message for the new or amended commit")
@click.option(
    "--no-amend", is_flag=True, help="Always create a new commit instead of amending"
)
def modify(commit, message, no_amend):
    """Modify/amend the current commit or create a new one."""
    modify_commit(commit, message, no_amend)


@cli.command(name="submit")
@click.argument("branch_name", required=False)
def submit(branch_name):
    """Update remote branch and PR after changes.

    BRANCH_NAME: Optional branch to update PR for
    """
    update_pull_request(branch_name)


@cli.command()
@click.argument("branch_name", required=False)
@click.option(
    "--no-delete-branch",
    is_flag=True,
    help="Don't delete the local branch after merging",
)
@click.option(
    "--no-update-children",
    is_flag=True,
    help="Don't update child branches after merging",
)
def merge(branch_name, no_delete_branch, no_update_children):
    """Merge a PR and manage the branch stack after merge.

    BRANCH_NAME: Optional branch to merge
    """
    merge_branch(branch_name, not no_delete_branch, not no_update_children)


@cli.command()
@click.argument("main_branch", required=False, default="main")
def sync(main_branch):
    """Sync branches with remote repository changes.

    MAIN_BRANCH: Base branch to sync with (default: main)
    """
    sync_with_remote(main_branch)


def main():
    """Main entry point for the panqake CLI."""
    # Initialize panqake directory and files
    init_panqake()

    # Check if we're in a git repository
    if not is_git_repo():
        click.echo("Error: Not in a git repository")
        sys.exit(1)

    # Check if any arguments were provided
    if len(sys.argv) <= 1:
        # No arguments, show help
        cli.main(args=["--help"])
        return

    # Get the first argument (potential command)
    potential_command = sys.argv[1]

    # If the potential command is known, use Click CLI
    if potential_command in KNOWN_COMMANDS:
        cli.main(standalone_mode=False)
    # Otherwise, pass all arguments to git
    else:
        print_formatted_text("[info]Passing command to git...[/info]")
        result = run_git_command(sys.argv[1:])
        if result is not None:
            click.echo(result)


if __name__ == "__main__":
    main()
