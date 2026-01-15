"""
Fake implementations of ports for testing with simple, inspectable in-memory state.
"""

from dataclasses import dataclass, field

from panqake.ports import (
    BranchNotFoundError,
    CommitError,
    FileInfo,
    GitOperationError,
    MergeMethod,
    PRBaseUpdateError,
    PRCreationError,
    PRMergeError,
    PromptCall,
    PushError,
    RebaseConflictError,
    StagingError,
    UserCancelledError,
    WorktreeError,
)
from panqake.utils.types import BranchName


class FakeGit:
    """In-memory fake for GitPort.

    Maintains a simple branch graph that tests can inspect.
    """

    def __init__(
        self,
        branches: list[BranchName] | None = None,
        current_branch: BranchName | None = "main",
        staged_files: list[FileInfo] | None = None,
        unstaged_files: list[FileInfo] | None = None,
        branch_commits: dict[BranchName, bool] | None = None,
        last_commit_amended: bool = False,
        force_push_needed: dict[BranchName, bool] | None = None,
        pushed_branches: set[BranchName] | None = None,
        commit_subjects: dict[BranchName, str] | None = None,
        potential_parents: dict[BranchName, list[BranchName]] | None = None,
        merged_branches: dict[BranchName, list[BranchName]] | None = None,
        unpushed_changes: dict[BranchName, bool] | None = None,
        commit_hashes: dict[BranchName, str] | None = None,
    ):
        self.branches: set[BranchName] = set(
            branches if branches is not None else ["main"]
        )
        self.current_branch: BranchName | None = current_branch
        self.worktrees: dict[BranchName, str] = {}
        self.staged_files: list[FileInfo] = list(staged_files or [])
        self.unstaged_files: list[FileInfo] = list(unstaged_files or [])
        self.branch_commits: dict[BranchName, bool] = dict(branch_commits or {})
        self._last_commit_amended: bool = last_commit_amended
        self._force_push_needed: dict[BranchName, bool] = dict(force_push_needed or {})
        self._pushed_branches: set[BranchName] = set(pushed_branches or set())
        self._commit_subjects: dict[BranchName, str] = dict(commit_subjects or {})
        self._potential_parents: dict[BranchName, list[BranchName]] = dict(
            potential_parents or {}
        )
        self._merged_branches: dict[BranchName, list[BranchName]] = dict(
            merged_branches or {}
        )
        self._unpushed_changes: dict[BranchName, bool] = dict(unpushed_changes or {})
        self._commit_hashes: dict[BranchName, str] = dict(commit_hashes or {})

        # Track calls for verification
        self.created_branches: list[tuple[BranchName, BranchName]] = []
        self.created_worktrees: list[tuple[BranchName, str, BranchName]] = []
        self.staged_file_calls: list[list[FileInfo]] = []
        self.commits: list[str] = []
        self.amend_calls: list[str | None] = []
        self.push_calls: list[tuple[BranchName, bool]] = []

        # Track calls for new methods
        self.checkout_calls: list[BranchName] = []
        self.deleted_local_branches: list[BranchName] = []
        self.deleted_remote_branches: list[BranchName] = []
        self.removed_worktrees: list[str] = []
        self.rebase_calls: list[tuple[BranchName, BranchName]] = []
        self.fetch_calls: int = 0
        self.pull_calls: list[BranchName] = []

        # Track rename calls
        self.rename_calls: list[tuple[BranchName, BranchName]] = []

        # Configure failures
        self.fail_create_branch: bool = False
        self.fail_add_worktree: bool = False
        self.fail_stage: bool = False
        self.fail_commit: bool = False
        self.fail_amend: bool = False
        self.fail_push: bool = False
        self.fail_checkout: bool = False
        self.fail_delete_local: bool = False
        self.fail_delete_remote: bool = False
        self.fail_remove_worktree: bool = False
        self.fail_rebase: bool = False
        self.fail_fetch: bool = False
        self.fail_pull: bool = False
        self.fail_rename: bool = False

    def get_current_branch(self) -> BranchName | None:
        return self.current_branch

    def list_all_branches(self) -> list[BranchName]:
        return sorted(self.branches)

    def branch_exists(self, branch: BranchName) -> bool:
        return branch in self.branches

    def validate_branch(self, branch: BranchName) -> None:
        if branch not in self.branches:
            raise BranchNotFoundError(f"Branch '{branch}' does not exist")

    def create_branch(self, branch_name: BranchName, base_branch: BranchName) -> None:
        if self.fail_create_branch:
            raise GitOperationError(f"Failed to create branch '{branch_name}'")
        if branch_name in self.branches:
            raise GitOperationError(f"Branch '{branch_name}' already exists")
        if base_branch not in self.branches:
            raise GitOperationError(f"Base branch '{base_branch}' does not exist")

        self.branches.add(branch_name)
        self.current_branch = branch_name
        self.created_branches.append((branch_name, base_branch))

    def add_worktree(
        self, branch_name: BranchName, path: str, base_branch: BranchName
    ) -> None:
        if self.fail_add_worktree:
            raise WorktreeError(f"Failed to create worktree at '{path}'")
        if branch_name in self.branches:
            raise WorktreeError(f"Branch '{branch_name}' already exists")
        if base_branch not in self.branches:
            raise WorktreeError(f"Base branch '{base_branch}' does not exist")

        self.branches.add(branch_name)
        self.worktrees[branch_name] = path
        self.created_worktrees.append((branch_name, path, base_branch))

    def get_staged_files(self) -> list[FileInfo]:
        return list(self.staged_files)

    def get_unstaged_files(self) -> list[FileInfo]:
        return list(self.unstaged_files)

    def branch_has_commits(
        self, branch: BranchName, parent_branch: BranchName | None
    ) -> bool:
        return self.branch_commits.get(branch, False)

    def stage_files(self, files: list[FileInfo]) -> None:
        if self.fail_stage:
            raise StagingError("Failed to stage files")
        self.staged_file_calls.append(list(files))
        for f in files:
            self.staged_files.append(f)

    def commit(self, message: str) -> None:
        if self.fail_commit:
            raise CommitError("Failed to create commit")
        self.commits.append(message)

    def amend_commit(self, message: str | None = None) -> None:
        if self.fail_amend:
            raise CommitError("Failed to amend commit")
        self.amend_calls.append(message)

    def is_last_commit_amended(self) -> bool:
        return self._last_commit_amended

    def is_force_push_needed(self, branch: BranchName) -> bool:
        return self._force_push_needed.get(branch, False)

    def push_branch(self, branch: BranchName, force_with_lease: bool = False) -> None:
        if self.fail_push:
            raise PushError(f"Failed to push branch '{branch}' to remote")
        self.push_calls.append((branch, force_with_lease))
        self._pushed_branches.add(branch)

    def is_branch_pushed_to_remote(self, branch: BranchName) -> bool:
        return branch in self._pushed_branches

    def get_last_commit_subject(self, branch: BranchName) -> str | None:
        return self._commit_subjects.get(branch)

    def checkout_branch(self, branch: BranchName) -> None:
        if self.fail_checkout:
            raise GitOperationError(f"Failed to checkout branch '{branch}'")
        if branch not in self.branches:
            raise GitOperationError(f"Branch '{branch}' does not exist")
        self.current_branch = branch
        self.checkout_calls.append(branch)

    def delete_local_branch(self, branch: BranchName, force: bool = True) -> None:
        if self.fail_delete_local:
            raise GitOperationError(f"Failed to delete local branch '{branch}'")
        if branch not in self.branches:
            raise GitOperationError(f"Branch '{branch}' does not exist")
        if branch == self.current_branch:
            raise GitOperationError("Cannot delete currently checked out branch")
        self.branches.discard(branch)
        self.deleted_local_branches.append(branch)

    def delete_remote_branch(self, branch: BranchName) -> None:
        if self.fail_delete_remote:
            raise GitOperationError(f"Failed to delete remote branch '{branch}'")
        self._pushed_branches.discard(branch)
        self.deleted_remote_branches.append(branch)

    def remove_worktree(self, path: str, force: bool = False) -> None:
        if self.fail_remove_worktree:
            raise WorktreeError(f"Failed to remove worktree at '{path}'")
        branch_to_remove = None
        for branch, wt_path in self.worktrees.items():
            if wt_path == path:
                branch_to_remove = branch
                break
        if branch_to_remove:
            del self.worktrees[branch_to_remove]
        self.removed_worktrees.append(path)

    def rebase_onto(
        self, branch: BranchName, new_base: BranchName, abort_on_conflict: bool = True
    ) -> None:
        if self.fail_rebase:
            raise RebaseConflictError(f"Rebase conflict in branch '{branch}'")
        if branch not in self.branches:
            raise GitOperationError(f"Branch '{branch}' does not exist")
        if new_base not in self.branches:
            raise GitOperationError(f"Base branch '{new_base}' does not exist")
        self.current_branch = branch
        self.rebase_calls.append((branch, new_base))

    def fetch_from_remote(self) -> None:
        if self.fail_fetch:
            raise GitOperationError("Failed to fetch from remote")
        self.fetch_calls += 1

    def pull_branch(self, branch: BranchName) -> None:
        if self.fail_pull:
            raise GitOperationError(f"Failed to pull branch '{branch}'")
        self.pull_calls.append(branch)

    def get_worktree_path(self, branch: BranchName) -> str | None:
        return self.worktrees.get(branch)

    def get_potential_parents(self, branch: BranchName) -> list[BranchName]:
        return self._potential_parents.get(branch, [])

    def rename_branch(self, old_name: BranchName, new_name: BranchName) -> None:
        from panqake.ports import BranchExistsError

        if self.fail_rename:
            raise GitOperationError(
                f"Failed to rename branch '{old_name}' to '{new_name}'"
            )
        if old_name not in self.branches:
            raise BranchNotFoundError(f"Branch '{old_name}' does not exist")
        if new_name in self.branches:
            raise BranchExistsError(f"Branch '{new_name}' already exists")

        self.branches.discard(old_name)
        self.branches.add(new_name)

        if self.current_branch == old_name:
            self.current_branch = new_name

        if old_name in self.worktrees:
            self.worktrees[new_name] = self.worktrees.pop(old_name)

        if old_name in self._pushed_branches:
            self._pushed_branches.discard(old_name)
            self._pushed_branches.add(new_name)

        self.rename_calls.append((old_name, new_name))

    def get_merged_branches(self, into_branch: BranchName) -> list[BranchName]:
        return list(self._merged_branches.get(into_branch, []))

    def is_branch_worktree(self, branch: BranchName) -> bool:
        return branch in self.worktrees

    def has_unpushed_changes(self, branch: BranchName) -> bool:
        return self._unpushed_changes.get(branch, False)

    def get_commit_hash(self, branch: BranchName) -> str | None:
        return self._commit_hashes.get(branch)

    def rebase_onto_in_worktree(
        self, branch: BranchName, new_base: BranchName, abort_on_conflict: bool = True
    ) -> None:
        if self.fail_rebase:
            raise RebaseConflictError(f"Rebase conflict in branch '{branch}'")
        if branch not in self.branches:
            raise GitOperationError(f"Branch '{branch}' does not exist")
        if new_base not in self.branches:
            raise GitOperationError(f"Base branch '{new_base}' does not exist")
        self.rebase_calls.append((branch, new_base))


