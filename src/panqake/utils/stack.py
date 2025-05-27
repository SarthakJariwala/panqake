"""Stack data structure for managing branch relationships in panqake."""

import json
from pathlib import Path
from typing import List, Set

from panqake.utils.git import get_repo_id
from panqake.utils.questionary_prompt import format_branch
from panqake.utils.types import (
    BranchMetadata,
    BranchName,
    ParentBranchName,
    RepoId,
    SerializedStacksData,
    StacksData,
)

# Global constants
PANQAKE_DIR: Path = Path.home() / ".panqake"
STACK_FILE: Path = PANQAKE_DIR / "stacks.json"


class Branch:
    """Represents a branch in a stack with its relationships."""

    def __init__(self, name: BranchName, parent: ParentBranchName = "") -> None:
        """Initialize a branch with its name and parent.

        Args:
            name: The name of the branch
            parent: The name of the parent branch (empty string for root branches)
        """
        self.name = name
        self.parent = parent

    def to_dict(self) -> BranchMetadata:
        """Convert branch to dictionary for serialization.

        Returns:
            Dict containing the branch data
        """
        return {"parent": self.parent}

    @classmethod
    def from_dict(cls, name: BranchName, data: BranchMetadata) -> "Branch":
        """Create a Branch instance from dictionary data.

        Args:
            name: The name of the branch
            data: The dictionary containing branch data

        Returns:
            A new Branch instance
        """
        return cls(name, data.get("parent", ""))


