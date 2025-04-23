"""Git operations for panqake git-stacking utility."""

import os
import subprocess
import sys
from typing import List, Optional

from panqake.utils.prompt import format_branch
from panqake.utils.questionary_prompt import print_formatted_text


def is_git_repo() -> bool:
    """Check if current directory is in a git repository."""
    result = run_git_command(["rev-parse", "--is-inside-work-tree"])
    return result is not None


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
    result = run_git_command(["show-ref", "--verify", f"refs/heads/{branch}"])
    return result is not None


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
    print_formatted_text("<info>Pushing branch to origin...</info>")
    print_formatted_text(f"<branch>{branch}</branch>")
    print("")

    push_cmd = ["push", "-u", "origin", branch]
    if force:
        push_cmd.insert(1, "--force-with-lease")
        print_formatted_text("<info>Using force-with-lease for safer force push</info>")

    result = run_git_command(push_cmd)

    if result is not None:
        print_formatted_text("<success>Successfully pushed to origin</success>")
        print_formatted_text(f"<branch>{branch}</branch>")
        print("")
        return True
    return False


def is_branch_pushed_to_remote(branch: str) -> bool:
    """Check if a branch exists on the remote."""
    result = run_git_command(["ls-remote", "--heads", "origin", branch])
    return bool(result and result.strip())


def delete_remote_branch(branch: str) -> bool:
    """Delete a branch on the remote repository."""
    print_formatted_text(
        f"<info>Deleting remote branch {format_branch(branch)}...</info>"
    )

    result = run_git_command(["push", "origin", "--delete", branch])

    if result is not None:
        print_formatted_text("<success>Remote branch deleted successfully</success>")
        return True

    print_formatted_text(
        f"<warning>Warning: Failed to delete remote branch '{branch}'</warning>"
    )
    return False


def get_potential_parents(branch: str) -> List[str]:
    """Get a list of potential parent branches from the Git history.

    This function analyzes the Git history of the specified branch and
    identifies other branches that could serve as potential parents.

    Args:
        branch: The branch name to find potential parents for

    Returns:
        A list of branch names that could be potential parents
    """
    # Get all branches
    all_branches = list_all_branches()
    if not all_branches:
        return []

    # Get the commit history of the current branch
    history_result = run_git_command(["log", "--pretty=format:%H", branch])
    if not history_result:
        return []

    commit_history = history_result.splitlines()

    # Find branches that have commits in common with the current branch
    potential_parents = []

    for other_branch in all_branches:
        # Skip the branch itself
        if other_branch == branch:
            continue

        # Check if this branch is in the history of the current branch
        merge_base = run_git_command(["merge-base", other_branch, branch])
        if not merge_base:
            continue

        # If the merge-base is in the history of the current branch, it's a potential parent
        if merge_base in commit_history:
            potential_parents.append(other_branch)

    return potential_parents
