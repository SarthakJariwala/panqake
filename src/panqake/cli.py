"""
Panqake - CLI for Git stacking
A Python implementation of git-stacking workflow management
"""

import sys
from pathlib import Path

import typer
from rich.console import Console
from typer.core import TyperGroup

from panqake.commands.delete import delete_branch
from panqake.commands.down import down as down_command
from panqake.commands.list import list_branches
from panqake.commands.merge import merge_branch
from panqake.commands.modify import modify_commit
from panqake.commands.move import move_branch, move_continue
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
from panqake.ports.results import MAX_PR_ATTACHMENTS, PRAttachment
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
    "move",
    "reparent",  # Alias for move
    "sync",
    "up",
    "down",
    "--help",
    "-h",
    "--install-completion",
    "--show-completion",
]

INFORMATIONAL_OPTIONS = {
    "--help",
    "-h",
    "--install-completion",
    "--show-completion",
}

COMMAND_ALIASES = {
    "ls": "list",
    "co": "switch",
    "reparent": "move",
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
JSON_OPTION = typer.Option(
    False,
    "--json",
    help="Output machine-readable JSON and disable interactive prompts",
)


def _examples(*commands: str) -> str:
    """Format copy-pasteable command examples for Typer help."""
    return "Examples:\n\n" + "\n\n".join(f"  {command}" for command in commands)


def _resolve_pr_body(body: str | None, body_file: str | None) -> str | None:
    """Resolve inline, file, or stdin PR body input."""
    if body is not None and body_file is not None:
        raise typer.BadParameter("--body and --body-file cannot be combined")
    if body_file is None:
        return body
    if body_file == "-":
        return sys.stdin.read()
    try:
        return Path(body_file).read_text(encoding="utf-8")
    except OSError as error:
        raise typer.BadParameter(
            f"Could not read --body-file '{body_file}': {error}"
        ) from error


def _resolve_reviewers(
    reviewers: list[str] | None,
    no_reviewers: bool,
) -> list[str] | None:
    """Resolve repeated reviewer options and an explicit empty selection."""
    if reviewers is not None and no_reviewers:
        raise typer.BadParameter("--reviewer and --no-reviewers cannot be combined")
    return [] if no_reviewers else reviewers


def _resolve_pr_attachments(raw: list[str] | None) -> list[PRAttachment] | None:
    """Parse and validate repeatable `--attach path[#alt]` values."""
    if raw is None:
        return None
    if len(raw) > MAX_PR_ATTACHMENTS:
        raise typer.BadParameter(f"cannot attach more than {MAX_PR_ATTACHMENTS} files")
    attachments: list[PRAttachment] = []
    seen: set[Path] = set()
    for item in raw:
        try:
            attachment = PRAttachment.parse(item)
        except ValueError as error:
            raise typer.BadParameter(str(error)) from error
        path = Path(attachment.path).expanduser()
        if not path.is_file():
            raise typer.BadParameter(f"attachment '{attachment.path}' is not a file")
        resolved = path.resolve()
        if resolved in seen:
            raise typer.BadParameter(
                f"cannot attach the same file twice: '{attachment.path}'"
            )
        seen.add(resolved)
        attachments.append(PRAttachment(path=str(path), alt_text=attachment.alt_text))
    return attachments


def _resolve_modify_files(
    files: list[str] | None,
    stage_all: bool,
    staged_only: bool,
) -> list[str] | None:
    """Resolve mutually exclusive non-interactive staging choices."""
    selected_modes = sum((files is not None, stage_all, staged_only))
    if selected_modes > 1:
        raise typer.BadParameter("--file, --all, and --staged-only cannot be combined")
    return [] if staged_only else files


# Create a custom TyperGroup to handle unknown commands
class PanqakeGroup(TyperGroup):
    def get_command(self, ctx, cmd_name):
        return super().get_command(ctx, cmd_name)


# Initialize the Typer app
app = typer.Typer(
    name="panqake",
    help="Panqake - CLI for Git stacking",
    epilog=_examples(
        "pq <command> --help",
        "pq list --json",
        "pq new feature-auth main",
    ),
    cls=PanqakeGroup,
    rich_markup_mode="rich",
    context_settings={"help_option_names": ["-h", "--help"]},
    add_completion=True,
)


@app.command(
    epilog=_examples(
        "pq new feature-auth main",
        "pq new feature-auth main --json",
        "pq new feature-auth main --tree --path ../feature-auth",
    )
)
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


@app.command(
    name="list",
    epilog=_examples("pq list", "pq list feature-auth --files --json"),
)
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


@app.command(
    name="ls",
    epilog=_examples("pq ls", "pq ls feature-auth --files --json"),
)
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


@app.command(
    epilog=_examples(
        "pq update feature-auth",
        "pq update feature-auth --no-push --yes --json",
    )
)
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


@app.command(
    epilog=_examples(
        "pq delete feature-auth",
        "pq delete feature-auth --yes --json",
    )
)
def delete(
    branch_name: str = typer.Argument(..., help="Name of the branch to delete"),
    yes: bool = typer.Option(False, "--yes", "-y", help="Skip confirmation prompts"),
    json: bool = JSON_OPTION,
):
    """Delete a branch and relink the stack."""
    delete_branch(branch_name, assume_yes=yes, json_output=json)


@app.command(
    epilog=_examples(
        "pq pr feature-auth",
        "pq pr feature-auth --push --no-draft --defaults --yes --json",
        'pq pr feature-auth --title "Add authentication" --body-file - --yes',
        "pq pr feature-auth --attach ./login.png --yes --defaults",
    )
)
def pr(
    branch_name: str | None = typer.Argument(
        None, help="Optional branch to start from"
    ),
    draft: bool | None = typer.Option(
        None,
        "--draft/--no-draft",
        help="Create PRs as drafts or ready for review without prompting",
    ),
    push: bool | None = typer.Option(
        None,
        "--push/--no-push",
        help="Push or skip unpushed branches without prompting",
    ),
    title: str | None = typer.Option(
        None,
        "--title",
        help="Title for the target branch's PR",
    ),
    body: str | None = typer.Option(
        None,
        "--body",
        help="Body for the target branch's PR",
    ),
    body_file: str | None = typer.Option(
        None,
        "--body-file",
        help="Read the target PR body from a file, or - for stdin",
    ),
    reviewer: list[str] | None = typer.Option(
        None,
        "--reviewer",
        help="Reviewer for the target PR; repeat for multiple reviewers",
    ),
    no_reviewers: bool = typer.Option(
        False,
        "--no-reviewers",
        help="Create without reviewers and without prompting",
    ),
    attach: list[str] | None = typer.Option(
        None,
        "--attach",
        help="Image or video for the target PR, as path or path#alt; repeat for more files",
    ),
    defaults: bool = typer.Option(
        False,
        "--defaults",
        help="Use generated titles, empty bodies, and no reviewers without prompting",
    ),
    yes: bool = typer.Option(
        False,
        "--yes",
        "-y",
        help="Create PRs without final confirmation prompts",
    ),
    json: bool = JSON_OPTION,
):
    """Create PRs for the branch stack."""
    create_pull_requests(
        branch_name,
        draft=draft,
        push=push,
        title=title,
        body=_resolve_pr_body(body, body_file),
        reviewers=_resolve_reviewers(reviewer, no_reviewers),
        use_defaults=defaults,
        assume_yes=yes,
        attachments=_resolve_pr_attachments(attach),
        json_output=json,
    )


@app.command(
    epilog=_examples("pq switch feature-auth", "pq switch feature-auth --json")
)
def switch(
    branch_name: str | None = typer.Argument(None, help="Optional branch to switch to"),
    json: bool = JSON_OPTION,
):
    """Interactively switch between branches."""
    switch_branch(branch_name, json_output=json)


@app.command(
    name="co",
    epilog=_examples("pq co feature-auth", "pq co feature-auth --json"),
)
def co_command(
    branch_name: str | None = typer.Argument(None, help="Optional branch to switch to"),
    json: bool = JSON_OPTION,
):
    """Alias for 'switch' - Interactively switch between branches."""
    switch_branch(branch_name, json_output=json)


@app.command(
    name="track",
    epilog=_examples(
        "pq track feature-auth",
        "pq track feature-auth --parent main --json",
    ),
)
def track_branch(
    branch_name: str | None = typer.Argument(
        None, help="Optional name of branch to track"
    ),
    parent: str | None = typer.Option(
        None,
        "--parent",
        help="Parent branch; avoids interactive selection",
    ),
    json: bool = JSON_OPTION,
):
    """Track an existing Git branch in the panqake stack."""
    track(branch_name, parent_branch=parent, json_output=json)


@app.command(
    name="untrack",
    epilog=_examples("pq untrack feature-auth", "pq untrack feature-auth --json"),
)
def untrack_branch(
    branch_name: str | None = typer.Argument(
        None, help="Optional name of branch to untrack"
    ),
    json: bool = JSON_OPTION,
):
    """Remove a branch from the panqake stack (does not delete the git branch)."""
    untrack(branch_name, json_output=json)


@app.command(
    epilog=_examples(
        'pq modify --message "Implement authentication"',
        'pq modify --file src/auth.py --message "Implement authentication"',
        'pq modify --all --message "Implement authentication"',
        'pq modify --staged-only --message "Implement authentication"',
        'pq modify --commit --message "Implement authentication" --json',
    )
)
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
    file: list[str] | None = typer.Option(
        None,
        "--file",
        help="Unstaged path to stage; repeat for multiple paths",
    ),
    all_: bool = typer.Option(
        False,
        "--all",
        help="Stage all unstaged files without prompting",
    ),
    staged_only: bool = typer.Option(
        False,
        "--staged-only",
        help="Commit only already-staged changes without prompting",
    ),
    json: bool = JSON_OPTION,
):
    """Modify/amend the current commit or create a new one."""
    modify_commit(
        commit,
        message,
        no_amend=not amend,
        selected_files=_resolve_modify_files(file, all_, staged_only),
        stage_all=all_,
        json_output=json,
    )


