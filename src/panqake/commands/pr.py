"""Command for creating pull requests for branches in the stack."""

import shutil
import subprocess
import sys

from panqake.utils.git import get_current_branch, branch_exists
from panqake.utils.config import get_parent_branch, get_child_branches


def create_pull_requests(branch_name=None):
    """Create pull requests for branches in the stack."""
    # Check for GitHub CLI
    if not shutil.which("gh"):
        print("Error: GitHub CLI (gh) is required but not installed.")
        print("Please install GitHub CLI: https://cli.github.com/manual/installation")
        sys.exit(1)

    # If no branch specified, use current branch
    if not branch_name:
        branch_name = get_current_branch()

    # Check if target branch exists
    if not branch_exists(branch_name):
        print(f"Error: Branch '{branch_name}' does not exist")
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
            print(f"Branch '{branch}' already has an open PR")
        except subprocess.CalledProcessError:
            print(f"Creating PR for branch '{branch}'...")

            # Get parent branch for PR target
            parent = get_parent_branch(branch)
            if not parent:
                parent = "main"  # Default to main if no parent

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
                        f"[{branch}] Stacked PR",
                        "--body",
                        "This is part of a stacked PR series.",
                    ],
                    check=True,
                )
            except subprocess.CalledProcessError:
                print(f"Error: Failed to create PR for branch '{branch}'")
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

    print(f"Creating PRs from the bottom of the stack up to '{branch_name}'...")
    create_prs_bottom_up(oldest_branch)

    print("Pull request creation complete")