class FakeGitHub:
    """In-memory fake for GitHubPort."""

    def __init__(
        self,
        cli_installed: bool = True,
        branches_with_pr: set[BranchName] | None = None,
        pr_urls: dict[BranchName, str] | None = None,
        potential_reviewers: list[str] | None = None,
        pr_checks: dict[BranchName, tuple[bool, list[str]]] | None = None,
    ):
        self._cli_installed: bool = cli_installed
        self._branches_with_pr: set[BranchName] = set(branches_with_pr or set())
        self._pr_urls: dict[BranchName, str] = dict(pr_urls or {})
        self._potential_reviewers: list[str] = list(potential_reviewers or [])
        self._pr_checks: dict[BranchName, tuple[bool, list[str]]] = dict(
            pr_checks or {}
        )

        # Track calls for verification
        self.create_pr_calls: list[
            tuple[BranchName, BranchName, str, str, list[str] | None, bool]
        ] = []
        self.created_prs: dict[BranchName, str] = {}
        self.merge_pr_calls: list[tuple[BranchName, MergeMethod]] = []
        self.update_pr_base_calls: list[tuple[BranchName, BranchName]] = []
        self.merged_prs: set[BranchName] = set()

        # Configure failures
        self.fail_create_pr: bool = False
        self.fail_merge_pr: bool = False
        self.fail_update_pr_base: bool = False

    def is_cli_installed(self) -> bool:
        return self._cli_installed

    def branch_has_pr(self, branch: BranchName) -> bool:
        return branch in self._branches_with_pr or branch in self.created_prs

    def get_pr_url(self, branch: BranchName) -> str | None:
        if branch in self.created_prs:
            return self.created_prs[branch]
        return self._pr_urls.get(branch)

    def create_pr(
        self,
        base: BranchName,
        head: BranchName,
        title: str,
        body: str = "",
        reviewers: list[str] | None = None,
        draft: bool = False,
    ) -> str | None:
        self.create_pr_calls.append((base, head, title, body, reviewers, draft))

        if self.fail_create_pr:
            raise PRCreationError(f"Failed to create PR for branch '{head}'")

        url = f"https://github.com/test/repo/pull/{len(self.create_pr_calls)}"
        self.created_prs[head] = url
        self._branches_with_pr.add(head)
        return url

    def get_potential_reviewers(self) -> list[str]:
        return list(self._potential_reviewers)

    def merge_pr(self, branch: BranchName, method: MergeMethod) -> None:
        self.merge_pr_calls.append((branch, method))
        if self.fail_merge_pr:
            raise PRMergeError(f"Failed to merge PR for branch '{branch}'")
        if branch not in self._branches_with_pr:
            raise PRMergeError(f"Branch '{branch}' does not have a PR")
        self._branches_with_pr.discard(branch)
        self.merged_prs.add(branch)

    def get_pr_checks_status(self, branch: BranchName) -> tuple[bool, list[str]]:
        return self._pr_checks.get(branch, (True, []))

    def update_pr_base(self, branch: BranchName, new_base: BranchName) -> None:
        self.update_pr_base_calls.append((branch, new_base))
        if self.fail_update_pr_base:
            raise PRBaseUpdateError(
                f"Failed to update PR base for '{branch}' to '{new_base}'"
            )


