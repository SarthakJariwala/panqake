"""Port protocols (interfaces) for dependency injection.

These protocols define the boundaries between core logic and external effects,
enabling pure unit tests without extensive mocking.
"""

from typing import Protocol

from panqake.utils.types import BranchName

from .results import FileInfo, MergeMethod


class GitPort(Protocol):
    """Interface for git operations.

    Methods raise domain exceptions on failure instead of returning bool.
    """

    def get_current_branch(self) -> BranchName | None:
        """Get the current branch name."""
        ...

    def list_all_branches(self) -> list[BranchName]:
        """Get a list of all branches."""
        ...

    def branch_exists(self, branch: BranchName) -> bool:
        """Check if a branch exists."""
        ...

    def validate_branch(self, branch: BranchName) -> None:
        """Validate that a branch exists.

        Raises:
            BranchNotFoundError: If branch does not exist
        """
        ...

    def create_branch(self, branch_name: BranchName, base_branch: BranchName) -> None:
        """Create a new branch based on the specified base branch.

        Raises:
            GitOperationError: If branch creation fails
        """
        ...

    def add_worktree(
        self, branch_name: BranchName, path: str, base_branch: BranchName
    ) -> None:
        """Create a new worktree with a new branch.

        Raises:
            WorktreeError: If worktree creation fails
        """
        ...

    def get_staged_files(self) -> list[FileInfo]:
        """Get list of staged files.

        Returns:
            List of FileInfo for each staged file
        """
        ...

    def get_unstaged_files(self) -> list[FileInfo]:
        """Get list of unstaged files.

        Returns:
            List of FileInfo for each unstaged file
        """
        ...

    def branch_has_commits(
        self, branch: BranchName, parent_branch: BranchName | None
    ) -> bool:
        """Check if branch has commits since parent.

        Returns:
            True if branch has at least one commit since parent
        """
        ...

    def stage_files(self, files: list[FileInfo]) -> None:
        """Stage the specified files.

        Raises:
            StagingError: If staging fails
        """
        ...

    def commit(self, message: str) -> None:
        """Create a new commit with the staged changes.

        Raises:
            CommitError: If commit fails
        """
        ...

    def amend_commit(self, message: str | None = None) -> None:
        """Amend the current commit.

        Args:
            message: New commit message. If None, keeps existing message.

        Raises:
            CommitError: If amend fails
        """
        ...

    def is_last_commit_amended(self) -> bool:
        """Check if the last commit was an amend operation.

        Returns:
            True if the last commit was an amend, False otherwise
        """
        ...

    def is_force_push_needed(self, branch: BranchName) -> bool:
        """Check if force push is needed for a branch.

        Returns:
            True if force push is needed, False otherwise
        """
        ...

    def push_branch(self, branch: BranchName, force_with_lease: bool = False) -> None:
        """Push a branch to the remote.

        Args:
            branch: The branch name to push
            force_with_lease: Whether to use force-with-lease for the push

        Raises:
            PushError: If push fails
        """
        ...

    def is_branch_pushed_to_remote(self, branch: BranchName) -> bool:
        """Check if a branch exists on the remote.

        Returns:
            True if branch exists on remote, False otherwise
        """
        ...

    def get_last_commit_subject(self, branch: BranchName) -> str | None:
        """Get the subject line of the last commit on a branch.

        Returns:
            The commit subject, or None if no commits
        """
        ...

    def checkout_branch(self, branch: BranchName) -> None:
        """Checkout to the specified branch.

        Raises:
            GitOperationError: If checkout fails
        """
        ...

    def delete_local_branch(self, branch: BranchName, force: bool = True) -> None:
        """Delete a local branch.

        Raises:
            GitOperationError: If deletion fails
        """
        ...

    def delete_remote_branch(self, branch: BranchName) -> None:
        """Delete a branch on the remote repository.

        Raises:
            GitOperationError: If deletion fails
        """
        ...

    def remove_worktree(self, path: str, force: bool = False) -> None:
        """Remove a worktree at the specified path.

        Raises:
            WorktreeError: If removal fails
        """
        ...

    def rebase_onto(
        self, branch: BranchName, new_base: BranchName, abort_on_conflict: bool = True
    ) -> None:
        """Rebase a branch onto a new base.

        Args:
            branch: The branch to rebase
            new_base: The new base branch
            abort_on_conflict: Whether to abort on conflict

        Raises:
            RebaseConflictError: If rebase has conflicts
            GitOperationError: If rebase fails for other reasons
        """
        ...

    def fetch_from_remote(self) -> None:
        """Fetch from remote.

        Raises:
            GitOperationError: If fetch fails
        """
        ...

    def pull_branch(self, branch: BranchName) -> None:
        """Pull latest changes for a branch.

        Raises:
            GitOperationError: If pull fails
        """
        ...

    def get_worktree_path(self, branch: BranchName) -> str | None:
        """Get the worktree path for a branch.

        Returns:
            The worktree path, or None if branch has no worktree
        """
        ...

    def get_potential_parents(self, branch: BranchName) -> list[BranchName]:
        """Get potential parent branches from git history.

        Analyzes the Git history of the specified branch and
        identifies other branches that could serve as potential parents.

        Returns:
            List of branch names that could be potential parents
        """
        ...

    def rename_branch(self, old_name: BranchName, new_name: BranchName) -> None:
        """Rename a git branch.

        Args:
            old_name: The current name of the branch
            new_name: The new name for the branch

        Raises:
            BranchNotFoundError: If old_name does not exist
            BranchExistsError: If new_name already exists
            GitOperationError: If rename fails
        """
        ...

    def get_merged_branches(self, into_branch: BranchName) -> list[BranchName]:
        """Get list of branches that have been merged into the specified branch.

        Returns:
            List of branch names merged into the target branch
        """
        ...

    def is_branch_worktree(self, branch: BranchName) -> bool:
        """Check if a branch is associated with a worktree.

        Returns:
            True if branch has a worktree, False otherwise
        """
        ...

    def has_unpushed_changes(self, branch: BranchName) -> bool:
        """Check if a branch has unpushed changes compared to remote.

        Returns:
            True if branch has unpushed commits, False otherwise
        """
        ...

    def get_commit_hash(self, branch: BranchName) -> str | None:
        """Get the commit hash for a branch.

        Returns:
            The commit hash, or None if branch doesn't exist
        """
        ...

    def rebase_onto_in_worktree(
        self, branch: BranchName, new_base: BranchName, abort_on_conflict: bool = True
    ) -> None:
        """Rebase a branch onto a new base within its worktree.

        Args:
            branch: The branch to rebase
            new_base: The new base branch
            abort_on_conflict: Whether to abort on conflict

        Raises:
            RebaseConflictError: If rebase has conflicts
            GitOperationError: If rebase fails for other reasons
        """
        ...


