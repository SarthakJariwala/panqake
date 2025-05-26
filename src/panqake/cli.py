#!/usr/bin/env python3
"""
Panqake - Git Branch Stacking Utility
A Python implementation of git-stacking workflow management
"""

import sys

import typer
from rich.console import Console

from panqake.commands.delete import delete_branch
from panqake.commands.down import down as down_command
from panqake.commands.list import list_branches
from panqake.commands.merge import merge_branch
from panqake.commands.modify import modify_commit
from panqake.commands.new import create_new_branch
from panqake.commands.pr import create_pull_requests
from panqake.commands.rename import rename as rename_branch
from panqake.commands.submit import update_pull_request
from panqake.commands.switch import switch_branch
from panqake.commands.sync import sync_with_remote
from panqake.commands.track import track
from panqake.commands.untrack import untrack
from panqake.commands.up import up as up_command
from panqake.commands.update import update_branches
from panqake.utils.config import init_panqake
from panqake.utils.git import is_git_repo, run_git_command
from panqake.utils.questionary_prompt import print_formatted_text

# Define known commands for passthrough handling
# These are commands/options that Typer itself might not list in app.registered_commands
# or app.registered_groups but should prevent git passthrough.
# Typer handles --help and -h for the app and subcommands automatically if they are defined.
# We only need to ensure that if these are passed as sys.argv[1], our logic lets Typer handle them.
KNOWN_COMMANDS = ["--help", "-h"]

app = typer.Typer(
    rich_markup_mode="markdown",
    context_settings={"help_option_names": ["-h", "--help"]},
    no_args_is_help=True,
    add_completion=False,
    name="panqake",
    help="Panqake - Git Branch Stacking Utility",
)
console = Console()

# All commands will be registered directly on the main 'app'


@app.command(name="list", help="List the branch stack.")
def list_command(
    branch_name: str = typer.Argument(None, help="Optional branch to start from"),
):
    """List the branch stack. (Longer description from docstring)"""
    list_branches(branch_name)


@app.command(help="Create a new branch in the stack.")
def new(
    branch_name: str = typer.Argument(None, help="Name of the new branch"),
    base_branch: str = typer.Argument(None, help="Parent branch"),
):
    """Create a new branch in the stack. (Longer description from docstring)"""
    create_new_branch(branch_name, base_branch)


@app.command(name="ls", help="Alias for 'list' - List the branch stack.")
def ls_command(
    branch_name: str = typer.Argument(None, help="Optional branch to start from"),
):
    """Alias for 'list' - List the branch stack. (Longer description from docstring)"""
    list_branches(branch_name)


@app.command(help="Update branches after changes and push to remote.")
def update(
    branch_name: str = typer.Argument(
        None, help="Optional branch to start updating from"
    ),
    no_push: bool = typer.Option(
        False, "--no-push", help="Don't push changes to remote after updating branches"
    ),
):
    """Update branches after changes and push to remote. (Longer description from docstring)"""
    update_branches(branch_name, skip_push=no_push)


@app.command(help="Delete a branch and relink the stack.")
def delete(branch_name: str = typer.Argument(..., help="Name of the branch to delete")):
    """Delete a branch and relink the stack. (Longer description from docstring)"""
    delete_branch(branch_name)


@app.command(help="Create PRs for the branch stack.")
def pr(branch_name: str = typer.Argument(None, help="Optional branch to start from")):
    """Create PRs for the branch stack. (Longer description from docstring)"""
    create_pull_requests(branch_name)


@app.command(help="Interactively switch between branches.")
def switch(
    branch_name: str = typer.Argument(None, help="Optional branch to switch to"),
):
    """Interactively switch between branches. (Longer description from docstring)"""
    switch_branch(branch_name)


@app.command(
    name="co", help="Alias for 'switch' - Interactively switch between branches."
)
def co_command(
    branch_name: str = typer.Argument(None, help="Optional branch to switch to"),
):
    """Alias for 'switch' - Interactively switch between branches. (Longer description from docstring)"""
    switch_branch(branch_name)


@app.command(name="track", help="Track an existing Git branch in the panqake stack.")
def track_branch(
    branch_name: str = typer.Argument(None, help="Optional name of branch to track"),
):
    """Track an existing Git branch in the panqake stack. (Longer description from docstring)"""
    track(branch_name)


@app.command(name="untrack", help="Untrack a branch (does not delete git branch).")
def untrack_branch(
    branch_name: str = typer.Argument(None, help="Optional name of branch to untrack"),
):
    """Remove a branch from the panqake stack (does not delete the git branch). (Longer description from docstring)"""
    untrack(branch_name)


