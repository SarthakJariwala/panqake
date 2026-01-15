"""Domain exceptions for panqake.

All exceptions inherit from PanqakeError which provides a message and exit_code.
"""


class PanqakeError(Exception):
    """Base exception for panqake domain errors."""

    def __init__(self, message: str, exit_code: int = 1):
        super().__init__(message)
        self.message = message
        self.exit_code = exit_code


class BranchExistsError(PanqakeError):
    """Raised when trying to create a branch that already exists."""

    pass


class BranchNotFoundError(PanqakeError):
    """Raised when a required branch does not exist."""

    pass


class WorktreeError(PanqakeError):
    """Raised when worktree operations fail."""

    pass


class UserCancelledError(PanqakeError):
    """Raised when user cancels an operation."""

    def __init__(self):
        super().__init__("Interrupted by user", exit_code=130)


class GitOperationError(PanqakeError):
    """Raised when a git operation fails."""

    pass


class NoChangesError(PanqakeError):
    """Raised when there are no changes to commit."""

    pass


class CommitError(PanqakeError):
    """Raised when commit or amend fails."""

    pass


class StagingError(PanqakeError):
    """Raised when staging files fails."""

    pass


class PushError(PanqakeError):
    """Raised when push operation fails."""

    pass


class GitHubCLINotFoundError(PanqakeError):
    """Raised when GitHub CLI is not installed."""

    pass


class PRCreationError(PanqakeError):
    """Raised when PR creation fails."""

    pass


class PRMergeError(PanqakeError):
    """Raised when PR merge fails."""

    pass


class PRBaseUpdateError(PanqakeError):
    """Raised when updating PR base fails."""

    pass


class RebaseConflictError(PanqakeError):
    """Raised when rebase has conflicts."""

    pass


class CannotDeleteCurrentBranchError(GitOperationError):
    """Raised when trying to delete the current branch."""

    pass


class InWorktreeBeingDeletedError(GitOperationError):
    """Raised when user is in the worktree being deleted."""

    def __init__(self, worktree_path: str, repo_root: str):
        super().__init__(
            f"Cannot delete branch: currently in worktree at '{worktree_path}'"
        )
        self.worktree_path = worktree_path
        self.repo_root = repo_root