class GitHubPort(Protocol):
    """Interface for GitHub CLI operations."""

    def is_cli_installed(self) -> bool:
        """Check if GitHub CLI is installed."""
        ...

    def branch_has_pr(self, branch: BranchName) -> bool:
        """Check if a branch already has an open PR."""
        ...

    def get_pr_url(self, branch: BranchName) -> str | None:
        """Get the URL of an open pull request for a branch."""
        ...

    def create_pr(
        self,
        base: BranchName,
        head: BranchName,
        title: str,
        body: str = "",
        reviewers: list[str] | None = None,
        draft: bool = False,
    ) -> str | None:
        """Create a pull request.

        Args:
            base: Base branch for the PR
            head: Head branch for the PR
            title: PR title
            body: PR description
            reviewers: Optional list of reviewer usernames
            draft: Whether to create as a draft PR

        Returns:
            PR URL if creation was successful

        Raises:
            PRCreationError: If PR creation fails
        """
        ...

    def get_potential_reviewers(self) -> list[str]:
        """Get list of potential reviewers from the repository.

        Returns:
            List of usernames that can be added as reviewers
        """
        ...

    def merge_pr(self, branch: BranchName, method: MergeMethod) -> None:
        """Merge a pull request.

        Args:
            branch: The branch with the PR to merge
            method: The merge method (squash, rebase, or merge)

        Raises:
            PRMergeError: If merge fails
        """
        ...

    def get_pr_checks_status(self, branch: BranchName) -> tuple[bool, list[str]]:
        """Get the status of PR checks.

        Returns:
            Tuple of (all_passed, list of failed check names)
        """
        ...

    def update_pr_base(self, branch: BranchName, new_base: BranchName) -> None:
        """Update the base branch of a PR.

        Raises:
            PRBaseUpdateError: If update fails
        """
        ...