class FakeConfig:
    """In-memory fake for ConfigPort.

    Maintains a simple stack structure that tests can inspect.
    """

    def __init__(self, stack: dict[BranchName, dict] | None = None):
        self.stack: dict[BranchName, dict] = dict(stack or {})

    def add_to_stack(
        self,
        branch_name: BranchName,
        parent_branch: BranchName,
        worktree_path: str | None = None,
    ) -> None:
        entry = {"parent": parent_branch}
        if worktree_path:
            entry["worktree"] = worktree_path
        self.stack[branch_name] = entry

    def get_parent_branch(self, branch: BranchName) -> BranchName | None:
        entry = self.stack.get(branch)
        if entry:
            return entry.get("parent")
        return None

    def get_child_branches(self, branch: BranchName) -> list[BranchName]:
        children = []
        for name, entry in self.stack.items():
            if entry.get("parent") == branch:
                children.append(name)
        return children

    def remove_from_stack(self, branch: BranchName) -> bool:
        if branch in self.stack:
            del self.stack[branch]
            return True
        return False

    def get_worktree_path(self, branch: BranchName) -> str | None:
        entry = self.stack.get(branch)
        if entry:
            path = entry.get("worktree")
            return path if path else None
        return None

    def set_worktree_path(self, branch: BranchName, path: str) -> bool:
        if branch in self.stack:
            if path:
                self.stack[branch]["worktree"] = path
            elif "worktree" in self.stack[branch]:
                del self.stack[branch]["worktree"]
            return True
        return False

    def rename_branch(self, old_name: BranchName, new_name: BranchName) -> bool:
        if old_name not in self.stack or new_name in self.stack:
            return False

        entry = self.stack.pop(old_name)
        self.stack[new_name] = entry

        for child_entry in self.stack.values():
            if child_entry.get("parent") == old_name:
                child_entry["parent"] = new_name

        return True

    def branch_exists(self, branch: BranchName) -> bool:
        return branch in self.stack


