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
from panqake.ports.exceptions import GitOperationError
from panqake.ports.helpers import _emit_json_error
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

COMMAND_ALIASES = {
    "ls": "list",
    "co": "switch",
}


def _json_requested(argv: list[str]) -> bool:
    """Check if --json mode was requested."""
    return "--json" in argv


def _normalized_app_argv(argv: list[str]) -> list[str] | None:
    """Normalize argv for Typer when dispatching a panqake command.

    Supports command-first invocations directly and rewrites leading `--json`
    invocations like `pq --json list` to `pq list --json`.
    """
    if not argv:
        return None

    first = argv[0]
    if first in KNOWN_COMMANDS:
        return argv

    # Support leading JSON flags before a subcommand.
    json_count = 0
    while json_count < len(argv) and argv[json_count] == "--json":
        json_count += 1

    if json_count == 0 or json_count >= len(argv):
        return None

    command = argv[json_count]
    if command not in KNOWN_COMMANDS:
        return None

    if command in {"-h", "--help"}:
        return [command]

    return [command, *argv[:json_count], *argv[json_count + 1 :]]


def _requested_command(argv: list[str]) -> str | None:
    """Extract requested panqake command name from argv, if resolvable."""
    normalized_argv = _normalized_app_argv(argv)
    if not normalized_argv:
        return None

    command = normalized_argv[0]
    if command.startswith("-"):
        return None

    return COMMAND_ALIASES.get(command, command)


# Create Rich console for output
console = Console()

# Reusable --json option for all commands
JSON_OPTION = typer.Option(False, "--json", help="Output machine-readable JSON")


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
    tree: bool = typer.Option(False, "--tree", help="Create branch in a new worktree"),
    path: str | None = typer.Option(
        None, "--path", "-p", help="Custom path for the worktree (implies --tree)"
    ),
    json: bool = JSON_OPTION,
):
    """Create a new branch in the stack."""
    use_worktree = tree or path is not None
    create_new_branch(branch_name, base_branch, use_worktree, path, json_output=json)


@app.command(name="list")
def list_command(
    branch_name: str | None = typer.Argument(
        None, help="Optional branch to start from"
    ),
    files: bool = typer.Option(
        False, "-f", "--files", help="Show files changed in each branch"
    ),
    json: bool = JSON_OPTION,
):
    """List the branch stack."""
    list_branches(branch_name, json_output=json, show_files=files)


@app.command(name="ls")
def ls_command(
    branch_name: str | None = typer.Argument(
        None, help="Optional branch to start from"
    ),
    files: bool = typer.Option(
        False, "-f", "--files", help="Show files changed in each branch"
    ),
    json: bool = JSON_OPTION,
):
    """Alias for 'list' - List the branch stack."""
    list_branches(branch_name, json_output=json, show_files=files)


@app.command()
def update(
    branch_name: str | None = typer.Argument(
        None, help="Optional branch to start updating from"
    ),
    push: bool = typer.Option(
        True, help="Push changes to remote after updating branches"
    ),
    yes: bool = typer.Option(False, "--yes", "-y", help="Skip confirmation prompts"),
    json: bool = JSON_OPTION,
):
    """Update branches after changes and push to remote."""
    update_branches(branch_name, skip_push=not push, assume_yes=yes, json_output=json)


@app.command()
def delete(
    branch_name: str = typer.Argument(..., help="Name of the branch to delete"),
    yes: bool = typer.Option(False, "--yes", "-y", help="Skip confirmation prompts"),
    json: bool = JSON_OPTION,
):
    """Delete a branch and relink the stack."""
    delete_branch(branch_name, assume_yes=yes, json_output=json)


@app.command()
def pr(
    branch_name: str | None = typer.Argument(
        None, help="Optional branch to start from"
    ),
    draft: bool = typer.Option(False, "--draft", help="Create PRs as drafts"),
    json: bool = JSON_OPTION,
):
    """Create PRs for the branch stack."""
    create_pull_requests(branch_name, draft=draft, json_output=json)


@app.command()
def switch(
    branch_name: str | None = typer.Argument(None, help="Optional branch to switch to"),
    json: bool = JSON_OPTION,
):
    """Interactively switch between branches."""
    switch_branch(branch_name, json_output=json)


@app.command(name="co")
def co_command(
    branch_name: str | None = typer.Argument(None, help="Optional branch to switch to"),
    json: bool = JSON_OPTION,
):
    """Alias for 'switch' - Interactively switch between branches."""
    switch_branch(branch_name, json_output=json)


@app.command(name="track")
def track_branch(
    branch_name: str | None = typer.Argument(
        None, help="Optional name of branch to track"
    ),
    json: bool = JSON_OPTION,
):
    """Track an existing Git branch in the panqake stack."""
    track(branch_name, json_output=json)