class Stacks:
    """Manages the hierarchical branch relationships."""

    def __init__(self) -> None:
        """Initialize an empty stacks structure."""
        self._branches: StacksData = {}
        self._current_repo_id: RepoId | None = None
        self._loaded = False
        # Auto-load data on initialization
        self._ensure_loaded()

    def _ensure_loaded(self) -> bool:
        """Ensure stacks data is loaded.

        Returns:
            bool: True if data was loaded successfully, False otherwise
        """
        if self._loaded:
            return True
        return self.load()

    def _ensure_repo_id(self) -> bool:
        """Ensure current repository ID is set.

        Returns:
            bool: True if repo ID is available, False otherwise
        """
        if not self._current_repo_id:
            self._current_repo_id = get_repo_id()
        return bool(self._current_repo_id)

    def _ensure_repo_exists(self) -> bool:
        """Ensure repository entry exists in stacks.

        Returns:
            bool: True if the repository exists or was created, False otherwise
        """
        if not self._ensure_repo_id():
            return False

        if (
            self._current_repo_id is not None
            and self._current_repo_id not in self._branches
        ):
            self._branches[self._current_repo_id] = {}
        return True

    def load(self) -> bool:
        """Load stacks data from file.

        Returns:
            bool: True if loading was successful, False otherwise
        """
        if not STACK_FILE.exists():
            # Initialize empty structure
            self._branches = {}
            self._loaded = True
            return True

        try:
            with open(STACK_FILE, "r") as f:
                try:
                    raw_data: SerializedStacksData = json.load(f)

                    # Convert raw data to Branch objects
                    self._branches = {}
                    for repo_id, branches in raw_data.items():
                        self._branches[repo_id] = {}
                        for branch_name, branch_data in branches.items():
                            self._branches[repo_id][branch_name] = Branch.from_dict(
                                branch_name, branch_data
                            )

                    self._current_repo_id = get_repo_id()
                    self._loaded = True
                    return True
                except json.JSONDecodeError:
                    return False
        except (IOError, OSError):
            return False

    def save(self) -> bool:
        """Save stacks data to file.

        Returns:
            bool: True if saving was successful, False otherwise
        """
        # Ensure panqake directory exists
        if not PANQAKE_DIR.exists():
            PANQAKE_DIR.mkdir(parents=True)

        try:
            # Convert Branch objects to dictionaries
            raw_data: SerializedStacksData = {}
            for repo_id, branches in self._branches.items():
                raw_data[repo_id] = {}
                for branch_name, branch in branches.items():
                    raw_data[repo_id][branch_name] = branch.to_dict()

            with open(STACK_FILE, "w") as f:
                json.dump(raw_data, f, indent=2)
            return True
        except (IOError, OSError):
            return False

    def get_parent(self, branch: BranchName) -> ParentBranchName:
        """Get the parent branch of the given branch.

        Args:
            branch: The name of the branch

        Returns:
            The name of the parent branch, or empty string if not found
        """
        if not self._ensure_loaded() or not self._ensure_repo_id():
            return ""

        if (
            self._current_repo_id is not None
            and self._current_repo_id in self._branches
            and branch in self._branches[self._current_repo_id]
        ):
            return self._branches[self._current_repo_id][branch].parent
        return ""

    def get_children(self, branch: BranchName) -> List[BranchName]:
        """Get all immediate child branches of the given branch.

        Args:
            branch: The name of the branch

        Returns:
            A list of child branch names
        """
        if not self._ensure_loaded() or not self._ensure_repo_id():
            return []

        children: List[BranchName] = []
        if (
            self._current_repo_id is not None
            and self._current_repo_id in self._branches
        ):
            for child_name, child_branch in self._branches[
                self._current_repo_id
            ].items():
                if child_branch.parent == branch:
                    children.append(child_name)
        return children

    def add_branch(self, branch: BranchName, parent: ParentBranchName) -> bool:
        """Add a branch to the stack.

        Args:
            branch: The name of the branch to add
            parent: The name of the parent branch

        Returns:
            bool: True if the branch was added successfully, False otherwise
        """
        if not self._ensure_loaded() or not self._ensure_repo_exists():
            return False

        if self._current_repo_id is not None:
            self._branches[self._current_repo_id][branch] = Branch(branch, parent)
        return self.save()

    def remove_branch(self, branch: BranchName) -> bool:
        """Remove a branch from the stack and update child references.

        This method removes the specified branch from the stack and updates
        any child branches to reference the parent of the removed branch.

        Args:
            branch: The name of the branch to remove

        Returns:
            bool: True if the branch was removed successfully, False otherwise
        """
        if not self._ensure_loaded() or not self._ensure_repo_id():
            return False

        repo_id: RepoId | None = self._current_repo_id
        if (
            repo_id is None
            or repo_id not in self._branches
            or branch not in self._branches[repo_id]
        ):
            return False

        # Get the parent of the branch being removed
        parent: ParentBranchName = self._branches[repo_id][branch].parent

        # Update all children of this branch to point to its parent
        for child_name, child_branch in self._branches[repo_id].items():
            if child_branch.parent == branch:
                child_branch.parent = parent

        # Remove the branch
        del self._branches[repo_id][branch]

        # Save changes
        return self.save()

    def get_branch_lineage(self, branch: BranchName) -> List[BranchName]:
        """Get the ancestry chain of a branch (all parents up to root).

        Args:
            branch: The name of the branch

        Returns:
            A list of branch names representing the lineage, starting with the given branch
        """
        if not self._ensure_loaded() or not self._ensure_repo_id():
            return []

        # Check if branch exists first
        repo_id: RepoId | None = self._current_repo_id
        if (
            repo_id is None
            or repo_id not in self._branches
            or branch not in self._branches[repo_id]
        ):
            return []

        lineage: List[BranchName] = []
        current: BranchName = branch
        visited: Set[BranchName] = set()  # Protect against circular references

        while current and current not in visited:
            lineage.append(current)
            visited.add(current)
            current = self.get_parent(current)

        return lineage

    def _would_create_cycle(
        self, branch: BranchName, new_parent: ParentBranchName
    ) -> bool:
        """Check if changing a branch's parent would create a cycle.

        Args:
            branch: The branch being modified
            new_parent: The proposed new parent

        Returns:
            bool: True if a cycle would be created, False otherwise
        """
        # If new_parent is in the descendants of branch, it would create a cycle
        if new_parent == branch:
            return True

        # Check if new_parent is a descendant of branch
        descendants = self.get_all_descendants(branch)
        return new_parent in descendants

    def get_all_descendants(self, branch: BranchName) -> List[BranchName]:
        """Get all descendant branches of the given branch (children, grandchildren, etc.).

        Args:
            branch: The name of the branch

        Returns:
            A list of all descendant branch names
        """
        if not self._ensure_loaded() or not self._ensure_repo_id():
            return []

        descendants: List[BranchName] = []
        to_process: List[BranchName] = self.get_children(branch)
        processed: Set[BranchName] = set()

        while to_process:
            current: BranchName = to_process.pop(0)
            if current not in processed:
                descendants.append(current)
                processed.add(current)
                to_process.extend(self.get_children(current))

        return descendants

    def change_parent(self, branch: BranchName, new_parent: ParentBranchName) -> bool:
        """Change the parent of a branch.

        Args:
            branch: The name of the branch to update
            new_parent: The name of the new parent branch

        Returns:
            bool: True if the parent was changed successfully, False otherwise
        """
        if not self._ensure_loaded() or not self._ensure_repo_exists():
            return False

        repo_id: RepoId | None = self._current_repo_id
        if (
            repo_id is None
            or repo_id not in self._branches
            or branch not in self._branches[repo_id]
        ):
            return False

        # Avoid circular references - check if new_parent is a descendant of branch
        if new_parent and self._would_create_cycle(branch, new_parent):
            return False

        # If new_parent doesn't exist and it's not empty, return False
        if new_parent and (
            repo_id not in self._branches or new_parent not in self._branches[repo_id]
        ):
            return False

        self._branches[repo_id][branch].parent = new_parent
        return self.save()

    def get_common_ancestor(
        self, branch1: BranchName, branch2: BranchName
    ) -> BranchName | None:
        """Find the common ancestor of two branches.

        Args:
            branch1: The name of the first branch
            branch2: The name of the second branch

        Returns:
            The name of the common ancestor branch, or None if not found
        """
        if not self._ensure_loaded() or not self._ensure_repo_id():
            return None

        lineage1: List[BranchName] = self.get_branch_lineage(branch1)
        lineage2: List[BranchName] = self.get_branch_lineage(branch2)

        # Convert second lineage to a set for faster lookup
        lineage2_set: Set[BranchName] = set(lineage2)

        # Find the first common branch
        for branch in lineage1:
            if branch in lineage2_set:
                return branch

        return None

    def _format_branch_display(
        self, branch: BranchName, current_branch: BranchName
    ) -> str:
        """Format branch display with current branch indicator.

        Args:
            branch: Branch name to format
            current_branch: Current branch name for highlighting

        Returns:
            Formatted branch display string
        """

        is_current: bool = branch == current_branch
        return format_branch(branch, current=is_current)

    def _print_branch_tree(
        self, start_branch: BranchName, current_branch: BranchName
    ) -> List[str]:
        """Generate tree representation of branch hierarchy.

        Args:
            start_branch: Starting branch for the tree
            current_branch: Current branch name for highlighting

        Returns:
            List of formatted lines for the tree
        """
        output: List[str] = []

        # Track branches to process with their indent and last-sibling status
        # Each item is (branch, indent, is_last_child)
        queue: List[tuple[BranchName, str, bool]] = [(start_branch, "", True)]

        while queue:
            branch, indent, is_last = queue.pop(0)

            # Determine the connector for this branch
            if indent:  # Not the root
                connector = "└── " if is_last else "├── "
            else:  # Root branch
                connector = ""

            # Format and add the branch
            output.append(
                f"{indent}{connector}{self._format_branch_display(branch, current_branch)}"
            )

            # Get children
            children: List[BranchName] = sorted(self.get_children(branch))
            child_count: int = len(children)

            if children:
                # Calculate indent for children: add vertical line or space
                child_indent: str = indent + ("    " if is_last else "│   ")

                # Add children to queue
                for i, child in enumerate(children):
                    is_last_child: bool = i == child_count - 1
                    queue.insert(i, (child, child_indent, is_last_child))

        return output

    def visualize_tree(
        self, root: BranchName = "", current_branch: BranchName = ""
    ) -> str:
        """Generate a text representation of the branch tree with proper formatting.

        Args:
            root: The name of the root branch (defaults to empty for all roots)
            current_branch: The current branch name to highlight (defaults to empty)

        Returns:
            A string visualization of the branch tree with proper tree connectors
        """
        if not self._ensure_loaded() or not self._ensure_repo_id():
            return ""

        repo_id: RepoId | None = self._current_repo_id
        if repo_id is None or repo_id not in self._branches:
            return ""

        output: list[str] = []

        if root:
            # Start from specific root
            output.extend(self._print_branch_tree(root, current_branch))
        else:
            # Find all root branches (branches with no parent)
            roots: List[BranchName] = []
            for branch_name, branch in self._branches[repo_id].items():
                if not branch.parent:
                    roots.append(branch_name)

            # Sort roots
            roots = sorted(roots)

            # Print each root tree
            for i, root_branch in enumerate(roots):
                if i > 0:
                    output.append("")  # Add blank line between root trees
                output.extend(self._print_branch_tree(root_branch, current_branch))

        return "\n".join(output)

    def get_all_branches(self) -> List[BranchName]:
        """Get all tracked branches for the current repository.

        Returns:
            A list of all branch names
        """
        if not self._ensure_loaded() or not self._ensure_repo_id():
            return []

        repo_id: RepoId | None = self._current_repo_id
        if repo_id is None or repo_id not in self._branches:
            return []

        return list(self._branches[repo_id].keys())

    def branch_exists(self, branch: BranchName) -> bool:
        """Check if a branch exists in the stack.

        Args:
            branch: The name of the branch

        Returns:
            bool: True if the branch exists, False otherwise
        """
        if not self._ensure_loaded() or not self._ensure_repo_id():
            return False

        repo_id: RepoId | None = self._current_repo_id
        return (
            repo_id is not None
            and repo_id in self._branches
            and branch in self._branches[repo_id]
        )

    def rename_branch(self, old_name: BranchName, new_name: BranchName) -> bool:
        """Rename a branch in the stack and update all references.

        This method performs the following:
        1. Renames the branch entry in the stack
        2. Updates any references to this branch as a parent in other branches

        Args:
            old_name: The current name of the branch
            new_name: The new name for the branch

        Returns:
            bool: True if the branch was renamed successfully, False otherwise
        """
        if not self._ensure_loaded() or not self._ensure_repo_id():
            return False

        repo_id: RepoId | None = self._current_repo_id
        if (
            repo_id is None
            or repo_id not in self._branches
            or old_name not in self._branches[repo_id]
        ):
            return False

        # Check if new name already exists in stack
        if new_name in self._branches[repo_id]:
            return False

        # Get the branch data
        branch_data: Branch = self._branches[repo_id][old_name]

        # Create new branch entry with the same parent
        self._branches[repo_id][new_name] = Branch(new_name, branch_data.parent)

        # Remove the old branch entry
        del self._branches[repo_id][old_name]

        # Update parent references in child branches
        for child_name, child_branch in self._branches[repo_id].items():
            if child_branch.parent == old_name:
                child_branch.parent = new_name

        # Save changes
        return self.save()

    def __enter__(self) -> "Stacks":
        """Context manager entry."""
        self._ensure_loaded()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """Context manager exit with auto-save."""
        self.save()