@app.command(
    name="submit",
    epilog=_examples(
        "pq submit feature-auth",
        (
            "pq submit feature-auth --create-pr --push --no-draft "
            "--defaults --yes --json"
        ),
        'pq submit --create-pr --title "Add auth UI" --body-file - --yes',
        "pq submit --create-pr --attach ./login.png --yes --defaults",
    ),
)
def submit(
    branch_name: str | None = typer.Argument(
        None, help="Optional branch to update PR for"
    ),
    create_pr: bool | None = typer.Option(
        None,
        "--create-pr/--no-create-pr",
        help="Control PR creation when one does not exist",
    ),
    draft: bool | None = typer.Option(
        None,
        "--draft/--no-draft",
        help="Create a new PR as draft or ready for review without prompting",
    ),
    push: bool | None = typer.Option(
        None,
        "--push/--no-push",
        help="Push or skip an unpushed PR base branch without prompting",
    ),
    title: str | None = typer.Option(None, "--title", help="Title for a new PR"),
    body: str | None = typer.Option(None, "--body", help="Body for a new PR"),
    body_file: str | None = typer.Option(
        None,
        "--body-file",
        help="Read a new PR body from a file, or - for stdin",
    ),
    reviewer: list[str] | None = typer.Option(
        None,
        "--reviewer",
        help="Reviewer for a new PR; repeat for multiple reviewers",
    ),
    no_reviewers: bool = typer.Option(
        False,
        "--no-reviewers",
        help="Create a new PR without reviewers and without prompting",
    ),
    attach: list[str] | None = typer.Option(
        None,
        "--attach",
        help="Image or video for a new PR, as path or path#alt; repeat for more files",
    ),
    defaults: bool = typer.Option(
        False,
        "--defaults",
        help="Use a generated title, empty body, and no reviewers without prompting",
    ),
    yes: bool = typer.Option(
        False,
        "--yes",
        "-y",
        help="Create a new PR without a final confirmation prompt",
    ),
    json: bool = JSON_OPTION,
):
    """Update remote branch and PR after changes."""
    update_pull_request(
        branch_name,
        create_pr=create_pr,
        draft=draft,
        push=push,
        title=title,
        body=_resolve_pr_body(body, body_file),
        reviewers=_resolve_reviewers(reviewer, no_reviewers),
        use_defaults=defaults,
        assume_yes=yes,
        attachments=_resolve_pr_attachments(attach),
        json_output=json,
    )


