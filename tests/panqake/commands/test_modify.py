"""Tests for modify.py command module."""

from unittest.mock import patch

import pytest

from panqake.commands.modify import (
    amend_existing_commit,
    create_new_commit,
    has_staged_changes,
    has_unstaged_changes,
    modify_commit,
    stage_selected_files,
)


@pytest.fixture
def mock_git_utils():
    """Mock all git utility functions."""
    with (
        patch("panqake.commands.modify.run_git_command") as mock_run,
        patch("panqake.commands.modify.get_current_branch") as mock_current,
        patch("panqake.commands.modify.get_staged_files") as mock_staged,
        patch("panqake.commands.modify.get_unstaged_files") as mock_unstaged,
        patch("panqake.commands.modify.branch_has_commits") as mock_has_commits,
    ):
        mock_current.return_value = "feature-branch"
        yield {
            "run": mock_run,
            "current": mock_current,
            "staged": mock_staged,
            "unstaged": mock_unstaged,
            "has_commits": mock_has_commits,
        }


@pytest.fixture
def mock_config_utils():
    """Mock config utility functions."""
    with patch("panqake.commands.modify.get_parent_branch") as mock_get_parent:
        mock_get_parent.return_value = "main"
        yield {"get_parent": mock_get_parent}


@pytest.fixture
def mock_prompt():
    """Mock questionary prompt functions."""
    with (
        patch("panqake.commands.modify.print_formatted_text") as mock_print,
        patch("panqake.commands.modify.select_files_for_staging") as mock_select_files,
        patch("panqake.commands.modify.prompt_input") as mock_input,
    ):
        yield {
            "print": mock_print,
            "select_files": mock_select_files,
            "input": mock_input,
        }


def test_has_staged_changes_true(mock_git_utils):
    """Test detection of staged changes when present."""
    # Setup
    mock_git_utils["run"].return_value = "modified.py\ndeleted.py"

    # Execute
    result = has_staged_changes()

    # Verify
    assert result is True
    mock_git_utils["run"].assert_called_once_with(["diff", "--staged", "--name-only"])


def test_has_staged_changes_false(mock_git_utils):
    """Test detection of staged changes when none present."""
    # Setup
    mock_git_utils["run"].return_value = ""

    # Execute
    result = has_staged_changes()

    # Verify
    assert result is False


def test_has_unstaged_changes_true(mock_git_utils):
    """Test detection of unstaged changes when present."""
    # Setup
    mock_git_utils["run"].return_value = "modified.py\ndeleted.py"

    # Execute
    result = has_unstaged_changes()

    # Verify
    assert result is True
    mock_git_utils["run"].assert_called_once_with(["diff", "--name-only"])


def test_has_unstaged_changes_false(mock_git_utils):
    """Test detection of unstaged changes when none present."""
    # Setup
    mock_git_utils["run"].return_value = ""

    # Execute
    result = has_unstaged_changes()

    # Verify
    assert result is False


def test_stage_selected_files_success(mock_git_utils, mock_prompt):
    """Test successful staging of selected files."""
    # Setup
    files = [
        {"path": "new.py"},
        {"path": "renamed.py", "original_path": "old.py"},
    ]
    mock_git_utils["run"].return_value = "success"

    # Execute
    result = stage_selected_files(files)

    # Verify
    assert result is True
    assert (
        mock_git_utils["run"].call_count == 3
    )  # One regular file + two paths for rename


def test_stage_selected_files_empty(mock_prompt):
    """Test staging with no files selected."""
    # Execute
    result = stage_selected_files([])

    # Verify
    assert result is False


def test_stage_selected_files_failure(mock_git_utils, mock_prompt):
    """Test staging failure."""
    # Setup
    files = [{"path": "new.py"}]
    mock_git_utils["run"].return_value = None

    # Execute
    result = stage_selected_files(files)

    # Verify
    assert result is False


def test_stage_selected_files_deleted(mock_git_utils, mock_prompt):
    """Test successful staging of deleted files."""
    # Setup
    files = [
        {"path": "deleted.py", "display": "Deleted: deleted.py"},
        {"path": "also_deleted.py", "display": "Deleted: also_deleted.py"},
    ]
    mock_git_utils["run"].return_value = "success"

    # Execute
    result = stage_selected_files(files)

    # Verify
    assert result is True
    assert mock_git_utils["run"].call_count == 2
    # Verify that git rm --cached was used for deleted files
    mock_git_utils["run"].assert_any_call(["rm", "--cached", "--", "deleted.py"])
    mock_git_utils["run"].assert_any_call(["rm", "--cached", "--", "also_deleted.py"])


