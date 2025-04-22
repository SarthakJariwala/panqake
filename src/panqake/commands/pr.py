"""Command for creating pull requests for branches in the stack."""

import shutil
import subprocess
import sys

from panqake.utils.config import get_child_branches, get_parent_branch
from panqake.utils.git import branch_exists, get_current_branch, run_git_command
from panqake.utils.questionary_prompt import (
    PRTitleValidator,
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


def is_branch_pushed_to_remote(branch):
    """Check if a branch exists on the remote."""
    result = subprocess.run(
        ["git", "ls-remote", "--heads", "origin", branch],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    return bool(result.stdout.strip())


def push_branch_to_remote(branch):
    """Push a branch to the remote."""
    try:
        print_formatted_text(
            f"<info>Pushing branch {format_branch(branch)} to origin...</info>"
        )
        subprocess.run(
            ["git", "push", "-u", "origin", branch],
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        print_formatted_text(
            f"<success>Successfully pushed {format_branch(branch)} to origin</success>"
        )
        return True
    except subprocess.CalledProcessError as e:
        error_message = e.stderr.decode("utf-8") if e.stderr else "Unknown error"
        print_formatted_text(
            f"<warning>Failed to push branch to origin: {error_message}</warning>"
        )
        return False


def ensure_branch_pushed(branch):
    """Ensure a branch is pushed to remote."""
    if not is_branch_pushed_to_remote(branch):
        print_formatted_text(
            f"<warning>Branch {format_branch(branch)} has not been pushed to remote yet</warning>"
        )
        if prompt_confirm("Would you like to push it now?"):
            return push_branch_to_remote(branch)
        else:
            print_formatted_text("<info>PR creation skipped.</info>")
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
            f"<warning>Error: No commits found between {format_branch(parent)} and {format_branch(branch)}</warning>"
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
    print_formatted_text("<info>PR for branch:</info>")
    print_formatted_text(f"<branch>{branch}</branch>")
    print("")

    print_formatted_text("<info>Target branch:</info>")
    print_formatted_text(f"<branch>{parent}</branch>")
    print("")

    print_formatted_text("<info>Title:</info>")
    print_formatted_text(f"{title}")
    print("")

    if not prompt_confirm("Create this pull request?"):
        print_formatted_text("<info>PR creation skipped.</info>")
        return False

    # Create the PR
    try:
        subprocess.run(
            [
                "gh",
                "pr",
                "create",
                "--base",
                parent,
                "--head",
                branch,
                "--title",
                title,
                "--body",
                description,
            ],
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        print_formatted_text(
            f"<success>PR created successfully for {format_branch(branch)}</success>"
        )
        return True
    except subprocess.CalledProcessError as e:
        error_message = e.stderr.decode("utf-8") if e.stderr else "Unknown error"
        print_formatted_text(
            f"<warning>Error: Failed to create PR for branch '{branch}'</warning>"
        )
        print_formatted_text(f"<warning>Details: {error_message}</warning>")
        return False


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
        print_formatted_text(f"<info>Branch {branch} already has an open PR</info>")
        pr_created = True
    else:
        print_formatted_text("<info>Creating PR for branch:</info> ")
        print_formatted_text(f"<branch>{branch}</branch>")
        print("")
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
            f"<warning>Skipping child branches of {format_branch(branch)} due to PR creation failure</warning>"
        )


def create_pull_requests(branch_name=None):
    """Create pull requests for branches in the stack."""
    # Check for GitHub CLI
    if not shutil.which("gh"):
        print_formatted_text(
            "<warning>Error: GitHub CLI (gh) is required but not installed.</warning>"
        )
        print_formatted_text(
            "<info>Please install GitHub CLI: https://cli.github.com/manual/installation</info>"
        )
        sys.exit(1)

    # If no branch specified, use current branch
    if not branch_name:
        branch_name = get_current_branch()

    # Check if target branch exists
    if not branch_exists(branch_name):
        print_formatted_text(
            f"<warning>Error: Branch '{branch_name}' does not exist</warning>"
        )
        sys.exit(1)

    # Find the oldest branch in the stack that needs a PR
    oldest_branch = find_oldest_branch_without_pr(branch_name)

    print_formatted_text(
        "<info>Creating PRs from the bottom of the stack up to:</info> "
    )
    print_formatted_text(f"<branch>{branch_name}</branch>")
    print("")

    process_branch_for_pr(oldest_branch, branch_name)

    print_formatted_text("<success>Pull request creation complete</success>")
