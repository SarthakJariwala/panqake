"""Git operations for panqake git-stacking utility."""

import os
import subprocess


def is_git_repo():
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


def run_git_command(command):
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


def get_repo_id():
    """Get the current repository identifier."""
    repo_path = run_git_command(["rev-parse", "--show-toplevel"])
    if repo_path:
        return os.path.basename(repo_path)
    return None


def get_current_branch():
    """Get the current branch name."""
    return run_git_command(["symbolic-ref", "--short", "HEAD"])


def branch_exists(branch):
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
