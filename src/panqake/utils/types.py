"""Type aliases for git stacking concepts used across the panqake utils module."""

from typing import TYPE_CHECKING, Dict, TypeAlias

# Forward declaration for Branch class (defined in stack.py)
if TYPE_CHECKING:
    from panqake.utils.stack import Branch

# Core git stacking types
RepoId: TypeAlias = str
BranchName: TypeAlias = str
# Empty string indicates root branch (no parent)
ParentBranchName: TypeAlias = str
# Contains "parent" key mapping to parent branch name
BranchMetadata: TypeAlias = Dict[str, ParentBranchName]
BranchObject: TypeAlias = "Branch"
RepoBranches: TypeAlias = Dict[BranchName, BranchObject]
StacksData: TypeAlias = Dict[RepoId, RepoBranches]
SerializedStacksData: TypeAlias = Dict[RepoId, Dict[BranchName, BranchMetadata]]
