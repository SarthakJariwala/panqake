"""GitHub CLI operations for panqake git-stacking utility."""

import shutil
import subprocess
from typing import List, Optional


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


def check_github_cli_installed() -> bool:
    """Check if GitHub CLI is installed."""
    return bool(shutil.which("gh"))


def create_pr(base: str, head: str, title: str, body: str = "") -> bool:
    """Create a pull request using GitHub CLI."""
    result = run_gh_command(
        [
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
    )
    return result is not None


def update_pr_base(branch: str, new_base: str) -> bool:
    """Update the base branch of a PR."""
    result = run_gh_command(["pr", "edit", branch, "--base", new_base])
    return result is not None


def merge_pr(branch: str, merge_method: str = "squash") -> bool:
    """Merge a PR using GitHub CLI."""
    result = run_gh_command(["pr", "merge", branch, f"--{merge_method}"])
    return result is not None
