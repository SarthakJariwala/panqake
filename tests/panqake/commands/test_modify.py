"""Tests for modify command using the ports/fakes testing architecture."""

import pytest

from panqake.commands.modify import modify_commit_core
from panqake.ports import (
    CommitError,
    FileInfo,
    NoChangesError,
    UserCancelledError,
)
from panqake.testing.fakes import FakeConfig, FakeGit, FakeUI


class TestModifyCommitCore:
    """Test modify_commit_core with fakes."""

    def test_amends_when_branch_has_commits(self):
        """When branch has commits, should amend by default."""
        git = FakeGit(
            current_branch="feature-x",
            staged_files=[FileInfo("file.py", "Modified: file.py")],
            branch_commits={"feature-x": True},
        )
        config = FakeConfig(stack={"feature-x": {"parent": "main"}})
        ui = FakeUI(strict=False)

        result = modify_commit_core(git=git, config=config, ui=ui)

        assert result.amended is True
        assert result.branch_name == "feature-x"
        assert len(git.amend_calls) == 1
        assert len(git.commits) == 0

    def test_creates_new_commit_when_no_commits_on_branch(self):
        """When branch has no commits, should create new commit."""
        git = FakeGit(
            current_branch="feature-x",
            staged_files=[FileInfo("file.py", "Modified: file.py")],
            branch_commits={"feature-x": False},
        )
        config = FakeConfig(stack={"feature-x": {"parent": "main"}})
        ui = FakeUI(input_responses=["Initial commit"], strict=False)

        result = modify_commit_core(git=git, config=config, ui=ui)

        assert result.amended is False
        assert result.message == "Initial commit"
        assert len(git.commits) == 1
        assert git.commits[0] == "Initial commit"
        assert len(git.amend_calls) == 0

    def test_force_new_commit_with_commit_flag(self):
        """--commit flag should force new commit even if branch has commits."""
        git = FakeGit(
            current_branch="feature-x",
            staged_files=[FileInfo("file.py", "Modified: file.py")],
            branch_commits={"feature-x": True},
        )
        config = FakeConfig(stack={"feature-x": {"parent": "main"}})
        ui = FakeUI(input_responses=["Forced new commit"], strict=False)

        result = modify_commit_core(git=git, config=config, ui=ui, commit_flag=True)

        assert result.amended is False
        assert result.message == "Forced new commit"
        assert len(git.commits) == 1
        assert len(git.amend_calls) == 0

    def test_no_amend_flag_creates_new_commit(self):
        """--no-amend flag should create new commit."""
        git = FakeGit(
            current_branch="feature-x",
            staged_files=[FileInfo("file.py", "Modified: file.py")],
            branch_commits={"feature-x": True},
        )
        config = FakeConfig(stack={"feature-x": {"parent": "main"}})
        ui = FakeUI(input_responses=["New commit"], strict=False)

        result = modify_commit_core(git=git, config=config, ui=ui, no_amend=True)

        assert result.amended is False
        assert len(git.commits) == 1

    def test_explicit_message_used_for_new_commit(self):
        """Explicit message should be used without prompting."""
        git = FakeGit(
            current_branch="feature-x",
            staged_files=[FileInfo("file.py", "Modified: file.py")],
            branch_commits={"feature-x": False},
        )
        config = FakeConfig(stack={"feature-x": {"parent": "main"}})
        ui = FakeUI(strict=False)

        result = modify_commit_core(
            git=git, config=config, ui=ui, message="Explicit message"
        )

        assert result.message == "Explicit message"
        assert git.commits[0] == "Explicit message"
        assert len(ui.input_calls) == 0

    def test_explicit_message_used_for_amend(self):
        """Explicit message should be passed to amend."""
        git = FakeGit(
            current_branch="feature-x",
            staged_files=[FileInfo("file.py", "Modified: file.py")],
            branch_commits={"feature-x": True},
        )
        config = FakeConfig(stack={"feature-x": {"parent": "main"}})
        ui = FakeUI(strict=False)

        result = modify_commit_core(
            git=git, config=config, ui=ui, message="New amend message"
        )

        assert result.amended is True
        assert result.message == "New amend message"
        assert git.amend_calls[0] == "New amend message"

    def test_stages_selected_unstaged_files(self):
        """Should stage files selected by user."""
        unstaged = [
            FileInfo("a.py", "Modified: a.py"),
            FileInfo("b.py", "Modified: b.py"),
            FileInfo("c.py", "Untracked: c.py"),
        ]
        git = FakeGit(
            current_branch="feature-x",
            unstaged_files=unstaged,
            branch_commits={"feature-x": True},
        )
        config = FakeConfig(stack={"feature-x": {"parent": "main"}})
        ui = FakeUI(select_files_responses=[["a.py", "c.py"]], strict=False)

        result = modify_commit_core(git=git, config=config, ui=ui)

        assert result.files_staged == ["a.py", "c.py"]
        assert len(git.staged_file_calls) == 1
        staged_paths = [f.path for f in git.staged_file_calls[0]]
        assert "a.py" in staged_paths
        assert "c.py" in staged_paths
        assert "b.py" not in staged_paths

    def test_no_changes_error_when_nothing_to_commit(self):
        """Should raise NoChangesError when no staged or unstaged changes."""
        git = FakeGit(current_branch="feature-x")
        config = FakeConfig()
        ui = FakeUI(strict=False)

        with pytest.raises(NoChangesError) as exc_info:
            modify_commit_core(git=git, config=config, ui=ui)

        assert "No changes" in exc_info.value.message

    def test_no_changes_error_when_nothing_staged(self):
        """Should raise NoChangesError when user doesn't stage anything."""
        unstaged = [FileInfo("a.py", "Modified: a.py")]
        git = FakeGit(
            current_branch="feature-x",
            unstaged_files=unstaged,
        )
        config = FakeConfig()
        ui = FakeUI(select_files_responses=[[]], strict=False)

        with pytest.raises(NoChangesError) as exc_info:
            modify_commit_core(git=git, config=config, ui=ui)

        assert "No changes staged" in exc_info.value.message

    def test_commit_error_on_empty_message(self):
        """Should raise CommitError when commit message is empty."""
        git = FakeGit(
            current_branch="feature-x",
            staged_files=[FileInfo("file.py", "Modified: file.py")],
            branch_commits={"feature-x": False},
        )
        config = FakeConfig()
        ui = FakeUI(input_responses=[""], strict=False)

        with pytest.raises(CommitError) as exc_info:
            modify_commit_core(git=git, config=config, ui=ui)

        assert "empty" in exc_info.value.message.lower()

    def test_user_cancelled_on_file_selection(self):
        """Should raise UserCancelledError when user cancels file selection."""
        unstaged = [FileInfo("a.py", "Modified: a.py")]
        git = FakeGit(
            current_branch="feature-x",
            unstaged_files=unstaged,
        )
        config = FakeConfig()
        ui = FakeUI(cancel_on_select_files=True)

        with pytest.raises(UserCancelledError):
            modify_commit_core(git=git, config=config, ui=ui)

        assert len(git.commits) == 0
        assert len(git.amend_calls) == 0

    def test_user_cancelled_on_commit_message_prompt(self):
        """Should raise UserCancelledError when user cancels message prompt."""
        git = FakeGit(
            current_branch="feature-x",
            staged_files=[FileInfo("file.py", "Modified: file.py")],
            branch_commits={"feature-x": False},
        )
        config = FakeConfig()
        ui = FakeUI(cancel_on_input=True)

        with pytest.raises(UserCancelledError):
            modify_commit_core(git=git, config=config, ui=ui)

    def test_handles_renamed_files(self):
        """Should properly stage renamed files."""
        unstaged = [
            FileInfo("new.py", "Renamed: old.py → new.py", original_path="old.py"),
        ]
        git = FakeGit(
            current_branch="feature-x",
            unstaged_files=unstaged,
            branch_commits={"feature-x": True},
        )
        config = FakeConfig(stack={"feature-x": {"parent": "main"}})
        ui = FakeUI(select_files_responses=[["new.py"]], strict=False)

        result = modify_commit_core(git=git, config=config, ui=ui)

        assert result.files_staged == ["new.py"]
        staged_files = git.staged_file_calls[0]
        assert staged_files[0].original_path == "old.py"

    def test_handles_deleted_files(self):
        """Should properly stage deleted files."""
        unstaged = [
            FileInfo("deleted.py", "Deleted: deleted.py"),
        ]
        git = FakeGit(
            current_branch="feature-x",
            unstaged_files=unstaged,
            branch_commits={"feature-x": True},
        )
        config = FakeConfig(stack={"feature-x": {"parent": "main"}})
        ui = FakeUI(select_files_responses=[["deleted.py"]], strict=False)

        result = modify_commit_core(git=git, config=config, ui=ui)

        assert "deleted.py" in result.files_staged

    def test_prints_info_messages(self):
        """Should print appropriate info messages."""
        git = FakeGit(
            current_branch="feature-x",
            staged_files=[FileInfo("file.py", "Modified: file.py")],
            branch_commits={"feature-x": True},
        )
        config = FakeConfig(stack={"feature-x": {"parent": "main"}})
        ui = FakeUI(strict=False)

        modify_commit_core(git=git, config=config, ui=ui)

        assert any("feature-x" in msg for msg in ui.info_messages)
        assert any("staged" in msg.lower() for msg in ui.info_messages)


class TestModifyCommitScenarios:
    """Parametrized tests for various modify scenarios."""

    @pytest.mark.parametrize(
        "has_commits,commit_flag,no_amend,expected_amend",
        [
            (True, False, False, True),
            (True, True, False, False),
            (True, False, True, False),
            (False, False, False, False),
            (False, True, False, False),
        ],
    )
    def test_amend_decision_logic(
        self, has_commits, commit_flag, no_amend, expected_amend
    ):
        """Test the decision logic for amend vs new commit."""
        git = FakeGit(
            current_branch="feature-x",
            staged_files=[FileInfo("file.py", "Modified: file.py")],
            branch_commits={"feature-x": has_commits},
        )
        config = FakeConfig(stack={"feature-x": {"parent": "main"}})
        ui = FakeUI(input_responses=["test message"], strict=False)

        result = modify_commit_core(
            git=git, config=config, ui=ui, commit_flag=commit_flag, no_amend=no_amend
        )

        assert result.amended == expected_amend
