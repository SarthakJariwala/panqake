"""Tests for git.py module."""

import subprocess
from unittest.mock import Mock, patch

import pytest

from panqake.utils.git import (
    branch_exists,
    get_current_branch,
    get_repo_id,
    get_staged_files,
    has_unpushed_changes,
    is_force_push_needed,
    is_git_repo,
    is_last_commit_amended,
    list_all_branches,
    run_git_command,
    validate_branch,
)


@pytest.fixture
def mock_subprocess_run():
    """Mock subprocess.run for git commands."""
    with patch("subprocess.run") as mock_run:
        # Create a mock CompletedProcess object
        mock_process = Mock()
        mock_process.stdout = ""
        mock_process.stderr = ""
        mock_run.return_value = mock_process
        yield mock_run


def test_run_git_command_success(mock_subprocess_run):
    """Test successful git command execution."""
    mock_subprocess_run.return_value.stdout = "command output"
    result = run_git_command(["status"])
    assert result == "command output"
    mock_subprocess_run.assert_called_once_with(
        ["git", "status"],
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )


def test_run_git_command_failure(mock_subprocess_run):
    """Test failed git command execution."""
    mock_subprocess_run.side_effect = subprocess.CalledProcessError(
        1, "git", stderr="error"
    )
    result = run_git_command(["status"])
    assert result is None


def test_is_git_repo_true(mock_subprocess_run):
    """Test is_git_repo when in a git repository."""
    mock_subprocess_run.return_value.stdout = "true"
    assert is_git_repo() is True
    mock_subprocess_run.assert_called_once_with(
        ["git", "rev-parse", "--is-inside-work-tree"],
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )


def test_is_git_repo_false(mock_subprocess_run):
    """Test is_git_repo when not in a git repository."""
    mock_subprocess_run.side_effect = subprocess.CalledProcessError(
        128, "git", stderr="not a git repo"
    )
    assert is_git_repo() is False


def test_get_repo_id_success(mock_subprocess_run):
    """Test getting repository ID successfully."""
    mock_subprocess_run.return_value.stdout = "/path/to/repo"
    assert get_repo_id() == "repo"


def test_get_repo_id_failure(mock_subprocess_run):
    """Test getting repository ID when command fails."""
    mock_subprocess_run.side_effect = subprocess.CalledProcessError(1, "git")
    assert get_repo_id() is None


def test_get_current_branch_success(mock_subprocess_run):
    """Test getting current branch name successfully."""
    mock_subprocess_run.return_value.stdout = "main"
    assert get_current_branch() == "main"


def test_get_current_branch_failure(mock_subprocess_run):
    """Test getting current branch when command fails."""
    mock_subprocess_run.side_effect = subprocess.CalledProcessError(1, "git")
    assert get_current_branch() is None


def test_list_all_branches_success(mock_subprocess_run):
    """Test listing all branches successfully."""
    mock_subprocess_run.return_value.stdout = "main\nfeature\ndevelopment"
    assert list_all_branches() == ["main", "feature", "development"]


def test_list_all_branches_empty(mock_subprocess_run):
    """Test listing branches when none exist."""
    mock_subprocess_run.return_value.stdout = ""
    assert list_all_branches() == []


def test_branch_exists_true(mock_subprocess_run):
    """Test checking if an existing branch exists."""
    mock_subprocess_run.return_value.stdout = "ref found"
    assert branch_exists("main") is True


def test_branch_exists_false(mock_subprocess_run):
    """Test checking if a non-existent branch exists."""
    mock_subprocess_run.side_effect = subprocess.CalledProcessError(1, "git")
    assert branch_exists("nonexistent") is False


def test_validate_branch_existing(mock_subprocess_run):
    """Test validating an existing branch."""
    mock_subprocess_run.return_value.stdout = "ref found"
    assert validate_branch("main") == "main"


def test_get_staged_files_success(mock_subprocess_run):
    """Test getting staged files successfully."""
    mock_subprocess_run.return_value.stdout = "M\tfile1.txt\nA\tfile2.txt\nD\tfile3.txt"
    files = get_staged_files()
    assert len(files) == 3
    assert files[0]["display"] == "Modified: file1.txt"
    assert files[1]["display"] == "Added: file2.txt"
    assert files[2]["display"] == "Deleted: file3.txt"


