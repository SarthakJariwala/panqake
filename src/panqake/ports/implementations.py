"""Real implementations of port protocols.

These classes wrap actual git commands, GitHub CLI, config, and filesystem operations.
"""

from pathlib import Path

from panqake.utils.types import BranchName

from .exceptions import (
    BranchNotFoundError,
    CommitError,
    GitOperationError,
    PRBaseUpdateError,
    PRCreationError,
    PRMergeError,
    PushError,
    RebaseConflictError,
    StagingError,
    UserCancelledError,
    WorktreeError,
)
from .results import FileInfo, MergeMethod


class RealGit:
    """Real implementation of GitPort using actual git commands."""

    def get_current_branch(self) -> BranchName | None:
        from panqake.utils.git import get_current_branch

        return get_current_branch()

    def list_all_branches(self) -> list[BranchName]:
        from panqake.utils.git import list_all_branches

        return list_all_branches()

    def branch_exists(self, branch: BranchName) -> bool:
        from panqake.utils.git import branch_exists

        return branch_exists(branch)

    def validate_branch(self, branch: BranchName) -> None:
        if not self.branch_exists(branch):
            raise BranchNotFoundError(f"Branch '{branch}' does not exist")

    def create_branch(self, branch_name: BranchName, base_branch: BranchName) -> None:
        from panqake.utils.git import run_git_command

        result = run_git_command(
            ["checkout", "-b", branch_name, base_branch], silent_fail=True
        )
        if result is None:
            raise GitOperationError(f"Failed to create branch '{branch_name}'")

    def add_worktree(
        self, branch_name: BranchName, path: str, base_branch: BranchName
    ) -> None:
        abs_path = str(Path(path).resolve())
        from panqake.utils.git import run_git_command

        result = run_git_command(
            ["worktree", "add", "-b", branch_name, abs_path, base_branch],
            silent_fail=True,
        )
        if result is None:
            raise WorktreeError(f"Failed to create worktree at '{abs_path}'")

    def get_staged_files(self) -> list[FileInfo]:
        from panqake.utils.git import get_staged_files

        raw_files = get_staged_files()
        return [
            FileInfo(
                path=f["path"],
                display=f["display"],
                original_path=f.get("original_path"),
            )
            for f in raw_files
        ]

    def get_unstaged_files(self) -> list[FileInfo]:
        from panqake.utils.git import get_unstaged_files

        raw_files = get_unstaged_files()
        return [
            FileInfo(
                path=f["path"],
                display=f["display"],
                original_path=f.get("original_path"),
            )
            for f in raw_files
        ]

    def branch_has_commits(
        self, branch: BranchName, parent_branch: BranchName | None
    ) -> bool:
        from panqake.utils.git import branch_has_commits

        return branch_has_commits(branch, parent_branch)

    def stage_files(self, files: list[FileInfo]) -> None:
        from panqake.utils.git import run_git_command

        for file_info in files:
            if file_info.original_path:
                result_old = run_git_command(
                    ["add", "--", file_info.original_path], silent_fail=True
                )
                result_new = run_git_command(
                    ["add", "--", file_info.path], silent_fail=True
                )
                if result_old is None or result_new is None:
                    raise StagingError(
                        f"Failed to stage rename/copy {file_info.original_path} → {file_info.path}"
                    )
            else:
                is_deleted = file_info.display.startswith("Deleted:")
                if is_deleted:
                    result = run_git_command(
                        ["add", "-u", "--", file_info.path], silent_fail=True
                    )
                else:
                    result = run_git_command(
                        ["add", "-A", "--", file_info.path], silent_fail=True
                    )
                if result is None:
                    raise StagingError(f"Failed to stage {file_info.path}")

    def commit(self, message: str) -> None:
        from panqake.utils.git import run_git_command

        result = run_git_command(["commit", "-m", message], silent_fail=True)
        if result is None:
            raise CommitError("Failed to create commit")

    def amend_commit(self, message: str | None = None) -> None:
        from panqake.utils.git import run_git_command

        if message:
            cmd = ["commit", "--amend", "-m", message]
        else:
            cmd = ["commit", "--amend", "--no-edit"]
        result = run_git_command(cmd, silent_fail=True)
        if result is None:
            raise CommitError("Failed to amend commit")

    def is_last_commit_amended(self) -> bool:
        from panqake.utils.git import is_last_commit_amended

        return is_last_commit_amended()

    def is_force_push_needed(self, branch: BranchName) -> bool:
        from panqake.utils.git import is_force_push_needed

        return is_force_push_needed(branch)

    def push_branch(self, branch: BranchName, force_with_lease: bool = False) -> None:
        from panqake.utils.git import push_branch_to_remote

        success = push_branch_to_remote(branch, force_with_lease)
        if not success:
            raise PushError(f"Failed to push branch '{branch}' to remote")

    def is_branch_pushed_to_remote(self, branch: BranchName) -> bool:
        from panqake.utils.git import is_branch_pushed_to_remote

        return is_branch_pushed_to_remote(branch)

    def get_last_commit_subject(self, branch: BranchName) -> str | None:
        from panqake.utils.git import run_git_command

        return run_git_command(["log", "-1", "--pretty=%s", branch], silent_fail=True)

    def checkout_branch(self, branch: BranchName) -> None:
        from panqake.utils.git import run_git_command

        result = run_git_command(["checkout", branch], silent_fail=True)
        if result is None:
            raise GitOperationError(f"Failed to checkout branch '{branch}'")

    def delete_local_branch(self, branch: BranchName, force: bool = True) -> None:
        from panqake.utils.git import run_git_command

        flag = "-D" if force else "-d"
        result = run_git_command(["branch", flag, branch], silent_fail=True)
        if result is None:
            raise GitOperationError(f"Failed to delete local branch '{branch}'")

    def delete_remote_branch(self, branch: BranchName) -> None:
        from panqake.utils.git import run_git_command

        result = run_git_command(
            ["push", "origin", "--delete", branch], silent_fail=True
        )
        if result is None:
            raise GitOperationError(f"Failed to delete remote branch '{branch}'")

    def remove_worktree(self, path: str, force: bool = False) -> None:
        from panqake.utils.git import run_git_command

        cmd = ["worktree", "remove", path]
        if force:
            cmd.append("--force")
        result = run_git_command(cmd, silent_fail=True)
        if result is None:
            raise WorktreeError(f"Failed to remove worktree at '{path}'")

    def rebase_onto(
        self, branch: BranchName, new_base: BranchName, abort_on_conflict: bool = True
    ) -> None:
        from panqake.utils.git import run_git_command

        self.checkout_branch(branch)
        result = run_git_command(["rebase", "--autostash", new_base], silent_fail=True)
        if result is None:
            if abort_on_conflict:
                run_git_command(["rebase", "--abort"], silent_fail=True)
            raise RebaseConflictError(f"Rebase conflict in branch '{branch}'")

    def fetch_from_remote(self) -> None:
        from panqake.utils.git import run_git_command

        result = run_git_command(["fetch", "origin"], silent_fail=True)
        if result is None:
            raise GitOperationError("Failed to fetch from remote")

    def pull_branch(self, branch: BranchName) -> None:
        from panqake.utils.git import run_git_command

        result = run_git_command(["pull", "origin", branch], silent_fail=True)
        if result is None:
            raise GitOperationError(f"Failed to pull branch '{branch}'")

    def get_worktree_path(self, branch: BranchName) -> str | None:
        from panqake.utils.git import get_worktree_path

        return get_worktree_path(branch)

    def get_potential_parents(self, branch: BranchName) -> list[BranchName]:
        from panqake.utils.git import get_potential_parents

        return get_potential_parents(branch)

    def rename_branch(self, old_name: BranchName, new_name: BranchName) -> None:
        from panqake.utils.git import run_git_command

        from .exceptions import BranchExistsError, BranchNotFoundError

        if not self.branch_exists(old_name):
            raise BranchNotFoundError(f"Branch '{old_name}' does not exist")
        if self.branch_exists(new_name):
            raise BranchExistsError(f"Branch '{new_name}' already exists")

        current = self.get_current_branch()
        if current != old_name:
            self.checkout_branch(old_name)

        result = run_git_command(["branch", "-m", new_name], silent_fail=True)
        if result is None:
            raise GitOperationError(
                f"Failed to rename branch '{old_name}' to '{new_name}'"
            )

    def get_merged_branches(self, into_branch: BranchName) -> list[BranchName]:
        from panqake.utils.git import run_git_command

        merged_result = run_git_command(
            ["branch", "--merged", into_branch], silent_fail=True
        )
        if not merged_result:
            return []

        merged_branches: list[BranchName] = []
        for branch in merged_result.splitlines():
            branch = branch.strip()
            if branch.startswith("* "):
                branch = branch[2:]
            if branch and branch != into_branch:
                merged_branches.append(branch)
        return merged_branches

    def is_branch_worktree(self, branch: BranchName) -> bool:
        from panqake.utils.git import is_branch_worktree

        return is_branch_worktree(branch)

    def has_unpushed_changes(self, branch: BranchName) -> bool:
        from panqake.utils.git import has_unpushed_changes

        return has_unpushed_changes(branch)

    def get_commit_hash(self, branch: BranchName) -> str | None:
        from panqake.utils.git import run_git_command

        result = run_git_command(["rev-parse", branch], silent_fail=True)
        return result.strip() if result else None

    def rebase_onto_in_worktree(
        self, branch: BranchName, new_base: BranchName, abort_on_conflict: bool = True
    ) -> None:
        from panqake.utils.git import run_git_command_for_branch_context

        result = run_git_command_for_branch_context(
            branch, ["rebase", "--autostash", new_base]
        )
        if result is None:
            if abort_on_conflict:
                run_git_command_for_branch_context(branch, ["rebase", "--abort"])
            raise RebaseConflictError(f"Rebase conflict in branch '{branch}'")


