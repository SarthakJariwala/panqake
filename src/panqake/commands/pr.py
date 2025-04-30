"""Command for creating pull requests for branches in the stack."""

import sys

from rich.console import Group
from rich.panel import Panel
from rich.text import Text

from panqake.utils.config import get_child_branches, get_parent_branch
from panqake.utils.git import (
    branch_exists,
    get_current_branch,
    is_branch_pushed_to_remote,
    push_branch_to_remote,
    run_git_command,
)
from panqake.utils.github import (
    branch_has_pr,
    check_github_cli_installed,
    create_pr,
)
from panqake.utils.questionary_prompt import (
    PRTitleValidator,
    console,
    format_branch,
    print_formatted_text,
    prompt_confirm,
    prompt_input,
)


def find_oldest_branch_without_pr(branch):
    """Find the bottom-most branch without a PR."""
    parent = get_parent_branch(branch)

    # If no parent or parent is main/master, we've reached the bottom
    if not parent or parent in ["main", "master"]:
        return branch

    # Check if parent branch already has a PR
    if branch_has_pr(parent):
        # Parent already has a PR, so this is the bottom-most branch without one
        return branch
    else:
        # Parent doesn't have a PR, check further down the stack
        return find_oldest_branch_without_pr(parent)


def is_branch_in_path_to_target(child, branch_name, parent_branch):
    """Check if a child branch is in the path to the target branch."""
    current = branch_name
    while current and current != parent_branch:
        if current == child:
            return True
        current = get_parent_branch(current)

    return False


def process_branch_for_pr(branch, target_branch):
    """Process a branch to create PR and handle its children."""
    if branch_has_pr(branch):
        print_formatted_text(
            f"[info]Branch {format_branch(branch)} already has an open PR[/info]"
        )
        pr_created = True
    else:
        print_formatted_text(
            f"[info]Creating PR for branch: {format_branch(branch)}[/info]"
        )
        # Get parent branch for PR target
        parent = get_parent_branch(branch)
        if not parent:
            parent = "main"  # Default to main if no parent

        pr_created = create_pr_for_branch(branch, parent)

    # Only process children if PR was created successfully or already existed
    if pr_created:
        # Process any children of this branch that lead to the target
        for child in get_child_branches(branch):
            if (
                is_branch_in_path_to_target(child, target_branch, branch)
                or child == target_branch
            ):
                process_branch_for_pr(child, target_branch)
    else:
        print_formatted_text(
            f"[warning]Skipping child branches of {format_branch(branch)} due to PR creation failure[/warning]"
        )


def create_pull_requests(branch_name=None):
    """Create pull requests for branches in the stack."""
    # Check for GitHub CLI
    if not check_github_cli_installed():
        print_formatted_text(
            "[warning]Error: GitHub CLI (gh) is required but not installed.[/warning]"
        )
        print_formatted_text(
            "[info]Please install GitHub CLI: https://cli.github.com/[/info]"
        )
        sys.exit(1)

    # If no branch specified, use current branch
    if not branch_name:
        branch_name = get_current_branch()

    # Check if target branch exists
    if not branch_exists(branch_name):
        print_formatted_text(
            f"[warning]Error: Branch '{branch_name}' does not exist[/warning]"
        )
        sys.exit(1)

    # Find the oldest branch in the stack that needs a PR
    oldest_branch = find_oldest_branch_without_pr(branch_name)

    print_formatted_text(
        f"[info]Creating PRs from the bottom of the stack up to: {format_branch(branch_name)}[/info]"
    )

    process_branch_for_pr(oldest_branch, branch_name)

    print_formatted_text("[success]Pull request creation complete[/success]")


def ensure_branch_pushed(branch):
    """Ensure a branch is pushed to remote."""
    if not is_branch_pushed_to_remote(branch):
        print_formatted_text(
            f"[warning]Branch {format_branch(branch)} has not been pushed to remote yet[/warning]"
        )
        if prompt_confirm("Would you like to push it now?"):
            return push_branch_to_remote(branch)
        else:
            print_formatted_text("[info]PR creation skipped[/info]")
            return False
    return True


def create_pr_for_branch(branch, parent):
    """Create a PR for a specific branch."""
    # Check if both branches are pushed to remote
    if not ensure_branch_pushed(branch) or not ensure_branch_pushed(parent):
        return False

    # Check if there are commits between branches
    diff_command = ["log", f"{parent}..{branch}", "--oneline"]
    diff_output = run_git_command(diff_command)

    if not diff_output.strip():
        print_formatted_text(
            f"[warning]Error: No commits found between {format_branch(parent)} and {format_branch(branch)}[/warning]"
        )
        return False

    # Get commit message for default PR title
    commit_message = run_git_command(["log", "-1", "--pretty=%s", branch])
    default_title = (
        f"[{branch}] {commit_message}" if commit_message else f"[{branch}] Stacked PR"
    )

    # Prompt for PR details
    title = prompt_input(
        "Enter PR title: ", validator=PRTitleValidator(), default=default_title
    )

    description = prompt_input(
        "Enter PR description (optional): ",
        default="",
    )

    # Show summary and confirm
    # Create formatted content for the panel
    arrow = Text(" ← ", style="muted")
    title_info = Text(f"Title: {title}", style="info")

    # Create branch relationship line
    relationship = Group(
        Text(""),  # Empty line for spacing
        Text.assemble(title_info),
        Text(""),
        Text.assemble(description),
    )

    # Create and print panel with all information
    pr_panel = Panel(
        relationship,
        title=Text.assemble(
            parent,
            arrow,
            branch,
        ),
        border_style="cyan",
    )

    console.print(pr_panel)

    if not prompt_confirm("Create this pull request?"):
        print_formatted_text("[info]PR creation skipped.[/info]")
        return False

    # Create the PR
    if create_pr(parent, branch, title, description):
        print_formatted_text(
            f"[success]PR created successfully for {format_branch(branch)}[/success]"
        )
        return True
    else:
        print_formatted_text(
            f"[warning]Error: Failed to create PR for branch '{branch}'[/warning]"
        )
        return False
