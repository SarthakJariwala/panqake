"""Git operations for panqake git-stacking utility."""

import os
import subprocess
import sys
from typing import List, Optional

from panqake.utils.prompt import format_branch, print_formatted_text


def is_git_repo() -> bool:
    """Check if current directory is in a git repository."""
    try:
        subprocess.run(
            ["git", "rev-parse", "--is-inside-work-tree"],
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        return True
    except subprocess.CalledProcessError:
        return False


def run_git_command(command: List[str]) -> Optional[str]:
    """Run a git command and return its output."""
    try:
        result = subprocess.run(
            ["git"] + command,
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        return result.stdout.strip()
    except subprocess.CalledProcessError as e:
        print(f"Error running git command: {e}")
        print(f"stderr: {e.stderr}")
        return None


def get_repo_id() -> Optional[str]:
    """Get the current repository identifier."""
    repo_path = run_git_command(["rev-parse", "--show-toplevel"])
    if repo_path:
        return os.path.basename(repo_path)
    return None


def get_current_branch() -> Optional[str]:
    """Get the current branch name."""
    return run_git_command(["symbolic-ref", "--short", "HEAD"])


def list_all_branches() -> List[str]:
    """Get a list of all branches."""
    result = run_git_command(["branch", "--format=%(refname:short)"])
    if result:
        return result.splitlines()
    return []


def branch_exists(branch: str) -> bool:
    """Check if a branch exists."""
    try:
        subprocess.run(
            ["git", "show-ref", "--verify", f"refs/heads/{branch}"],
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        return True
    except subprocess.CalledProcessError:
        return False


def validate_branch(branch_name: Optional[str] = None) -> str:
    """Validate branch exists and get current branch if none specified.

    Args:
        branch_name: The branch name to validate, or None to use current branch

    Returns:
        The validated branch name

    Raises:
        SystemExit: If the branch does not exist
    """
    # If no branch specified, use current branch
    if not branch_name:
        branch_name = get_current_branch()

    # Check if target branch exists
    if not branch_exists(branch_name):
        print_formatted_text(
            f"<warning>Error: Branch '{branch_name}' does not exist</warning>"
        )
        sys.exit(1)

    return branch_name


def push_branch_to_remote(branch: str, force: bool = False) -> bool:
    """Push a branch to the remote.

    Args:
        branch: The branch name to push
        force: Whether to use force-with-lease for the push

    Returns:
        True if the push was successful, False otherwise
    """
    try:
        print_formatted_text("<info>Pushing branch to origin...</info>")
        print_formatted_text(f"<branch>{branch}</branch>")
        print("")

        push_cmd = ["push", "-u", "origin", branch]
        if force:
            push_cmd.insert(1, "--force-with-lease")
            print_formatted_text(
                "<info>Using force-with-lease for safer force push</info>"
            )

        subprocess.run(
            ["git"] + push_cmd,
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )

        print_formatted_text("<success>Successfully pushed to origin</success>")
        print_formatted_text(f"<branch>{branch}</branch>")
        print("")
        return True
    except subprocess.CalledProcessError as e:
        error_message = e.stderr.decode("utf-8") if e.stderr else "Unknown error"
        print_formatted_text(
            f"<warning>Failed to push branch to origin: {error_message}</warning>"
        )
        return False


def is_branch_pushed_to_remote(branch: str) -> bool:
    """Check if a branch exists on the remote."""
    result = subprocess.run(
        ["git", "ls-remote", "--heads", "origin", branch],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    return bool(result.stdout.strip())


def delete_remote_branch(branch: str) -> bool:
    """Delete a branch on the remote repository."""
    try:
        print_formatted_text(
            f"<info>Deleting remote branch {format_branch(branch)}...</info>"
        )
        subprocess.run(
            ["git", "push", "origin", "--delete", branch],
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        print_formatted_text("<success>Remote branch deleted successfully</success>")
        return True
    except subprocess.CalledProcessError as e:
        error_message = e.stderr.decode("utf-8") if e.stderr else "Unknown error"
        print_formatted_text(
            f"<warning>Warning: Failed to delete remote branch '{branch}'</warning>"
        )
        print_formatted_text(f"<warning>Details: {error_message}</warning>")
        return False
