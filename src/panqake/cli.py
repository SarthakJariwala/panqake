"""
Panqake - CLI for Git stacking
A Python implementation of git-stacking workflow management
"""

import sys

import typer
from rich.console import Console
from typer.core import TyperGroup

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
    "untrack",
    "rename",
    "modify",
    "submit",
    "merge",
    "sync",
    "up",
    "down",
    "--help",
    "-h",
]

# Create Rich console for output
console = Console()


# Create a custom TyperGroup to handle unknown commands
class PanqakeGroup(TyperGroup):
    def get_command(self, ctx, cmd_name):
        return super().get_command(ctx, cmd_name)


# Initialize the Typer app
app = typer.Typer(
    name="panqake",
    help="Panqake - CLI for Git stacking",
    cls=PanqakeGroup,
    rich_markup_mode="rich",
    context_settings={"help_option_names": ["-h", "--help"]},
    add_completion=True,
)


@app.command()
def new(
    branch_name: str | None = typer.Argument(None, help="Name of the new branch"),
    base_branch: str | None = typer.Argument(None, help="Parent branch"),
):
    """Create a new branch in the stack."""
    create_new_branch(branch_name, base_branch)


@app.command(name="list")
def list_command(
    branch_name: str | None = typer.Argument(
        None, help="Optional branch to start from"
    ),
):
    """List the branch stack."""
    list_branches(branch_name)


@app.command(name="ls")
def ls_command(
    branch_name: str | None = typer.Argument(
        None, help="Optional branch to start from"
    ),
):
    """Alias for 'list' - List the branch stack."""
    list_branches(branch_name)


@app.command()
def update(
    branch_name: str | None = typer.Argument(
        None, help="Optional branch to start updating from"
    ),
    push: bool = typer.Option(
        True, help="Push changes to remote after updating branches"
    ),
):
    """Update branches after changes and push to remote."""
    update_branches(branch_name, skip_push=not push)


@app.command()
def delete(
    branch_name: str = typer.Argument(..., help="Name of the branch to delete"),
):
    """Delete a branch and relink the stack."""
    delete_branch(branch_name)


@app.command()
def pr(
    branch_name: str | None = typer.Argument(
        None, help="Optional branch to start from"
    ),
    draft: bool = typer.Option(False, "--draft", help="Create PRs as drafts"),
):
    """Create PRs for the branch stack."""
    create_pull_requests(branch_name, draft=draft)


@app.command()
def switch(
    branch_name: str | None = typer.Argument(None, help="Optional branch to switch to"),
):
    """Interactively switch between branches."""
    switch_branch(branch_name)


@app.command(name="co")
def co_command(
    branch_name: str | None = typer.Argument(None, help="Optional branch to switch to"),
):
    """Alias for 'switch' - Interactively switch between branches."""
    switch_branch(branch_name)


@app.command(name="track")
def track_branch(
    branch_name: str | None = typer.Argument(
        None, help="Optional name of branch to track"
    ),
):
    """Track an existing Git branch in the panqake stack."""
    track(branch_name)


@app.command(name="untrack")
def untrack_branch(
    branch_name: str | None = typer.Argument(
        None, help="Optional name of branch to untrack"
    ),
):
    """Remove a branch from the panqake stack (does not delete the git branch)."""
    untrack(branch_name)


@app.command()
def modify(
    commit: bool = typer.Option(
        False, "-c", "--commit", help="Create a new commit instead of amending"
    ),
    message: str | None = typer.Option(
        None,
        "-m",
        "--message",
        help="Commit message for the new or amended commit",
    ),
    amend: bool = typer.Option(True, help="Amend the current commit if possible"),
):
    """Modify/amend the current commit or create a new one."""
    modify_commit(commit, message, no_amend=not amend)


@app.command(name="submit")
def submit(
    branch_name: str | None = typer.Argument(
        None, help="Optional branch to update PR for"
    ),
):
    """Update remote branch and PR after changes."""
    update_pull_request(branch_name)


@app.command()
def merge(
    branch_name: str | None = typer.Argument(None, help="Optional branch to merge"),
    delete_branch: bool = typer.Option(
        True, help="Delete the local branch after merging"
    ),
    update_children: bool = typer.Option(
        True, help="Update child branches after merging"
    ),
):
    """Merge a PR and manage the branch stack after merge."""
    merge_branch(branch_name, delete_branch, update_children)


@app.command()
def sync(
    main_branch: str = typer.Argument(
        "main", help="Base branch to sync with (default: main)"
    ),
    push: bool = typer.Option(
        True, help="Push changes to remote after syncing branches"
    ),
):
    """Sync branches with remote repository changes."""
    sync_with_remote(main_branch, skip_push=not push)


@app.command()
def rename(
    old_name: str | None = typer.Argument(
        None,
        help="Current name of the branch to rename (default: current branch)",
    ),
    new_name: str | None = typer.Argument(
        None, help="New name for the branch (if not provided, will prompt)"
    ),
):
    """Rename a branch while maintaining stack relationships."""
    rename_branch(old_name, new_name)


@app.command()
def up():
    """Navigate to the parent branch in the stack.

    Move up from the current branch to its closest ancestor.
    If there is no parent branch, informs the user.
    """
    up_command()


@app.command()
def down():
    """Navigate to a child branch in the stack.

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
        console.print("Error: Not in a git repository", style="bold red")
        sys.exit(1)

    # Check if any arguments were provided
    if len(sys.argv) <= 1:
        # No arguments, show help
        app(["-h"])
        return

    # Get the first argument (potential command)
    potential_command = sys.argv[1]

    # If the potential command is known, use Typer app
    if potential_command in KNOWN_COMMANDS:
        app()
    # Otherwise, pass all arguments to git
    else:
        print_formatted_text("[info]Passing command to git...[/info]")
        result = run_git_command(sys.argv[1:])
        if result is not None:
            console.print(result)


if __name__ == "__main__":
    main()