class RealGitHub:
    """Real implementation of GitHubPort using GitHub CLI."""

    def is_cli_installed(self) -> bool:
        from panqake.utils.github import check_github_cli_installed

        return check_github_cli_installed()

    def branch_has_pr(self, branch: BranchName) -> bool:
        from panqake.utils.github import branch_has_pr

        return branch_has_pr(branch)

    def get_pr_url(self, branch: BranchName) -> str | None:
        from panqake.utils.github import get_pr_url

        return get_pr_url(branch)

    def create_pr(
        self,
        base: BranchName,
        head: BranchName,
        title: str,
        body: str = "",
        reviewers: list[str] | None = None,
        draft: bool = False,
    ) -> str | None:
        from panqake.utils.github import create_pr

        success, url = create_pr(base, head, title, body, reviewers, draft)
        if not success:
            raise PRCreationError(f"Failed to create PR for branch '{head}'")
        return url

    def get_potential_reviewers(self) -> list[str]:
        from panqake.utils.github import get_potential_reviewers

        return get_potential_reviewers()

    def merge_pr(self, branch: BranchName, method: MergeMethod) -> None:
        from panqake.utils.github import merge_pr

        success = merge_pr(branch, method)
        if not success:
            raise PRMergeError(f"Failed to merge PR for branch '{branch}'")

    def get_pr_checks_status(self, branch: BranchName) -> tuple[bool, list[str]]:
        from panqake.utils.github import get_pr_checks_status

        return get_pr_checks_status(branch)

    def update_pr_base(self, branch: BranchName, new_base: BranchName) -> None:
        from panqake.utils.github import update_pr_base

        success = update_pr_base(branch, new_base)
        if not success:
            raise PRBaseUpdateError(
                f"Failed to update PR base for '{branch}' to '{new_base}'"
            )


