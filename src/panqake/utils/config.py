"""Configuration utilities for panqake git-stacking."""

import json

from panqake.utils.stack import PANQAKE_DIR, STACK_FILE, Stacks
from panqake.utils.types import BranchName, ParentBranchName


def init_panqake() -> None:
    """Initialize panqake directories and files."""
    # Create panqake directory if it doesn't exist
    if not PANQAKE_DIR.exists():
        PANQAKE_DIR.mkdir(parents=True)

    # Create stack file if it doesn't exist
    if not STACK_FILE.exists():
        with open(STACK_FILE, "w") as f:
            json.dump({}, f)


def get_parent_branch(branch: BranchName) -> ParentBranchName:
    """Get parent branch of the given branch."""
    stacks = Stacks()
    return stacks.get_parent(branch)


def get_child_branches(branch: BranchName) -> list[BranchName]:
    """Get all child branches of the given branch."""
    stacks = Stacks()
    return stacks.get_children(branch)


def add_to_stack(branch: BranchName, parent: ParentBranchName) -> None:
    """Add a branch to the stack."""
    stacks = Stacks()
    stacks.add_branch(branch, parent)


def remove_from_stack(branch: BranchName) -> bool:
    """Remove a branch from the stack.

    This function removes the specified branch from the stack and updates
    any child branches to reference the parent of the removed branch.

    Args:
        branch: The name of the branch to remove

    Returns:
        bool: True if the branch was removed, False otherwise
    """
    stacks = Stacks()
    return stacks.remove_branch(branch)
