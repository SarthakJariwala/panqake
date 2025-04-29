"""Git operations for panqake git-stacking utility."""

import os
import subprocess
import sys
from typing import List, Optional

from panqake.utils.questionary_prompt import print_formatted_text


def is_git_repo() -> bool:
    """Check if current directory is in a git repository."""
    result = run_git_command(["rev-parse", "--is-inside-work-tree"])
    return result is not None


def run_git_command(command: List[str], silent_fail: bool = False) -> Optional[str]:
    """Run a git command and return its output.

    Args:
        command: The git command to run
        silent_fail: If True, don't print error messages on failure
    """
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
        if not silent_fail:
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
    # Use silent_fail=True because it's normal for this command to fail when checking
    # if a branch exists before creating it
    result = run_git_command(
        ["show-ref", "--verify", f"refs/heads/{branch}"], silent_fail=True
    )
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


def checkout_branch(branch_name: str) -> None:
    """Checkout to the specified branch."""
    print_formatted_text(f"[info]Switching to branch '{branch_name}'...[/info]")
    result = run_git_command(["checkout", branch_name])

    if result is not None:
        print_formatted_text(
            f"[success]Successfully switched to branch '{branch_name}'[/success]"
        )
    else:
        print_formatted_text("[danger]Failed to switch branches[/danger]")
        sys.exit(1)


def create_branch(branch_name: str, base_branch: str) -> None:
    """Create a new branch based on the specified base branch and checkout to it."""
    print_formatted_text(
        f"[info]Creating new branch '{branch_name}' based on '{base_branch}'...[/info]"
    )
    result = run_git_command(["checkout", "-b", branch_name, base_branch])

    if result is not None:
        print_formatted_text(
            f"[success]Successfully created and switched to branch '{branch_name}'[/success]"
        )
    else:
        print_formatted_text("[danger]Failed to create new branch[/danger]")
        sys.exit(1)


def push_branch_to_remote(branch: str, force: bool = False) -> bool:
    """Push a branch to the remote.

    Args:
        branch: The branch name to push
        force: Whether to use force-with-lease for the push

    Returns:
        True if the push was successful, False otherwise
    """
    print_formatted_text(f"[info]Pushing [branch]{branch}[/branch] to origin...[/info]")

    push_cmd = ["push", "-u", "origin", branch]
    if force:
        push_cmd.insert(1, "--force-with-lease")
        print_formatted_text("[info]Using force-with-lease for safer force push[/info]")

    result = run_git_command(push_cmd)

    if result is not None:
        print_formatted_text(
            f"[success]Successfully pushed [branch]{branch}[/branch] to origin[/success]"
        )
        return True
    return False


def is_branch_pushed_to_remote(branch: str) -> bool:
    """Check if a branch exists on the remote."""
    result = run_git_command(["ls-remote", "--heads", "origin", branch])
    return bool(result and result.strip())