class RealConfig:
    """Real implementation of ConfigPort using actual config functions."""

    def add_to_stack(
        self,
        branch_name: BranchName,
        parent_branch: BranchName,
        worktree_path: str | None = None,
    ) -> None:
        from panqake.utils.config import add_to_stack

        if worktree_path:
            add_to_stack(branch_name, parent_branch, worktree_path)
        else:
            add_to_stack(branch_name, parent_branch)

    def get_parent_branch(self, branch: BranchName) -> BranchName | None:
        from panqake.utils.config import get_parent_branch

        return get_parent_branch(branch)

    def get_child_branches(self, branch: BranchName) -> list[BranchName]:
        from panqake.utils.config import get_child_branches

        return get_child_branches(branch)

    def remove_from_stack(self, branch: BranchName) -> bool:
        from panqake.utils.config import remove_from_stack

        return remove_from_stack(branch)

    def get_worktree_path(self, branch: BranchName) -> str | None:
        from panqake.utils.config import get_worktree_path

        path = get_worktree_path(branch)
        return path if path else None

    def set_worktree_path(self, branch: BranchName, path: str) -> bool:
        from panqake.utils.config import set_worktree_path

        return set_worktree_path(branch, path)

    def rename_branch(self, old_name: BranchName, new_name: BranchName) -> bool:
        from panqake.utils.stack import Stacks

        stacks = Stacks()
        return stacks.rename_branch(old_name, new_name)

    def branch_exists(self, branch: BranchName) -> bool:
        from panqake.utils.stack import Stacks

        stacks = Stacks()
        return stacks.branch_exists(branch)


