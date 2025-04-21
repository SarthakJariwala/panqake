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

    def find_oldest_branch_without_pr(branch):
        """Find the bottom-most branch without a PR."""
        parent = get_parent_branch(branch)

        # If no parent or parent is main/master, we've reached the bottom
        if not parent or parent in ["main", "master"]:
            return branch

        # Check if parent branch already has a PR
        try:
            subprocess.run(
                ["gh", "pr", "view", parent],
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
            # Parent already has a PR, so this is the bottom-most branch without one
            return branch
        except subprocess.CalledProcessError:
            # Parent doesn't have a PR, check further down the stack
            return find_oldest_branch_without_pr(parent)

    # Find the oldest branch in the stack that needs a PR
    oldest_branch = find_oldest_branch_without_pr(branch_name)

    def create_prs_bottom_up(branch):
        """Create PRs from bottom up."""
        # Check if this branch already has a PR
        try:
            subprocess.run(
                ["gh", "pr", "view", branch],
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
            print_formatted_text(
                f"Branch {format_branch(branch)} already has an open PR"
            )
        except subprocess.CalledProcessError:
            print_formatted_text(
                f"<info>Creating PR for branch:</info> {format_branch(branch)}"
            )

            # Get parent branch for PR target
            parent = get_parent_branch(branch)
            if not parent:
                parent = "main"  # Default to main if no parent

            # Get commit message for default PR title
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
                "Enter PR description (optional): ",
                default="This is part of a stacked PR series.",
            )

            # Show summary and confirm
            print_formatted_text(f"<info>PR for branch:</info> {format_branch(branch)}")
            print_formatted_text(f"<info>Target branch:</info> {format_branch(parent)}")
            print_formatted_text(f"<info>Title:</info> {title}")

            if not prompt_confirm("Create this pull request?"):
                print_formatted_text("<info>PR creation skipped.</info>")
                return

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
                )
                print_formatted_text(
                    f"<success>PR created successfully for {format_branch(branch)}</success>"
                )
            except subprocess.CalledProcessError:
                print_formatted_text(
                    f"<warning>Error: Failed to create PR for branch '{branch}'</warning>"
                )
                sys.exit(1)

        # Process any children of this branch that lead to the target
        is_in_path_to_target = False

        for child in get_child_branches(branch):
            # Check if this child is in the path to the target
            current = branch_name
            while current and current != branch:
                if current == child:
                    is_in_path_to_target = True
                    break
                current = get_parent_branch(current)

            if is_in_path_to_target or child == branch_name:
                create_prs_bottom_up(child)

    print_formatted_text(
        f"<info>Creating PRs from the bottom of the stack up to:</info> {format_branch(branch_name)}"
    )
    create_prs_bottom_up(oldest_branch)

    print_formatted_text("<success>Pull request creation complete</success>")
