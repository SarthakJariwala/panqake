"""Configuration utilities for panqake git-stacking."""

import json
import shutil
from pathlib import Path

from panqake.utils.git import get_repo_id

# Global constants
PANQAKE_DIR = Path.home() / ".panqake"
STACK_FILE = PANQAKE_DIR / "stacks.json"


def init_panqake():
    """Initialize panqake directories and files."""
    # Create panqake directory if it doesn't exist
    if not PANQAKE_DIR.exists():
        PANQAKE_DIR.mkdir(parents=True)

    # Create stack file if it doesn't exist
    if not STACK_FILE.exists():
        with open(STACK_FILE, "w") as f:
            json.dump({}, f)


def check_dependencies():
    """Check for required dependencies."""
    # Check for jq (used in JSON processing)
    if not shutil.which("jq"):
        print("Warning: jq is not installed. It's recommended for JSON processing.")
        print("Please install jq with your package manager:")
        print("  - macOS: brew install jq")
        print("  - Ubuntu/Debian: sudo apt install jq")
        print("  - CentOS/RHEL: sudo yum install jq")


def get_parent_branch(branch):
    """Get parent branch of the given branch."""
    if not STACK_FILE.exists():
        return ""

    repo_id = get_repo_id()
    with open(STACK_FILE, "r") as f:
        try:
            stacks = json.load(f)
            if repo_id in stacks and branch in stacks[repo_id]:
                return stacks[repo_id][branch].get("parent", "")
        except json.JSONDecodeError:
            print("Error reading stack file")
    return ""


def get_child_branches(branch):
    """Get all child branches of the given branch."""
    if not STACK_FILE.exists():
        return []

    repo_id = get_repo_id()
    children = []

    with open(STACK_FILE, "r") as f:
        try:
            stacks = json.load(f)
            if repo_id in stacks:
                for child_branch, data in stacks[repo_id].items():
                    if data.get("parent", "") == branch:
                        children.append(child_branch)
        except json.JSONDecodeError:
            print("Error reading stack file")

    return children


def add_to_stack(branch, parent):
    """Add a branch to the stack."""
    repo_id = get_repo_id()

    with open(STACK_FILE, "r") as f:
        try:
            stacks = json.load(f)
        except json.JSONDecodeError:
            stacks = {}

    # Create the repository entry if it doesn't exist
    if repo_id not in stacks:
        stacks[repo_id] = {}

    # Add the branch and its parent
    stacks[repo_id][branch] = {"parent": parent}

    with open(STACK_FILE, "w") as f:
        json.dump(stacks, f, indent=2)


def remove_from_stack(branch):
    """Remove a branch from the stack."""
    repo_id = get_repo_id()

    with open(STACK_FILE, "r") as f:
        try:
            stacks = json.load(f)
        except json.JSONDecodeError:
            return

    if repo_id in stacks and branch in stacks[repo_id]:
        del stacks[repo_id][branch]

        with open(STACK_FILE, "w") as f:
            json.dump(stacks, f, indent=2)
