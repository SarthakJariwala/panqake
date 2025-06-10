"""GitHub CLI operations for panqake git-stacking utility."""

import json
import shutil
import subprocess
from typing import List, Optional, Tuple

from panqake.utils.status import status


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
    with status("Fetching potential reviewers..."):
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
    draft: bool = False,
) -> Tuple[bool, Optional[str]]:
    """Create a pull request using GitHub CLI.

    Args:
        base: Base branch for the PR
        head: Head branch for the PR
        title: PR title
        body: PR description
        reviewers: Optional list of reviewer usernames
        draft: Whether to create as a draft PR

    Returns:
        Tuple[bool, Optional[str]]: (success, url) where success indicates if
        PR creation was successful and url is the PR URL if available
    """
    with status("Creating pull request..."):
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

        # Add draft flag if requested
        if draft:
            cmd.append("--draft")

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
    with status(f"Updating PR base to {new_base}..."):
        result = run_gh_command(["pr", "edit", branch, "--base", new_base])
        return result is not None


def get_pr_checks_status(branch: str) -> Tuple[bool, List[str]]:
    """Check if all required status checks have passed for a PR.

    Returns:
        Tuple[bool, List[str]]: (all_passed, failed_checks) where all_passed indicates
        if all checks passed and failed_checks is a list of failed check names
    """
    with status("Checking PR status..."):
        result = run_gh_command(["pr", "view", branch, "--json", "statusCheckRollup"])
        if not result:
            return False, ["Failed to retrieve check status"]

        try:
            data = json.loads(result)
            checks = data.get("statusCheckRollup", [])

            # If there are no checks, consider it passed
            if not checks:
                return True, []

            failed_checks = []
            # Check for failed or incomplete checks
            for check in checks:
                conclusion = check.get("conclusion")
                name = check.get("name", "Unknown check")

                if conclusion != "SUCCESS":
                    check_status = conclusion or "PENDING"
                    failed_checks.append(f"{name} ({check_status})")

            return len(failed_checks) == 0, failed_checks
        except json.JSONDecodeError:
            return False, ["Failed to parse check status"]


def merge_pr(branch: str, merge_method: str = "squash") -> bool:
    """Merge a PR using GitHub CLI."""
    with status(f"Merging pull request ({merge_method})..."):
        result = run_gh_command(["pr", "merge", branch, f"--{merge_method}"])
        return result is not None
