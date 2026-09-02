"""GitHub CLI operations for panqake git-stacking utility."""

import json
import shutil
import subprocess
from collections.abc import Sequence

from panqake.ports.results import PRAttachment
from panqake.utils.status import status


def run_gh_command(command: list[str]) -> str | None:
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


def get_open_pr_info(branch: str) -> dict | None:
    """Get PR info for a branch, only if the PR is open.

    Returns:
        Optional[dict]: PR info dict with 'state' and 'url' keys if an open PR exists,
        None otherwise. This prevents linking to old merged/closed PRs when a branch
        name is reused.
    """
    result = run_gh_command(["pr", "view", branch, "--json", "state,url"])
    if not result:
        return None
    try:
        data = json.loads(result)
        if data.get("state") == "OPEN":
            return data
    except json.JSONDecodeError:
        pass
    return None


def branch_has_pr(branch: str) -> bool:
    """Check if a branch already has an open PR."""
    return get_open_pr_info(branch) is not None


def get_pr_url(branch: str) -> str | None:
    """Get the URL of an open pull request for a branch."""
    info = get_open_pr_info(branch)
    return info.get("url") if info else None


def check_github_cli_installed() -> bool:
    """Check if GitHub CLI is installed."""
    return bool(shutil.which("gh"))


def get_potential_reviewers() -> list[str]:
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


def _pull_request_url(output: str) -> str | None:
    for line in reversed(output.splitlines()):
        stripped = line.strip()
        if stripped.startswith("https://") and "/pull/" in stripped:
            return stripped
    return None


def create_pr(
    base: str,
    head: str,
    title: str,
    body: str = "",
    reviewers: list[str] | None = None,
    draft: bool = False,
    attachments: Sequence[PRAttachment] | None = None,
) -> tuple[bool, str | None]:
    """Create a pull request using GitHub CLI.

    Args:
        base: Base branch for the PR
        head: Head branch for the PR
        title: PR title
        body: PR description
        reviewers: Optional list of reviewer usernames
        draft: Whether to create as a draft PR
        attachments: Optional local files forwarded as `gh pr create --attach`

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

        if draft:
            cmd.append("--draft")

        if reviewers:
            for reviewer in reviewers:
                cmd.extend(["--reviewer", reviewer])

        if attachments:
            for attachment in attachments:
                cmd.extend(["--attach", attachment.to_gh_value()])

        completed = subprocess.run(
            ["gh", *cmd],
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        output = (completed.stdout or "").strip()
        url = _pull_request_url(output)
        if completed.returncode == 0:
            return True, url or get_pr_url(head)
        if url:
            return True, url
        fallback = get_pr_url(head)
        if fallback:
            return True, fallback
        return False, None


def update_pr_base(branch: str, new_base: str) -> bool:
    """Update the base branch of a PR."""
    result = run_gh_command(["pr", "edit", branch, "--base", new_base])
    return result is not None


def get_pr_checks_status(branch: str) -> tuple[bool, list[str]]:
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