def delete_remote_branch(branch: str) -> bool:
    """Delete a branch on the remote repository."""
    print_formatted_text(
        f"[info]Deleting remote branch [branch]{branch}[/branch]...[/info]"
    )

    result = run_git_command(["push", "origin", "--delete", branch])

    if result is not None:
        print_formatted_text(
            f"[success]Remote branch [branch]{branch}[/branch] deleted successfully[/success]"
        )
        return True

    print_formatted_text(
        f"[warning]Warning: Failed to delete remote branch '{branch}'[/warning]"
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


def branch_has_commits(branch: str = None, parent_branch: Optional[str] = None) -> bool:
    """Check if the branch has any commits since the specified parent branch.

    This checks if a branch has new commits relative to a given parent.
    It relies on the caller to determine the correct parent (e.g., from stack config).

    Args:
        branch: The branch to check. If None, check current branch.
        parent_branch: The parent branch to compare against.

    Returns:
        True if the branch has at least one commit since the parent_branch,
        False otherwise (or if parent is not provided or branches invalid).
    """
    if not branch:
        branch = get_current_branch()

    if not branch:
        return False  # Cannot determine branch

    if not branch_exists(branch):
        return False  # Branch doesn't exist locally

    # If no parent is provided, we cannot determine if it has *new* commits
    if not parent_branch:
        return False

    # Ensure the provided parent branch actually exists locally before comparing
    if not branch_exists(parent_branch):
        print_formatted_text(
            f"[warning]Provided parent branch '{parent_branch}' for '{branch}' not found locally.[/warning]"
        )
        return False  # Cannot compare if parent doesn't exist

    # Count commits between the parent and the branch tip
    count_cmd = ["rev-list", "--count", f"{parent_branch}..{branch}"]
    count_output = run_git_command(count_cmd, silent_fail=True)

    try:
        commit_count = int(count_output)
        return commit_count > 0
    except (ValueError, TypeError, AttributeError):
        # Handle cases where count_output is None or not an integer
        print_formatted_text(
            f"[warning]Could not determine commit count for {branch} relative to {parent_branch}[/warning]"
        )
        return False  # Safer to return False if count fails


def get_staged_files() -> List[dict]:
    """Get a list of staged files using git diff --staged.

    Returns:
        List of dictionaries with path and display for each staged file
    """
    # Get list of staged files with their status
    staged_result = run_git_command(["diff", "--staged", "--name-status"])
    if not staged_result:
        return []

    files = []
    for line in staged_result.splitlines():
        if not line.strip():
            continue

        # Format from diff --name-status: Status<TAB>Path
        parts = line.split("\t", 1)
        if len(parts) != 2:
            continue  # Skip malformed lines

        status, path = parts
        status_type = ""

        if status == "A":
            status_type = "Added"
        elif status == "M":
            status_type = "Modified"
        elif status == "D":
            status_type = "Deleted"
        elif status.startswith("R"):
            status_type = "Renamed"
            # For renames, path is "oldpath<tab>newpath"
            old_path, new_path = path.split("\t", 1)
            files.append(
                {
                    "path": new_path,
                    "display": f"{status_type}: {old_path} → {new_path}",
                    "original_path": old_path,
                }
            )
            continue  # Skip the default append for renames
        elif status.startswith("C"):
            status_type = "Copied"
            # For copies, path is "oldpath<tab>newpath"
            old_path, new_path = path.split("\t", 1)
            files.append(
                {
                    "path": new_path,
                    "display": f"{status_type}: {old_path} → {new_path}",
                    "original_path": old_path,
                }
            )
            continue  # Skip the default append for copies
        else:
            status_type = f"Status ({status})"

        files.append(
            {
                "path": path,
                "display": f"{status_type}: {path}",
            }
        )

    return files


def get_unstaged_files() -> List[dict]:
    """Get a list of unstaged files using git ls-files and git status.

    Returns:
        List of dictionaries with path and display for each unstaged file
    """
    # Get modified unstaged files
    modified_result = run_git_command(["ls-files", "--modified"])
    modified_files = modified_result.splitlines() if modified_result else []

    # Get untracked files
    untracked_result = run_git_command(["ls-files", "--others", "--exclude-standard"])
    untracked_files = untracked_result.splitlines() if untracked_result else []

    # Get deleted unstaged files (neither modified nor untracked, have to parse status)
    status_result = run_git_command(["status", "--porcelain"])
    deleted_files = []

    if status_result:
        for line in status_result.splitlines():
            if line.startswith(" D"):  # Space + D means unstaged deletion
                deleted_files.append(line[3:])

    # Build the results list
    files = []

    # Add modified files
    for path in modified_files:
        files.append(
            {
                "path": path,
                "display": f"Modified: {path}",
            }
        )

    # Add untracked files
    for path in untracked_files:
        files.append(
            {
                "path": path,
                "display": f"Untracked: {path}",
            }
        )

    # Add deleted files
    for path in deleted_files:
        files.append(
            {
                "path": path,
                "display": f"Deleted: {path}",
            }
        )

    return files
