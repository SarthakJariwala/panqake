"""Configuration utilities for panqake git-stacking."""

import json
from pathlib import Path
from typing import Dict, List

from panqake.utils.git import get_repo_id

# Global constants
PANQAKE_DIR = Path.home() / ".panqake"
STACK_FILE = PANQAKE_DIR / "stacks.json"


def init_panqake() -> None:
    """Initialize panqake directories and files."""
    # Create panqake directory if it doesn't exist
    if not PANQAKE_DIR.exists():
        PANQAKE_DIR.mkdir(parents=True)

    # Create stack file if it doesn't exist
    if not STACK_FILE.exists():
        with open(STACK_FILE, "w") as f:
            json.dump({}, f)


def get_parent_branch(branch: str) -> str:
    """Get parent branch of the given branch."""
    if not STACK_FILE.exists():
        return ""

    repo_id = get_repo_id()
    with open(STACK_FILE, "r") as f:
        try:
            stacks = json.load(f)
            if repo_id and repo_id in stacks and branch in stacks[repo_id]:
                return stacks[repo_id][branch].get("parent", "")
        except json.JSONDecodeError:
            print("Error reading stack file")
    return ""


def get_child_branches(branch: str) -> List[str]:
    """Get all child branches of the given branch."""
    if not STACK_FILE.exists():
        return []

    repo_id = get_repo_id()
    children: List[str] = []

    with open(STACK_FILE, "r") as f:
        try:
            stacks = json.load(f)
            if repo_id and repo_id in stacks:
                for child_branch, data in stacks[repo_id].items():
                    if data.get("parent", "") == branch:
                        children.append(child_branch)
        except json.JSONDecodeError:
            print("Error reading stack file")

    return children


def add_to_stack(branch: str, parent: str) -> None:
    """Add a branch to the stack."""
    repo_id = get_repo_id()
    if not repo_id:
        return

    with open(STACK_FILE, "r") as f:
        try:
            stacks: Dict[str, Dict[str, Dict[str, str]]] = json.load(f)
        except json.JSONDecodeError:
            stacks = {}

    # Create the repository entry if it doesn't exist
    if repo_id not in stacks:
        stacks[repo_id] = {}

    # Add the branch and its parent
    stacks[repo_id][branch] = {"parent": parent}

    with open(STACK_FILE, "w") as f:
        json.dump(stacks, f, indent=2)


def remove_from_stack(branch: str) -> None:
    """Remove a branch from the stack."""
    repo_id = get_repo_id()
    if not repo_id:
        return

    with open(STACK_FILE, "r") as f:
        try:
            stacks = json.load(f)
        except json.JSONDecodeError:
            return

    if repo_id in stacks and branch in stacks[repo_id]:
        del stacks[repo_id][branch]

        with open(STACK_FILE, "w") as f:
            json.dump(stacks, f, indent=2)
