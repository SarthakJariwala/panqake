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
    get_potential_reviewers,
)
from panqake.utils.questionary_prompt import (
    PRTitleValidator,
    console,
    format_branch,
    print_formatted_text,
    prompt_confirm,
    prompt_input,
)
from panqake.utils.selection import select_reviewers
from panqake.utils.status import status
from panqake.utils.types import BranchName


def prompt_for_reviewers(potential_reviewers: list[str]) -> list[str]:
    """Prompt the user to select reviewers from a list of potential reviewers.

    Args:
        potential_reviewers: List of potential reviewer usernames

    Returns:
        List of selected reviewer usernames
    """
    return select_reviewers(potential_reviewers, include_skip_option=True)


def find_oldest_branch_without_pr(branch: BranchName) -> BranchName | None:
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


def is_branch_in_path_to_target(
    child: BranchName, branch_name: BranchName, parent_branch: BranchName | None
) -> bool:
    """Check if a child branch is in the path to the target branch."""
    current = branch_name
    while current and current != parent_branch:
        if current == child:
            return True
        current = get_parent_branch(current)

    return False


def process_branch_for_pr(
    branch: BranchName, target_branch: BranchName, draft: bool = False
) -> bool:
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

        pr_created = create_pr_for_branch(branch, parent, draft)

    # Only process children if PR was created successfully or already existed
    if pr_created:
        # Process any children of this branch that lead to the target
        for child in get_child_branches(branch):
            if (
                is_branch_in_path_to_target(child, target_branch, branch)
                or child == target_branch
            ):
                process_branch_for_pr(child, target_branch, draft)
    else:
        print_formatted_text(
            f"[warning]Skipping child branches of {format_branch(branch)} due to PR creation failure[/warning]"
        )

    return pr_created


def create_pull_requests(
    branch_name: BranchName | None = None, draft: bool = False
) -> None:
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
        if not branch_name:
            print_formatted_text(
                "[danger]Error: Could not determine current branch[/danger]"
            )
            sys.exit(1)

    with status("Analyzing branch stack for PR creation...") as s:
        # Check if target branch exists
        s.update("Validating target branch...")
        if not branch_exists(branch_name):
            s.pause_and_print(
                f"[warning]Error: Branch '{branch_name}' does not exist[/warning]"
            )
            sys.exit(1)

        # Find the oldest branch in the stack that needs a PR
        s.update("Finding branches that need PRs...")
        oldest_branch = find_oldest_branch_without_pr(branch_name)
        if not oldest_branch:
            print_formatted_text("[info]No branches found that need PRs[/info]")
            return

        s.pause_and_print(
            f"[info]Creating PRs from the bottom of the stack up to: {format_branch(branch_name)}[/info]"
        )

    process_branch_for_pr(oldest_branch, branch_name, draft)

    print_formatted_text("[success]Pull request creation complete[/success]")


def ensure_branch_pushed(branch: BranchName) -> bool:
    """Ensure a branch is pushed to remote."""
    if not is_branch_pushed_to_remote(branch):
        print_formatted_text(
            f"[warning]Branch {format_branch(branch)} has not been pushed to remote yet[/warning]"
        )
        if prompt_confirm("Would you like to push it now?"):
            with status(f"Pushing {branch} to remote..."):
                return push_branch_to_remote(branch)
        else:
            print_formatted_text("[info]PR creation skipped[/info]")
            return False
    return True


def create_pr_for_branch(
    branch: BranchName, parent: BranchName, draft: bool = False
) -> bool:
    """Create a PR for a specific branch."""
    # Check if both branches are pushed to remote
    if not ensure_branch_pushed(branch) or not ensure_branch_pushed(parent):
        return False

    with status("Validating PR requirements...") as s:
        # Check if there are commits between branches
        s.update("Checking for commits between branches...")
        diff_command = ["log", f"{parent}..{branch}", "--oneline"]
        diff_output = run_git_command(diff_command)

        if not diff_output or not diff_output.strip():
            s.pause_and_print(
                f"[warning]Error: No commits found between {format_branch(parent)} and {format_branch(branch)}[/warning]"
            )
            return False

        # Get commit message for default PR title
        s.update("Generating default PR title...")
        commit_message = run_git_command(["log", "-1", "--pretty=%s", branch])
        default_title = (
            f"[{branch}] {commit_message}"
            if commit_message
            else f"[{branch}] Stacked PR"
        )

    # Prompt for PR details
    title = prompt_input(
        "Enter PR title: ", validator=PRTitleValidator(), default=default_title
    )

    description = prompt_input(
        "Enter PR description (optional): ", default="", multiline=True
    )

    # Prompt for draft status if not already specified
    if not draft:
        draft = prompt_confirm("Is this a draft PR?")

    # Get potential reviewers and prompt for selection
    with status("Fetching potential reviewers..."):
        potential_reviewers = get_potential_reviewers()
    selected_reviewers = prompt_for_reviewers(potential_reviewers)

    # Show summary and confirm
    # Create formatted content for the panel
    arrow = Text(" ← ", style="muted")
    title_info = Text(f"Title: {title}", style="info")
    reviewers_info = Text(
        f"Reviewers: {', '.join(selected_reviewers) if selected_reviewers else 'None'}",
        style="muted",
    )

    # Create branch relationship line
    relationship = Group(
        Text(""),  # Empty line for spacing
        Text.assemble(title_info),
        Text(""),
        Text.assemble(description),
        Text(""),
        Text.assemble(reviewers_info),
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
    with status(f"Creating pull request for {branch}..."):
        success, pr_url = create_pr(
            parent, branch, title, description, selected_reviewers, draft
        )

    if success:
        print_formatted_text(
            f"[success]PR created successfully for {format_branch(branch)}[/success]"
        )
        if pr_url:
            print_formatted_text(f"[info]Pull request URL: {pr_url}[/info]")
        return True
    else:
        print_formatted_text(
            f"[warning]Error: Failed to create PR for branch '{branch}'[/warning]"
        )
        return False