class RealUI:
    """Real implementation of UIPort using questionary and rich."""

    def prompt_input(
        self,
        message: str,
        default: str = "",
        completer: list[str] | None = None,
        validator: object | None = None,
    ) -> str:
        from panqake.utils.questionary_prompt import prompt_input

        try:
            kwargs: dict = {}
            if completer:
                kwargs["completer"] = completer
            if default:
                kwargs["default"] = default
            if validator:
                kwargs["validator"] = validator
            result = prompt_input(message, **kwargs)
            if result is None:
                raise UserCancelledError()
            return result
        except KeyboardInterrupt:
            raise UserCancelledError()

    def prompt_path(
        self,
        message: str,
        default: str = "",
    ) -> str:
        import questionary

        from panqake.utils.questionary_prompt import rich_prompt, style

        rich_prompt(f"{message} [default: {default}]: ", "prompt")
        try:
            result = questionary.path(
                "",
                default=default,
                only_directories=True,
                style=style,
            ).ask()
            if result is None:
                raise UserCancelledError()
            return result
        except KeyboardInterrupt:
            raise UserCancelledError()

    def print_success(self, message: str) -> None:
        from panqake.utils.questionary_prompt import print_formatted_text

        print_formatted_text(f"[success]{message}[/success]")

    def print_error(self, message: str) -> None:
        from panqake.utils.questionary_prompt import print_formatted_text

        print_formatted_text(f"[warning]{message}[/warning]")

    def print_info(self, message: str) -> None:
        from panqake.utils.questionary_prompt import print_formatted_text

        print_formatted_text(f"[info]{message}[/info]")

    def print_muted(self, message: str) -> None:
        from panqake.utils.questionary_prompt import print_formatted_text

        print_formatted_text(f"[muted]{message}[/muted]")

    def prompt_select_files(
        self,
        files: list[FileInfo],
        message: str,
        default_all: bool = False,
    ) -> list[str]:
        from panqake.utils.selection import select_files_for_staging

        try:
            file_dicts = [
                {
                    "path": f.path,
                    "display": f.display,
                    **({"original_path": f.original_path} if f.original_path else {}),
                }
                for f in files
            ]
            result = select_files_for_staging(
                file_dicts,
                message,
                default_all=default_all,
                search_threshold=10,
            )
            return result if result else []
        except KeyboardInterrupt:
            raise UserCancelledError()

    def prompt_confirm(self, message: str, default: bool = False) -> bool:
        from panqake.utils.questionary_prompt import prompt_confirm

        try:
            result = prompt_confirm(message)
            if result is None:
                raise UserCancelledError()
            return result
        except KeyboardInterrupt:
            raise UserCancelledError()

    def prompt_select_reviewers(
        self, potential_reviewers: list[str], include_skip_option: bool = True
    ) -> list[str]:
        from panqake.utils.selection import select_reviewers

        try:
            return select_reviewers(
                potential_reviewers,
                include_skip_option=include_skip_option,
            )
        except KeyboardInterrupt:
            raise UserCancelledError()

    def prompt_input_multiline(
        self,
        message: str,
        default: str = "",
    ) -> str:
        from panqake.utils.questionary_prompt import prompt_input

        try:
            result = prompt_input(message, default=default, multiline=True)
            if result is None:
                raise UserCancelledError()
            return result
        except KeyboardInterrupt:
            raise UserCancelledError()

    def prompt_select_branch(
        self,
        branches: list[str],
        message: str,
        current_branch: str | None = None,
        exclude_protected: bool = False,
        enable_search: bool = True,
    ) -> str | None:
        from typing import Any

        from panqake.utils.questionary_prompt import prompt_select

        try:
            filtered = [b for b in branches if b != current_branch]
            if exclude_protected:
                filtered = [b for b in filtered if b not in ("main", "master")]
            if not filtered:
                return None
            choices: list[str | dict[str, Any]] = [
                {"display": b, "value": b} for b in filtered
            ]
            result = prompt_select(message, choices, enable_search=enable_search)
            if result is None:
                raise UserCancelledError()
            return result
        except KeyboardInterrupt:
            raise UserCancelledError()

    def display_branch_tree(
        self,
        root_branch: str,
        current_branch: str | None = None,
    ) -> None:
        from panqake.utils.questionary_prompt import format_branch, print_formatted_text
        from panqake.utils.stack import Stacks

        print_formatted_text(
            f"[info]Branch stack (current: {format_branch(current_branch or '', current=True)})[/info]"
        )
        stacks = Stacks()
        tree_output = stacks.visualize_tree(
            root=root_branch, current_branch=current_branch or ""
        )
        print_formatted_text(tree_output)


class RealFilesystem:
    """Real implementation of FilesystemPort."""

    def path_exists(self, path: str) -> bool:
        return Path(path).exists()

    def is_directory(self, path: str) -> bool:
        expanded = Path(path).expanduser()
        return expanded.exists() and expanded.is_dir()

    def resolve_path(self, path: str) -> str:
        return str(Path(path).expanduser().resolve())
