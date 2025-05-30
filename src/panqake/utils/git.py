"""Git operations for panqake git-stacking utility."""

import os
import subprocess
import sys
from typing import Any

from panqake.utils.questionary_prompt import print_formatted_text
from panqake.utils.status import status
from panqake.utils.types import BranchName, RepoId


def is_git_repo() -> bool:
    """Check if current directory is in a git repository."""
    result = run_git_command(["rev-parse", "--is-inside-work-tree"])
    return result is not None


def run_git_command(
    command: list[str],
    silent_fail: bool = False,
    return_stderr_on_error: bool = False,
) -> str | None:
    """Run a git command and return its output.

    Args:
        command: The git command to run
        silent_fail: If True, don't print error messages on failure
        return_stderr_on_error: If True, return stderr content on failure instead of None
            (only applies when silent_fail=True)
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
            if hasattr(e, "stderr"):
                print(f"stderr: {e.stderr}")
            return None

        # When silent_fail=True and return_stderr_on_error=True, return stderr
        if return_stderr_on_error and hasattr(e, "stderr") and e.stderr:
            return e.stderr.strip()

        return None


def get_repo_id() -> RepoId | None:
    """Get the current repository identifier."""
    repo_path = run_git_command(["rev-parse", "--show-toplevel"])
    if repo_path:
        return os.path.basename(repo_path)
    return None


def get_current_branch() -> BranchName | None:
    """Get the current branch name."""
    return run_git_command(["symbolic-ref", "--short", "HEAD"])


def list_all_branches() -> list[BranchName]:
    """Get a list of all branches."""
    result = run_git_command(["branch", "--format=%(refname:short)"])
    if result:
        return result.splitlines()
    return []


def branch_exists(branch: BranchName) -> bool:
    """Check if a branch exists."""
    # Use silent_fail=True because it's normal for this command to fail when checking
    # if a branch exists before creating it
    result = run_git_command(
        ["show-ref", "--verify", f"refs/heads/{branch}"], silent_fail=True
    )
    return result is not None


def validate_branch(branch_name: BranchName | None = None) -> BranchName:
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
    if branch_name and not branch_exists(branch_name):
        print_formatted_text(
            f"<warning>Error: Branch '{branch_name}' does not exist</warning>"
        )
        sys.exit(1)

    # At this point branch_name should not be None due to earlier assignment
    if branch_name is None:
        print_formatted_text(
            "<warning>Error: Could not determine branch name</warning>"
        )
        sys.exit(1)

    return branch_name


def checkout_branch(branch_name: BranchName) -> None:
    """Checkout to the specified branch."""
    with status(f"Switching to branch '{branch_name}'..."):
        result = run_git_command(["checkout", branch_name])

    if result is not None:
        print_formatted_text(
            f"[success]Successfully switched to branch '{branch_name}'[/success]"
        )
    else:
        print_formatted_text("[danger]Failed to switch branches[/danger]")
        sys.exit(1)


def create_branch(branch_name: BranchName, base_branch: BranchName) -> None:
    """Create a new branch based on the specified base branch and checkout to it."""
    with status(f"Creating new branch '{branch_name}' based on '{base_branch}'..."):
        result = run_git_command(["checkout", "-b", branch_name, base_branch])

    if result is not None:
        print_formatted_text(
            f"[success]Successfully created and switched to branch '{branch_name}'[/success]"
        )
    else:
        print_formatted_text("[danger]Failed to create new branch[/danger]")
        sys.exit(1)


def push_branch_to_remote(branch: BranchName, force_with_lease: bool = False) -> bool:
    """Push a branch to the remote.

    Args:
        branch: The branch name to push
        force_with_lease: Whether to use force-with-lease for the push

    Returns:
        True if the push was successful, False otherwise
    """

    with status(f"Pushing {branch} to origin..."):
        push_cmd = ["push", "-u", "origin", branch]
        if force_with_lease:
            push_cmd.insert(1, "--force-with-lease")

        result = run_git_command(push_cmd)

    if result is not None:
        print_formatted_text(
            f"[success]Successfully pushed [branch]{branch}[/branch] to origin[/success]"
        )
        return True
    return False


def is_branch_pushed_to_remote(branch: BranchName) -> bool:
    """Check if a branch exists on the remote."""
    result = run_git_command(["ls-remote", "--heads", "origin", branch])
    return bool(result and result.strip())


def delete_remote_branch(branch: BranchName) -> bool:
    """Delete a branch on the remote repository."""
    with status(f"Deleting remote branch {branch}..."):
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


def get_potential_parents(branch: BranchName) -> list[BranchName]:
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


def branch_has_commits(
    branch: BranchName | None = None, parent_branch: BranchName | None = None
) -> bool:
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
        if count_output is None:
            return False
        commit_count = int(count_output)
        return commit_count > 0
    except (ValueError, TypeError, AttributeError):
        # Handle cases where count_output is None or not an integer
        print_formatted_text(
            f"[warning]Could not determine commit count for {branch} relative to {parent_branch}[/warning]"
        )
        return False  # Safer to return False if count fails


def rename_branch(old_name: BranchName, new_name: BranchName) -> bool:
    """Rename a git branch.

    Args:
        old_name: The current name of the branch
        new_name: The new name for the branch

    Returns:
        bool: True if the branch was renamed successfully, False otherwise
    """
    # Check if the new branch name already exists
    if branch_exists(new_name):
        print_formatted_text(
            f"[warning]Error: Branch '{new_name}' already exists[/warning]"
        )
        return False

    # Check if old branch exists
    if not branch_exists(old_name):
        print_formatted_text(
            f"[warning]Error: Branch '{old_name}' does not exist[/warning]"
        )
        return False

    # Get current branch to determine if we need to switch branches
    current_branch = get_current_branch()
    on_target_branch = current_branch == old_name

    with status(f"Renaming branch '{old_name}' to '{new_name}'...") as s:
        # If we're not on the branch to rename, checkout the branch first
        if not on_target_branch:
            s.update(f"Checking out {old_name}...")
            try:
                checkout_branch(old_name)
            except SystemExit:
                return False

        # Rename the branch
        s.update(f"Renaming {old_name} to {new_name}...")
        rename_cmd = ["branch", "-m", new_name]
        result = run_git_command(rename_cmd)

        if result is None:
            print_formatted_text(
                f"[danger]Failed to rename branch '{old_name}' to '{new_name}'[/danger]"
            )
            return False

        # If the renamed branch was pushed to the remote, update remote references
        if is_branch_pushed_to_remote(old_name):
            s.update("Updating remote references...")
            # Delete the old remote branch
            delete_remote_branch(old_name)
            # Push the new branch to remote
            push_branch_to_remote(new_name)

    print_formatted_text(
        f"[success]Successfully renamed branch '{old_name}' to '{new_name}'[/success]"
    )

    return True


def get_staged_files() -> list[dict[str, Any]]:
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


def get_unstaged_files() -> list[dict[str, Any]]:
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


def is_last_commit_amended() -> bool:
    """Check if the last commit was an amend operation.

    Returns:
        True if the last commit was an amend, False otherwise
    """
    # Use git reflog to check the last entry for 'amend' keyword
    reflog_result = run_git_command(["reflog", "-1"])
    if reflog_result and "amend" in reflog_result.lower():
        return True
    return False


def is_force_push_needed(branch: BranchName) -> bool:
    """Check if force push is needed for a branch by doing a dry run.

    This checks if a normal push would fail due to history rewrites.

    Args:
        branch: The branch name to check

    Returns:
        True if force push is needed, False otherwise
    """
    # Check if branch exists on remote first
    if not is_branch_pushed_to_remote(branch):
        return False  # Not on remote yet, no force push needed

    # Try a dry run push to see if it would succeed
    result = run_git_command(
        ["push", "--dry-run", "--porcelain", "origin", branch],
        silent_fail=True,
        return_stderr_on_error=True,
    )

    # If the result contains '[rejected]' or 'error: failed', force push is needed
    if result and ("[rejected]" in result or "error: failed" in result):
        return True

    return False


def has_unpushed_changes(branch: BranchName) -> bool:
    """Check if branch has unpushed changes compared to its remote counterpart.

    This uses git rev-list to compare the local and remote branches to determine
    if there are any commits that need to be pushed.

    Args:
        branch: The branch name to check

    Returns:
        True if the branch has unpushed changes, False otherwise
    """
    # Check if branch exists on remote first
    if not is_branch_pushed_to_remote(branch):
        return True  # Not on remote, so definitely needs to be pushed

    # Use rev-list to count commits that differ between local and remote
    result = run_git_command(
        ["rev-list", "--left-right", "--count", f"origin/{branch}...{branch}"],
        silent_fail=True,
    )

    if not result:
        return False  # Failed to get count, safer to assume no differences

    # Parse the output which is in format "N M" where:
    # N = number of commits in origin/branch but not in local branch
    # M = number of commits in local branch but not in origin/branch
    try:
        behind, ahead = map(int, result.split())
        return ahead > 0  # If we have local commits not in origin
    except (ValueError, TypeError):
        return False  # Parse error, safer to assume no differences