@app.command(
    epilog=_examples(
        "pq merge feature-auth",
        "pq merge feature-auth --method squash --yes --json",
    )
)
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


@app.command(
    epilog=_examples(
        "pq sync main",
        "pq sync main --keep-merged --no-push --json",
    )
)
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


@app.command(
    epilog=_examples(
        "pq rename feature-auth auth-service",
        "pq rename feature-auth auth-service --json",
    )
)
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


@app.command(
    epilog=_examples(
        "pq move feature-auth --to main",
        "pq move feature-auth --to main --json",
        "pq move --continue",
    )
)
def move(
    branch_name: str | None = typer.Argument(
        None, help="Branch to move (default: current branch)"
    ),
    to: str | None = typer.Option(
        None, "--to", help="New parent branch (if not provided, will prompt)"
    ),
    continue_: bool = typer.Option(
        False,
        "--continue",
        help=(
            "Resume a previously conflicted move after running `git rebase --continue`."
        ),
    ),
    json: bool = JSON_OPTION,
):
    """Move a branch to a new parent, rebasing its subtree onto it."""
    if continue_:
        if branch_name is not None or to is not None:
            err = GitOperationError(
                "--continue does not take a branch name or --to argument.",
                exit_code=1,
            )
            if json:
                _emit_json_error("move", err)
            else:
                console.print(f"Error: {err.message}", style="bold red")
            raise typer.Exit(code=err.exit_code)
        move_continue(json_output=json)
    else:
        move_branch(branch_name, to, json_output=json)