class ConfigPort(Protocol):
    """Interface for stack configuration operations."""

    def add_to_stack(
        self,
        branch_name: BranchName,
        parent_branch: BranchName,
        worktree_path: str | None = None,
    ) -> None:
        """Record a branch in the stack with its parent."""
        ...

    def get_parent_branch(self, branch: BranchName) -> BranchName | None:
        """Get the parent branch of the given branch.

        Returns:
            Parent branch name, or None if not in stack
        """
        ...

    def get_child_branches(self, branch: BranchName) -> list[BranchName]:
        """Get all child branches of the given branch.

        Returns:
            List of child branch names
        """
        ...

    def remove_from_stack(self, branch: BranchName) -> bool:
        """Remove a branch from the stack.

        Returns:
            True if branch was removed, False if not found
        """
        ...

    def get_worktree_path(self, branch: BranchName) -> str | None:
        """Get the worktree path for the given branch.

        Returns:
            The worktree path, or empty string if none
        """
        ...

    def set_worktree_path(self, branch: BranchName, path: str) -> bool:
        """Set the worktree path for a branch.

        Returns:
            True if successful
        """
        ...

    def rename_branch(self, old_name: BranchName, new_name: BranchName) -> bool:
        """Rename a branch in the stack and update all references.

        Updates the branch entry and any parent references in child branches.

        Args:
            old_name: The current name of the branch
            new_name: The new name for the branch

        Returns:
            True if successful, False if branch not found or new name exists
        """
        ...

    def branch_exists(self, branch: BranchName) -> bool:
        """Check if a branch is tracked in the stack.

        Returns:
            True if the branch is in the stack
        """
        ...


class UIPort(Protocol):
    """Interface for user interaction.

    All prompt methods raise UserCancelledError on Ctrl-C/cancel.
    """

    def prompt_input(
        self,
        message: str,
        default: str = "",
        completer: list[str] | None = None,
        validator: object | None = None,
    ) -> str:
        """Prompt the user for text input.

        Raises:
            UserCancelledError: If user cancels (Ctrl-C)
        """
        ...

    def prompt_path(
        self,
        message: str,
        default: str = "",
    ) -> str:
        """Prompt the user for a path.

        Raises:
            UserCancelledError: If user cancels (Ctrl-C)
        """
        ...

    def print_success(self, message: str) -> None:
        """Print a success message."""
        ...

    def print_error(self, message: str) -> None:
        """Print an error message."""
        ...

    def print_info(self, message: str) -> None:
        """Print an info message."""
        ...

    def print_muted(self, message: str) -> None:
        """Print a muted/dimmed message."""
        ...

    def prompt_select_files(
        self,
        files: list[FileInfo],
        message: str,
        default_all: bool = False,
    ) -> list[str]:
        """Prompt user to select files from a list.

        Args:
            files: List of FileInfo to choose from
            message: Prompt message
            default_all: Whether all files are selected by default

        Returns:
            List of selected file paths

        Raises:
            UserCancelledError: If user cancels
        """
        ...

    def prompt_confirm(self, message: str, default: bool = False) -> bool:
        """Prompt user for yes/no confirmation.

        Args:
            message: Question to ask
            default: Default value if user presses enter

        Returns:
            True if user confirms, False otherwise

        Raises:
            UserCancelledError: If user cancels (Ctrl-C)
        """
        ...

    def prompt_select_reviewers(
        self, potential_reviewers: list[str], include_skip_option: bool = True
    ) -> list[str]:
        """Prompt user to select reviewers from a list.

        Args:
            potential_reviewers: List of potential reviewer usernames
            include_skip_option: Whether to include a skip option

        Returns:
            List of selected reviewer usernames

        Raises:
            UserCancelledError: If user cancels
        """
        ...

    def prompt_input_multiline(
        self,
        message: str,
        default: str = "",
    ) -> str:
        """Prompt the user for multiline text input.

        Raises:
            UserCancelledError: If user cancels (Ctrl-C)
        """
        ...

    def prompt_select_branch(
        self,
        branches: list[str],
        message: str,
        current_branch: str | None = None,
        exclude_protected: bool = False,
        enable_search: bool = True,
    ) -> str | None:
        """Prompt user to select a branch from a list.

        Args:
            branches: List of branch names to choose from
            message: Prompt message
            current_branch: Current branch to exclude from selection
            exclude_protected: Whether to exclude main/master
            enable_search: Whether to enable search functionality

        Returns:
            Selected branch name, or None if no selection

        Raises:
            UserCancelledError: If user cancels
        """
        ...

    def display_branch_tree(
        self,
        root_branch: str,
        current_branch: str | None = None,
    ) -> None:
        """Display the branch stack tree.

        Args:
            root_branch: Root branch to start tree from
            current_branch: Current branch to highlight
        """
        ...


class FilesystemPort(Protocol):
    """Interface for filesystem operations."""

    def path_exists(self, path: str) -> bool:
        """Check if a path exists."""
        ...

    def is_directory(self, path: str) -> bool:
        """Check if a path is a directory."""
        ...

    def resolve_path(self, path: str) -> str:
        """Resolve and expand a path to absolute form."""
        ...
