"""Tests for git.py module."""

import subprocess
from unittest.mock import Mock, patch

import pytest

from panqake.utils.git import (
    branch_exists,
    get_current_branch,
    get_repo_id,
    get_staged_files,
    is_git_repo,
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