@app.command(
    name="reparent",
    epilog=_examples(
        "pq reparent feature-auth --to main",
        "pq reparent feature-auth --to main --json",
        "pq reparent --continue",
    ),
)
def reparent_command(
    branch_name: str | None = typer.Argument(
        None, help="Branch to move (default: current branch)"
    ),
    to: str | None = typer.Option(
        None, "--to", help="New parent branch (if not provided, will prompt)"
    ),
    continue_: bool = typer.Option(
        False,
        "--continue",
        help=(
            "Resume a previously conflicted move after running `git rebase --continue`."
        ),
    ),
    json: bool = JSON_OPTION,
):
    """Alias for 'move' - Move a branch to a new parent."""
    if continue_:
        if branch_name is not None or to is not None:
            err = GitOperationError(
                "--continue does not take a branch name or --to argument.",
                exit_code=1,
            )
            if json:
                _emit_json_error("reparent", err)
            else:
                console.print(f"Error: {err.message}", style="bold red")
            raise typer.Exit(code=err.exit_code)
        move_continue(json_output=json)
    else:
        move_branch(branch_name, to, json_output=json)


@app.command(epilog=_examples("pq up", "pq up --json"))
def up(json: bool = JSON_OPTION):
    """Navigate to the parent branch in the stack.

    Move up from the current branch to its closest ancestor.
    If there is no parent branch, informs the user.
    """
    up_command(json_output=json)


@app.command(
    epilog=_examples(
        "pq down",
        "pq down feature-auth --json",
    )
)
def down(
    child: str | None = typer.Argument(
        None,
        help="Child branch to use when the current branch has multiple children",
    ),
    json: bool = JSON_OPTION,
):
    """Navigate to a child branch in the stack.

    Move down from the current branch to a child branch.
    If there are multiple children, prompts for selection.
    If there are no children, informs the user.
    """
    down_command(child, json_output=json)


def main():
    """Main entry point for the panqake CLI."""
    argv = sys.argv[1:]
    json_output = _json_requested(argv)
    normalized_app_argv = _normalized_app_argv(argv)

    # Help and shell-completion discovery should work from any directory and
    # must not initialize repository state as a side effect.
    if not argv:
        app(["-h"])
        return
    if normalized_app_argv is not None and any(
        option in normalized_app_argv for option in INFORMATIONAL_OPTIONS
    ):
        app(normalized_app_argv)
        return

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