def test_stage_selected_files_mixed(mock_git_utils, mock_prompt):
    """Test staging a mix of modified, new, and deleted files."""
    # Setup
    files = [
        {"path": "modified.py", "display": "Modified: modified.py"},
        {"path": "deleted.py", "display": "Deleted: deleted.py"},
        {"path": "new.py", "display": "Untracked: new.py"},
        {
            "path": "renamed.py",
            "original_path": "old.py",
            "display": "Renamed: old.py → renamed.py",
        },
    ]
    mock_git_utils["run"].return_value = "success"

    # Execute
    result = stage_selected_files(files)

    # Verify
    assert result is True
    # 3 regular files (using add -A) + 2 for the rename (old and new paths)
    assert mock_git_utils["run"].call_count == 5
    # Verify git add -A was used for regular files
    mock_git_utils["run"].assert_any_call(["add", "-A", "--", "modified.py"])
    mock_git_utils["run"].assert_any_call(["add", "-A", "--", "new.py"])
    # Verify git rm --cached was used for deleted files
    mock_git_utils["run"].assert_any_call(["rm", "--cached", "--", "deleted.py"])
    # Verify rename handling
    mock_git_utils["run"].assert_any_call(["add", "--", "old.py"])
    mock_git_utils["run"].assert_any_call(["add", "--", "renamed.py"])


def test_create_new_commit_success(mock_git_utils, mock_prompt):
    """Test successful creation of new commit."""
    # Setup
    message = "test commit"
    mock_git_utils["run"].return_value = "success"

    # Execute
    create_new_commit(message)

    # Verify
    mock_git_utils["run"].assert_called_once_with(["commit", "-m", message])


def test_create_new_commit_prompt(mock_git_utils, mock_prompt):
    """Test commit creation with prompted message."""
    # Setup
    mock_prompt["input"].return_value = "test commit"
    mock_git_utils["run"].return_value = "success"

    # Execute
    create_new_commit()

    # Verify
    mock_prompt["input"].assert_called_once()
    mock_git_utils["run"].assert_called_once_with(["commit", "-m", "test commit"])


def test_create_new_commit_empty_message(mock_prompt):
    """Test commit creation with empty message."""
    # Setup
    mock_prompt["input"].return_value = ""

    # Execute and verify
    with pytest.raises(SystemExit):
        create_new_commit()


def test_amend_existing_commit_success(mock_git_utils, mock_prompt):
    """Test successful commit amendment."""
    # Setup
    mock_git_utils["run"].return_value = "success"

    # Execute
    amend_existing_commit()

    # Verify
    mock_git_utils["run"].assert_called_once_with(["commit", "--amend", "--no-edit"])


def test_amend_existing_commit_with_message(mock_git_utils, mock_prompt):
    """Test commit amendment with new message."""
    # Setup
    message = "updated commit"
    mock_git_utils["run"].return_value = "success"

    # Execute
    amend_existing_commit(message)

    # Verify
    mock_git_utils["run"].assert_called_once_with(["commit", "--amend", "-m", message])


def test_modify_commit_no_changes(mock_git_utils, mock_prompt):
    """Test modify commit when no changes exist."""
    # Setup
    mock_git_utils["staged"].return_value = []
    mock_git_utils["unstaged"].return_value = []

    # Execute and verify
    with pytest.raises(SystemExit):
        modify_commit()


def test_modify_commit_amend_existing(mock_git_utils, mock_config_utils, mock_prompt):
    """Test modifying existing commit via amendment."""
    # Setup
    mock_git_utils["staged"].return_value = [{"display": "modified.py"}]
    mock_git_utils["unstaged"].return_value = []
    mock_git_utils["has_commits"].return_value = True
    mock_git_utils["run"].return_value = "success"

    # Execute
    modify_commit()

    # Verify amend was called
    mock_git_utils["run"].assert_called_with(["commit", "--amend", "--no-edit"])


def test_modify_commit_force_new(mock_git_utils, mock_config_utils, mock_prompt):
    """Test forcing new commit creation with --commit flag."""
    # Setup
    mock_git_utils["staged"].return_value = [{"display": "modified.py"}]
    mock_git_utils["unstaged"].return_value = []
    mock_git_utils["has_commits"].return_value = True
    mock_git_utils["run"].return_value = "success"
    # Mock the commit message prompt
    commit_message = "Forced new commit message"
    mock_prompt["input"].return_value = commit_message

    # Execute
    modify_commit(commit_flag=True)

    # Verify new commit was created with the prompted message
    mock_prompt["input"].assert_called_once()
    mock_git_utils["run"].assert_called_once_with(["commit", "-m", commit_message])


def test_modify_commit_stage_unstaged(mock_git_utils, mock_config_utils, mock_prompt):
    """Test modifying commit with staging unstaged changes."""
    # Setup
    mock_git_utils["staged"].return_value = []
    mock_git_utils["unstaged"].return_value = [
        {"path": "unstaged.py", "display": "unstaged.py"}
    ]
    mock_git_utils["has_commits"].return_value = True
    mock_git_utils["run"].return_value = "success"
    mock_prompt["select_files"].return_value = ["unstaged.py"]

    # Execute
    modify_commit()

    # Verify staging and commit
    assert mock_git_utils["run"].call_count >= 2  # At least one stage and one commit
