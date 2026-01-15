"""Result dataclasses for command operations.

These are immutable dataclasses representing the outcome of operations.
Failures are handled via exceptions, so these represent successful results.
"""

from dataclasses import dataclass
from typing import Literal

from panqake.utils.types import BranchName


@dataclass(frozen=True)
class NewBranchResult:
    """Result of creating a new branch."""

    branch_name: BranchName
    base_branch: BranchName
    worktree_path: str | None = None


@dataclass(frozen=True)
class FileInfo:
    """Information about a file for staging/display."""

    path: str
    display: str
    original_path: str | None = None


@dataclass(frozen=True)
class ModifyResult:
    """Result of modifying/committing changes."""

    branch_name: BranchName
    amended: bool
    files_staged: list[str]
    message: str | None = None


@dataclass(frozen=True)
class SubmitResult:
    """Result of submitting a branch to remote."""

    branch_name: BranchName
    force_pushed: bool
    pr_existed: bool
    pr_created: bool
    pr_url: str | None = None


BranchPRStatus = Literal["created", "already_exists", "skipped"]


@dataclass(frozen=True)
class BranchPRResult:
    """Result of creating a PR for a single branch."""

    branch: BranchName
    base: BranchName
    status: BranchPRStatus
    pr_url: str | None = None
    title: str | None = None
    reviewers: list[str] | None = None
    draft: bool | None = None
    skip_reason: str | None = None


@dataclass(frozen=True)
class CreatePRStackResult:
    """Result of creating PRs for branches in a stack."""

    target_branch: BranchName
    starting_branch: BranchName
    results: list[BranchPRResult]


MergeMethod = Literal["squash", "rebase", "merge"]


@dataclass(frozen=True)
class PRBaseUpdateResult:
    """Result of updating a PR's base reference."""

    branch: BranchName
    new_base: BranchName
    had_pr: bool
    updated: bool
    error: str | None = None


@dataclass(frozen=True)
class ChildUpdateResult:
    """Result of updating a child branch after merge."""

    branch: BranchName
    new_parent: BranchName
    rebased: bool
    error: str | None = None


@dataclass(frozen=True)
class MergeResult:
    """Result of merging a branch."""

    branch: BranchName
    parent_branch: BranchName
    original_branch: BranchName | None
    merge_method: MergeMethod

    checks_passed: bool
    failed_checks: list[str]

    pr_base_updates: list[PRBaseUpdateResult]
    child_updates: list[ChildUpdateResult]

    remote_branch_deleted: bool
    local_branch_deleted: bool
    removed_from_stack: bool

    returned_to: BranchName | None
    warnings: list[str]


@dataclass(frozen=True)
class PromptCall:
    """Record of a prompt call for test assertions."""

    message: str
    default: str = ""
    completer: list[str] | None = None
    has_validator: bool = False


@dataclass(frozen=True)
class SwitchResult:
    """Result of switching branches."""

    target_branch: BranchName
    previous_branch: BranchName | None
    switched: bool
    worktree_path: str | None = None


@dataclass(frozen=True)
class TrackResult:
    """Result of tracking a branch."""

    branch_name: BranchName
    parent_branch: BranchName


@dataclass(frozen=True)
class UntrackResult:
    """Result of untracking a branch."""

    branch_name: BranchName
    was_tracked: bool


@dataclass(frozen=True)
class UpResult:
    """Result of navigating up to parent branch."""

    target_branch: BranchName
    previous_branch: BranchName | None
    switched: bool
    worktree_path: str | None = None


@dataclass(frozen=True)
class DownResult:
    """Result of navigating down to child branch."""

    target_branch: BranchName
    previous_branch: BranchName | None
    switched: bool
    worktree_path: str | None = None


@dataclass(frozen=True)
class ListResult:
    """Result of listing the branch stack."""

    root_branch: BranchName
    current_branch: BranchName
    target_branch: BranchName


DeleteStatus = Literal["deleted", "skipped"]


@dataclass(frozen=True)
class DeleteResult:
    """Result of deleting a branch."""

    deleted_branch: BranchName | None
    parent_branch: BranchName | None
    relinked_children: list[BranchName]
    worktree_removed: bool
    removed_from_stack: bool
    status: DeleteStatus
    skip_reason: str | None = None


@dataclass(frozen=True)
class RenameResult:
    """Result of renaming a branch."""

    old_name: BranchName
    new_name: BranchName
    was_tracked: bool
    remote_updated: bool


@dataclass(frozen=True)
class BranchUpdateResult:
    """Result of updating a single branch during sync."""

    branch: BranchName
    parent: BranchName
    success: bool
    error: str | None = None


@dataclass(frozen=True)
class SyncResult:
    """Result of syncing with remote."""

    main_branch: BranchName
    original_branch: BranchName
    returned_to: BranchName | None

    deleted_branches: list[BranchName]
    updated_branches: list[BranchName]
    conflict_branches: list[BranchName]
    pushed_branches: list[BranchName]
    skipped_push_branches: list[BranchName]

    skip_push: bool


@dataclass(frozen=True)
class UpdateResult:
    """Result of updating branches in a stack."""

    starting_branch: BranchName
    original_branch: BranchName
    returned_to: BranchName | None

    affected_branches: list[BranchName]
    updated_branches: list[BranchName]
    conflict_branches: list[BranchName]
    pushed_branches: list[BranchName]
    skipped_push_branches: list[BranchName]

    skip_push: bool