@app.command(help="Modify/amend the current commit or create a new one.")
def modify(
    commit: bool = typer.Option(
        False, "-c", "--commit", help="Create a new commit instead of amending"
    ),
    message: str = typer.Option(
        None, "-m", "--message", help="Commit message for the new or amended commit"
    ),
    no_amend: bool = typer.Option(
        False, "--no-amend", help="Always create a new commit instead of amending"
    ),
):
    """Modify/amend the current commit or create a new one. (Longer description from docstring)"""
    modify_commit(commit, message, no_amend)


@app.command(name="submit", help="Update remote branch and PR after changes.")
def submit(
    branch_name: str = typer.Argument(None, help="Optional branch to update PR for"),
):
    """Update remote branch and PR after changes. (Longer description from docstring)"""
    update_pull_request(branch_name)


@app.command(help="Merge a PR and manage the branch stack after merge.")
def merge(
    branch_name: str = typer.Argument(None, help="Optional branch to merge"),
    no_delete_branch: bool = typer.Option(
        False, "--no-delete-branch", help="Don't delete the local branch after merging"
    ),
    no_update_children: bool = typer.Option(
        False,
        "--no-update-children",
        help="Don't update child branches after merging",
    ),
):
    """Merge a PR and manage the branch stack after merge. (Longer description from docstring)"""
    merge_branch(branch_name, not no_delete_branch, not no_update_children)


@app.command(help="Sync branches with remote repository changes.")
def sync(
    main_branch: str = typer.Argument(
        "main", help="Base branch to sync with (default: main)"
    ),  # Added default to help
    no_push: bool = typer.Option(
        False, "--no-push", help="Skip pushing updated branches to remote"
    ),
):
    """Sync branches with remote repository changes. (Longer description from docstring)"""
    sync_with_remote(main_branch, skip_push=no_push)


@app.command(help="Rename a branch while maintaining stack relationships.")
def rename(
    old_name: str = typer.Argument(
        None, help="Current name of the branch to rename (default: current branch)"
    ),
    new_name: str = typer.Argument(
        None, help="New name for the branch (if not provided, will prompt)"
    ),
):
    """Rename a branch while maintaining stack relationships. (Longer description from docstring)"""
    rename_branch(old_name, new_name)


@app.command(help="Navigate to the parent branch in the stack.")
def up():
    """Navigate to the parent branch in the stack. (Longer description from docstring)

    Move up from the current branch to its closest ancestor.
    If there is no parent branch, informs the user.
    """
    up_command()


@app.command(help="Navigate to a child branch in the stack.")
def down():
    """Navigate to a child branch in the stack. (Longer description from docstring)

    Move down from the current branch to a child branch.
    If there are multiple children, prompts for selection.
    If there are no children, informs the user.
    """
    down_command()


def main():
    """Main entry point for the panqake CLI."""
    # Initialize panqake directory and files
    init_panqake()

    # Check if we're in a git repository
    if not is_git_repo():
        console.print("Error: Not in a git repository")
        sys.exit(1)

    # Check if any arguments were provided and if the command is known
    # Typer automatically handles help for no args or --help
    # We need to handle the git passthrough for unknown commands.

    # Build a set of all known Typer command names (including subcommand names like "nav list")
    # and group names.
    all_typer_commands_and_groups = set(KNOWN_COMMANDS)

    # Add top-level command names
    for cmd_info in app.registered_commands:
        all_typer_commands_and_groups.add(cmd_info.name)
        # Typer's CommandInfo doesn't directly expose aliases in a simple list.
        # Aliases are often handled by Typer by registering multiple command names
        # pointing to the same callback. If aliases need to be specifically enumerated here
        # beyond what KNOWN_COMMANDS covers, a different approach for alias detection
        # might be needed, or ensure aliases are in KNOWN_COMMANDS if not primary names.

    # Add group names and command names within groups
    # With a flat structure, there are no registered_groups to iterate for commands.
    # for group_info in app.registered_groups:
    #     all_typer_commands_and_groups.add(group_info.name)
    #     if group_info.typer_instance:
    #         for cmd_info_in_group in group_info.typer_instance.registered_commands:
    #             all_typer_commands_and_groups.add(cmd_info_in_group.name)

    if len(sys.argv) > 1:
        potential_command = sys.argv[1]
        # If the first argument is an option (starts with '-'), let Typer handle it.
        # Otherwise, if it's not a recognized Typer command/group, pass to git.
        if (
            not potential_command.startswith("-")
            and potential_command not in all_typer_commands_and_groups
        ):
            print_formatted_text("[info]Passing command to git...[/info]")
            result = run_git_command(sys.argv[1:])
            if result is not None:
                console.print(result)
            return  # Exit after passing to git

    app()


if __name__ == "__main__":
    main()