@app.command(name="untrack")
def untrack_branch(
    branch_name: str | None = typer.Argument(
        None, help="Optional name of branch to untrack"
    ),
    json: bool = JSON_OPTION,
):
    """Remove a branch from the panqake stack (does not delete the git branch)."""
    untrack(branch_name, json_output=json)


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
    json: bool = JSON_OPTION,
):
    """Modify/amend the current commit or create a new one."""
    modify_commit(commit, message, no_amend=not amend, json_output=json)


@app.command(name="submit")
def submit(
    branch_name: str | None = typer.Argument(
        None, help="Optional branch to update PR for"
    ),
    create_pr: bool | None = typer.Option(
        None,
        "--create-pr/--no-create-pr",
        help="Control PR creation when one does not exist",
    ),
    json: bool = JSON_OPTION,
):
    """Update remote branch and PR after changes."""
    update_pull_request(branch_name, create_pr=create_pr, json_output=json)


@app.command()
def merge(
    branch_name: str | None = typer.Argument(None, help="Optional branch to merge"),
    delete_branch: bool = typer.Option(
        True, help="Delete the local branch after merging"
    ),
    update_children: bool = typer.Option(
        True, help="Update child branches after merging"
    ),
    allow_failed_checks: bool = typer.Option(
        False,
        "--allow-failed-checks",
        help="Proceed even when required PR checks have not passed",
    ),
    yes: bool = typer.Option(False, "--yes", "-y", help="Skip confirmation prompts"),
    method: str | None = typer.Option(
        None,
        "--method",
        "-m",
        help="Merge method: squash, rebase, or merge",
    ),
    json: bool = JSON_OPTION,
):
    """Merge a PR and manage the branch stack after merge."""
    merge_branch(
        branch_name,
        delete_branch,
        update_children,
        allow_failed_checks=allow_failed_checks,
        assume_yes=yes,
        method=method,
        json_output=json,
    )


@app.command()
def sync(
    main_branch: str = typer.Argument(
        "main", help="Base branch to sync with (default: main)"
    ),
    push: bool = typer.Option(
        True, help="Push changes to remote after syncing branches"
    ),
    delete_merged: bool | None = typer.Option(
        None,
        "--delete-merged/--keep-merged",
        help="Delete or keep merged branches without prompting",
    ),
    json: bool = JSON_OPTION,
):
    """Sync branches with remote repository changes."""
    sync_with_remote(
        main_branch,
        skip_push=not push,
        delete_merged=delete_merged,
        json_output=json,
    )


@app.command()
def rename(
    old_name: str | None = typer.Argument(
        None,
        help="Current name of the branch to rename (default: current branch)",
    ),
    new_name: str | None = typer.Argument(
        None, help="New name for the branch (if not provided, will prompt)"
    ),
    json: bool = JSON_OPTION,
):
    """Rename a branch while maintaining stack relationships."""
    rename_branch(old_name, new_name, json_output=json)


@app.command()
def up(json: bool = JSON_OPTION):
    """Navigate to the parent branch in the stack.

    Move up from the current branch to its closest ancestor.
    If there is no parent branch, informs the user.
    """
    up_command(json_output=json)


@app.command()
def down(json: bool = JSON_OPTION):
    """Navigate to a child branch in the stack.

    Move down from the current branch to a child branch.
    If there are multiple children, prompts for selection.
    If there are no children, informs the user.
    """
    down_command(json_output=json)


def main():
    """Main entry point for the panqake CLI."""
    argv = sys.argv[1:]
    json_output = _json_requested(argv)

    # Initialize panqake directory and files
    init_panqake()

    # Check if we're in a git repository
    in_git_repo = (
        run_git_command(["rev-parse", "--is-inside-work-tree"], silent_fail=True)
        is not None
        if json_output
        else is_git_repo()
    )
    if not in_git_repo:
        if json_output:
            _emit_json_error(
                _requested_command(argv),
                GitOperationError("Not in a git repository", exit_code=1),
            )
        else:
            console.print("Error: Not in a git repository", style="bold red")
        sys.exit(1)

    # Check if any arguments were provided
    if not argv:
        # No arguments, show help
        app(["-h"])
        return

    normalized_app_argv = _normalized_app_argv(argv)

    # If this is a panqake command invocation, dispatch to Typer.
    if normalized_app_argv is not None:
        app(normalized_app_argv)
    # Otherwise, pass all arguments to git.
    else:
        print_formatted_text("[info]Passing command to git...[/info]")
        result = run_git_command(argv)
        if result is not None:
            console.print(result)


if __name__ == "__main__":
    main()
