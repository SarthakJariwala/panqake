"""GitHub CLI operations for panqake git-stacking utility."""

import shutil
import subprocess


def branch_has_pr(branch: str) -> bool:
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


def check_github_cli_installed() -> bool:
    """Check if GitHub CLI is installed."""
    return bool(shutil.which("gh"))


def create_pr(base: str, head: str, title: str, body: str = "") -> bool:
    """Create a pull request using GitHub CLI."""
    try:
        subprocess.run(
            [
                "gh",
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
            ],
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        return True
    except subprocess.CalledProcessError:
        return False


def update_pr_base(branch: str, new_base: str) -> bool:
    """Update the base branch of a PR."""
    try:
        subprocess.run(
            ["gh", "pr", "edit", branch, "--base", new_base],
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        return True
    except subprocess.CalledProcessError:
        return False


def merge_pr(branch: str, merge_method: str = "squash") -> bool:
    """Merge a PR using GitHub CLI."""
    try:
        subprocess.run(
            ["gh", "pr", "merge", branch, f"--{merge_method}"],
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        return True
    except subprocess.CalledProcessError:
        return False
