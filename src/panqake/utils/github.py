"""GitHub CLI operations for panqake git-stacking utility."""

import json
import shutil
import subprocess
from typing import List, Optional, Tuple


def run_gh_command(command: List[str]) -> Optional[str]:
    """Run a GitHub CLI command and return its output."""
    try:
        result = subprocess.run(
            ["gh"] + command,
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        return result.stdout.strip()
    except subprocess.CalledProcessError:
        return None


def branch_has_pr(branch: str) -> bool:
    """Check if a branch already has a PR."""
    result = run_gh_command(["pr", "view", branch])
    return result is not None


def get_pr_url(branch: str) -> Optional[str]:
    """Get the URL of a pull request for a branch."""
    result = run_gh_command(["pr", "view", branch, "--json", "url"])
    if result:
        try:
            data = json.loads(result)
            return data.get("url")
        except json.JSONDecodeError:
            pass
    return None


def check_github_cli_installed() -> bool:
    """Check if GitHub CLI is installed."""
    return bool(shutil.which("gh"))


def get_potential_reviewers() -> List[str]:
    """Get list of potential reviewers from the repository.

    Returns:
        List[str]: List of usernames that can be added as reviewers
    """
    # Get repository assignable users (users who can be assigned as reviewers)
    result = run_gh_command(["repo", "view", "--json", "owner,assignableUsers"])
    if not result:
        return []

    try:
        data = json.loads(result)
        reviewers = []

        # Add repository owner
        owner = data.get("owner", {}).get("login")
        if owner:
            reviewers.append(owner)

        # Add assignable users
        assignable_users = data.get("assignableUsers", [])
        for user in assignable_users:
            login = user.get("login")
            if login and login not in reviewers:
                reviewers.append(login)

        return sorted(reviewers)
    except json.JSONDecodeError:
        return []


def create_pr(
    base: str,
    head: str,
    title: str,
    body: str = "",
    reviewers: Optional[List[str]] = None,
) -> Tuple[bool, Optional[str]]:
    """Create a pull request using GitHub CLI.

    Args:
        base: Base branch for the PR
        head: Head branch for the PR
        title: PR title
        body: PR description
        reviewers: Optional list of reviewer usernames

    Returns:
        Tuple[bool, Optional[str]]: (success, url) where success indicates if
        PR creation was successful and url is the PR URL if available
    """
    cmd = [
        "pr",
        "create",
        "--base",
        base,
        "--head",
        head,
        "--title",
        title,
        "--body",
        body,
    ]

    # Add reviewers if provided
    if reviewers:
        for reviewer in reviewers:
            cmd.extend(["--reviewer", reviewer])

    result = run_gh_command(cmd)

    if result is None:
        return False, None

    # Extract URL from the output - gh CLI typically outputs the URL in the last line
    # Example output: "https://github.com/user/repo/pull/123"
    lines = result.split("\n")
    for line in reversed(lines):
        if line.startswith("https://") and "/pull/" in line:
            return True, line.strip()

    # If we couldn't parse the URL from output, try to get it directly
    url = get_pr_url(head)
    return True, url


def update_pr_base(branch: str, new_base: str) -> bool:
    """Update the base branch of a PR."""
    result = run_gh_command(["pr", "edit", branch, "--base", new_base])
    return result is not None


def get_pr_checks_status(branch: str) -> bool:
    """Check if all required status checks have passed for a PR.

    Returns:
        bool: True if all required checks passed or if there are no checks, False otherwise
    """
    result = run_gh_command(["pr", "view", branch, "--json", "statusCheckRollup"])
    if not result:
        return False

    try:
        data = json.loads(result)
        checks = data.get("statusCheckRollup", [])

        # If there are no checks, consider it passed
        if not checks:
            return True

        # Check if any required checks have failed
        for check in checks:
            if check.get("conclusion") != "SUCCESS":
                return False

        return True
    except json.JSONDecodeError:
        return False


def merge_pr(branch: str, merge_method: str = "squash") -> bool:
    """Merge a PR using GitHub CLI."""
    result = run_gh_command(["pr", "merge", branch, f"--{merge_method}"])
    return result is not None