@dataclass
class FakeUI:
    """Scriptable fake for UIPort.

    Provide responses in advance, then verify what was prompted/printed.
    In strict mode (default), raises if no response is queued.
    """

    input_responses: list[str] = field(default_factory=list)
    path_responses: list[str] = field(default_factory=list)
    select_files_responses: list[list[str]] = field(default_factory=list)
    confirm_responses: list[bool] = field(default_factory=list)
    select_reviewers_responses: list[list[str]] = field(default_factory=list)
    input_multiline_responses: list[str] = field(default_factory=list)
    select_branch_responses: list[str | None] = field(default_factory=list)
    strict: bool = True

    # Track all interactions
    input_calls: list[PromptCall] = field(default_factory=list)
    path_calls: list[PromptCall] = field(default_factory=list)
    select_files_calls: list[tuple[list[FileInfo], str, bool]] = field(
        default_factory=list
    )
    confirm_calls: list[tuple[str, bool]] = field(default_factory=list)
    select_reviewers_calls: list[tuple[list[str], bool]] = field(default_factory=list)
    input_multiline_calls: list[PromptCall] = field(default_factory=list)
    select_branch_calls: list[tuple[list[str], str, str | None, bool, bool]] = field(
        default_factory=list
    )
    display_tree_calls: list[tuple[str, str | None]] = field(default_factory=list)
    success_messages: list[str] = field(default_factory=list)
    error_messages: list[str] = field(default_factory=list)
    info_messages: list[str] = field(default_factory=list)
    muted_messages: list[str] = field(default_factory=list)

    # Simulate cancellation
    cancel_on_input: bool = False
    cancel_on_path: bool = False
    cancel_on_select_files: bool = False
    cancel_on_confirm: bool = False
    cancel_on_select_reviewers: bool = False
    cancel_on_input_multiline: bool = False
    cancel_on_select_branch: bool = False

    def __post_init__(self):
        # Convert to mutable lists if tuples passed
        self.input_responses = list(self.input_responses)
        self.path_responses = list(self.path_responses)
        self.select_files_responses = list(self.select_files_responses)
        self.confirm_responses = list(self.confirm_responses)
        self.select_reviewers_responses = list(self.select_reviewers_responses)
        self.input_multiline_responses = list(self.input_multiline_responses)
        self.select_branch_responses = list(self.select_branch_responses)

    def prompt_input(
        self,
        message: str,
        default: str = "",
        completer: list[str] | None = None,
        validator: object | None = None,
    ) -> str:
        self.input_calls.append(
            PromptCall(
                message=message,
                default=default,
                completer=completer,
                has_validator=validator is not None,
            )
        )

        if self.cancel_on_input:
            raise UserCancelledError()

        if self.input_responses:
            return self.input_responses.pop(0)

        if self.strict:
            raise AssertionError(
                f"FakeUI: No response queued for prompt_input('{message}')"
            )
        return default

    def prompt_path(
        self,
        message: str,
        default: str = "",
    ) -> str:
        self.path_calls.append(
            PromptCall(
                message=message,
                default=default,
            )
        )

        if self.cancel_on_path:
            raise UserCancelledError()

        if self.path_responses:
            return self.path_responses.pop(0)

        if self.strict:
            raise AssertionError(
                f"FakeUI: No response queued for prompt_path('{message}')"
            )
        return default

    def print_success(self, message: str) -> None:
        self.success_messages.append(message)

    def print_error(self, message: str) -> None:
        self.error_messages.append(message)

    def print_info(self, message: str) -> None:
        self.info_messages.append(message)

    def print_muted(self, message: str) -> None:
        self.muted_messages.append(message)

    def prompt_select_files(
        self,
        files: list[FileInfo],
        message: str,
        default_all: bool = False,
    ) -> list[str]:
        self.select_files_calls.append((list(files), message, default_all))

        if self.cancel_on_select_files:
            raise UserCancelledError()

        if self.select_files_responses:
            return self.select_files_responses.pop(0)

        if self.strict:
            raise AssertionError(
                f"FakeUI: No response queued for prompt_select_files('{message}')"
            )
        # Default: return all file paths if default_all, else empty
        if default_all:
            return [f.path for f in files]
        return []

    def prompt_confirm(self, message: str, default: bool = False) -> bool:
        self.confirm_calls.append((message, default))

        if self.cancel_on_confirm:
            raise UserCancelledError()

        if self.confirm_responses:
            return self.confirm_responses.pop(0)

        if self.strict:
            raise AssertionError(
                f"FakeUI: No response queued for prompt_confirm('{message}')"
            )
        return default

    def prompt_select_reviewers(
        self, potential_reviewers: list[str], include_skip_option: bool = True
    ) -> list[str]:
        self.select_reviewers_calls.append(
            (list(potential_reviewers), include_skip_option)
        )

        if self.cancel_on_select_reviewers:
            raise UserCancelledError()

        if self.select_reviewers_responses:
            return self.select_reviewers_responses.pop(0)

        if self.strict:
            raise AssertionError(
                "FakeUI: No response queued for prompt_select_reviewers()"
            )
        return []

    def prompt_input_multiline(
        self,
        message: str,
        default: str = "",
    ) -> str:
        self.input_multiline_calls.append(PromptCall(message=message, default=default))

        if self.cancel_on_input_multiline:
            raise UserCancelledError()

        if self.input_multiline_responses:
            return self.input_multiline_responses.pop(0)

        if self.strict:
            raise AssertionError(
                f"FakeUI: No response queued for prompt_input_multiline('{message}')"
            )
        return default

    def prompt_select_branch(
        self,
        branches: list[str],
        message: str,
        current_branch: str | None = None,
        exclude_protected: bool = False,
        enable_search: bool = True,
    ) -> str | None:
        self.select_branch_calls.append(
            (list(branches), message, current_branch, exclude_protected, enable_search)
        )

        if self.cancel_on_select_branch:
            raise UserCancelledError()

        if self.select_branch_responses:
            return self.select_branch_responses.pop(0)

        if self.strict:
            raise AssertionError(
                f"FakeUI: No response queued for prompt_select_branch('{message}')"
            )
        return None

    def display_branch_tree(
        self,
        root_branch: str,
        current_branch: str | None = None,
    ) -> None:
        self.display_tree_calls.append((root_branch, current_branch))


@dataclass
class FakeFilesystem:
    """In-memory fake for FilesystemPort."""

    existing_paths: set[str] = field(default_factory=set)
    directories: set[str] = field(default_factory=set)

    def path_exists(self, path: str) -> bool:
        return path in self.existing_paths or path in self.directories

    def is_directory(self, path: str) -> bool:
        return path in self.directories

    def resolve_path(self, path: str) -> str:
        # Simple resolution for testing - just normalize
        if path.startswith("~"):
            path = "/home/testuser" + path[1:]
        if not path.startswith("/"):
            path = "/cwd/" + path
        # Remove trailing slashes for consistency
        return path.rstrip("/")