def test_get_staged_files_renamed(mock_subprocess_run):
    """Test getting staged files with renamed files."""
    mock_subprocess_run.return_value.stdout = "R100\told.txt\tnew.txt"
    files = get_staged_files()
    assert len(files) == 1
    assert files[0]["display"] == "Renamed: old.txt → new.txt"
    assert files[0]["original_path"] == "old.txt"
    assert files[0]["path"] == "new.txt"


def test_is_last_commit_amended_true(mock_subprocess_run):
    """Test detecting an amended commit."""
    mock_subprocess_run.return_value.stdout = (
        "abc1234 HEAD@{0}: commit (amend): Fix bug"
    )
    assert is_last_commit_amended() is True


def test_is_last_commit_amended_false(mock_subprocess_run):
    """Test detecting a regular commit."""
    mock_subprocess_run.return_value.stdout = "abc1234 HEAD@{0}: commit: Fix bug"
    assert is_last_commit_amended() is False


def test_is_last_commit_amended_no_reflog(mock_subprocess_run):
    """Test when git reflog command fails."""
    mock_subprocess_run.side_effect = subprocess.CalledProcessError(1, "git")
    assert is_last_commit_amended() is False


@patch("panqake.utils.git.is_branch_pushed_to_remote")
def test_is_force_push_needed_branch_not_on_remote(mock_is_pushed, mock_subprocess_run):
    """Test is_force_push_needed when branch is not on remote."""
    mock_is_pushed.return_value = False
    assert is_force_push_needed("feature") is False
    # Ensure we don't try to do a dry-run push
    mock_subprocess_run.assert_not_called()


@patch("panqake.utils.git.is_branch_pushed_to_remote")
def test_is_force_push_needed_true(mock_is_pushed, mock_subprocess_run):
    """Test is_force_push_needed when force push is needed."""
    mock_is_pushed.return_value = True
    mock_subprocess_run.return_value.stdout = (
        "To github.com:user/repo.git\n"
        "! [rejected]        feature -> feature (non-fast-forward)\n"
        "error: failed to push some refs"
    )
    assert is_force_push_needed("feature") is True
    # Check that we called push with the right arguments
    mock_subprocess_run.assert_called_once_with(
        ["git", "push", "--dry-run", "--porcelain", "origin", "feature"],
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )


@patch("panqake.utils.git.is_branch_pushed_to_remote")
def test_is_force_push_needed_false(mock_is_pushed, mock_subprocess_run):
    """Test is_force_push_needed when force push is not needed."""
    mock_is_pushed.return_value = True
    mock_subprocess_run.return_value.stdout = (
        "To github.com:user/repo.git\n= [up to date]      feature -> feature"
    )
    assert is_force_push_needed("feature") is False


@patch("panqake.utils.git.is_branch_pushed_to_remote")
def test_has_unpushed_changes_branch_not_on_remote(mock_is_pushed, mock_subprocess_run):
    """Test has_unpushed_changes when branch is not on remote."""
    mock_is_pushed.return_value = False
    assert has_unpushed_changes("feature") is True
    # Ensure we don't try to get rev-list
    mock_subprocess_run.assert_not_called()


@patch("panqake.utils.git.is_branch_pushed_to_remote")
def test_has_unpushed_changes_with_changes(mock_is_pushed, mock_subprocess_run):
    """Test has_unpushed_changes when local is ahead of remote."""
    mock_is_pushed.return_value = True
    mock_subprocess_run.return_value.stdout = "0 3"  # 0 behind, 3 ahead
    assert has_unpushed_changes("feature") is True
    mock_subprocess_run.assert_called_once_with(
        ["git", "rev-list", "--left-right", "--count", "origin/feature...feature"],
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )


@patch("panqake.utils.git.is_branch_pushed_to_remote")
def test_has_unpushed_changes_no_changes(mock_is_pushed, mock_subprocess_run):
    """Test has_unpushed_changes when local and remote are in sync."""
    mock_is_pushed.return_value = True
    mock_subprocess_run.return_value.stdout = "0 0"  # 0 behind, 0 ahead
    assert has_unpushed_changes("feature") is False


@patch("panqake.utils.git.is_branch_pushed_to_remote")
def test_has_unpushed_changes_behind_only(mock_is_pushed, mock_subprocess_run):
    """Test has_unpushed_changes when local is behind remote but not ahead."""
    mock_is_pushed.return_value = True
    mock_subprocess_run.return_value.stdout = "2 0"  # 2 behind, 0 ahead
    assert has_unpushed_changes("feature") is False
