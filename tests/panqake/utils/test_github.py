"""Tests for github.py module."""

import subprocess
from unittest.mock import patch

import pytest

from panqake.utils.github import (
    branch_has_pr,
    check_github_cli_installed,
    create_pr,
    get_potential_reviewers,
    get_pr_checks_status,
    get_pr_url,
    merge_pr,
    run_gh_command,
    update_pr_base,
)


@pytest.fixture
def mock_subprocess_run():
    """Mock subprocess.run for gh commands."""
    with patch("subprocess.run") as mock_run:
        # Create a mock CompletedProcess object
        mock_process = subprocess.CompletedProcess(
            args=["gh"], returncode=0, stdout="", stderr=""
        )
        mock_run.return_value = mock_process
        yield mock_run


@pytest.fixture
def mock_which():
    """Mock shutil.which for gh CLI check."""
    with patch("shutil.which") as mock:
        yield mock


def test_run_gh_command_success(mock_subprocess_run):
    """Test successful GitHub CLI command execution."""
    mock_subprocess_run.return_value.stdout = "command output"
    result = run_gh_command(["pr", "list"])
    assert result == "command output"
    mock_subprocess_run.assert_called_once_with(
        ["gh", "pr", "list"],
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )


def test_run_gh_command_failure(mock_subprocess_run):
    """Test failed GitHub CLI command execution."""
    mock_subprocess_run.side_effect = subprocess.CalledProcessError(
        1, "gh", stderr="error"
    )
    result = run_gh_command(["pr", "list"])
    assert result is None


def test_check_github_cli_installed_true(mock_which):
    """Test GitHub CLI installation check when installed."""
    mock_which.return_value = "/usr/local/bin/gh"
    assert check_github_cli_installed() is True
    mock_which.assert_called_once_with("gh")


def test_check_github_cli_installed_false(mock_which):
    """Test GitHub CLI installation check when not installed."""
    mock_which.return_value = None
    assert check_github_cli_installed() is False


def test_branch_has_pr_true(mock_subprocess_run):
    """Test checking if branch has PR when it does."""
    mock_subprocess_run.return_value.stdout = "PR exists"
    assert branch_has_pr("feature") is True
    mock_subprocess_run.assert_called_once_with(
        ["gh", "pr", "view", "feature"],
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )


def test_branch_has_pr_false(mock_subprocess_run):
    """Test checking if branch has PR when it doesn't."""
    mock_subprocess_run.side_effect = subprocess.CalledProcessError(
        1, "gh", stderr="No PR found"
    )
    assert branch_has_pr("feature") is False


def test_create_pr_success(mock_subprocess_run):
    """Test successful PR creation."""
    mock_subprocess_run.return_value.stdout = (
        "PR created\nhttps://github.com/user/repo/pull/123"
    )
    success, url = create_pr(
        base="main", head="feature", title="Test PR", body="PR description"
    )
    assert success is True
    assert url == "https://github.com/user/repo/pull/123"
    mock_subprocess_run.assert_called_once_with(
        [
            "gh",
            "pr",
            "create",
            "--base",
            "main",
            "--head",
            "feature",
            "--title",
            "Test PR",
            "--body",
            "PR description",
        ],
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )


def test_create_pr_failure(mock_subprocess_run):
    """Test failed PR creation."""
    mock_subprocess_run.side_effect = subprocess.CalledProcessError(
        1, "gh", stderr="error"
    )
    success, url = create_pr(base="main", head="feature", title="Test PR")
    assert success is False
    assert url is None


def test_create_pr_with_reviewers(mock_subprocess_run):
    """Test successful PR creation with reviewers."""
    mock_subprocess_run.return_value.stdout = (
        "PR created\nhttps://github.com/user/repo/pull/123"
    )
    success, url = create_pr(
        base="main",
        head="feature",
        title="Test PR",
        body="PR description",
        reviewers=["reviewer1", "reviewer2"],
    )
    assert success is True
    assert url == "https://github.com/user/repo/pull/123"
    mock_subprocess_run.assert_called_once_with(
        [
            "gh",
            "pr",
            "create",
            "--base",
            "main",
            "--head",
            "feature",
            "--title",
            "Test PR",
            "--body",
            "PR description",
            "--reviewer",
            "reviewer1",
            "--reviewer",
            "reviewer2",
        ],
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )


def test_get_potential_reviewers_success(mock_subprocess_run):
    """Test successful retrieval of potential reviewers."""
    mock_subprocess_run.return_value.stdout = """{
        "owner": {"login": "owner_user"},
        "assignableUsers": [
            {"login": "assignable1"},
            {"login": "assignable2"},
            {"login": "owner_user"}
        ]
    }"""
    reviewers = get_potential_reviewers()
    assert reviewers == ["assignable1", "assignable2", "owner_user"]
    mock_subprocess_run.assert_called_once_with(
        ["gh", "repo", "view", "--json", "owner,assignableUsers"],
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )


def test_get_potential_reviewers_failure(mock_subprocess_run):
    """Test failed retrieval of potential reviewers."""
    mock_subprocess_run.side_effect = subprocess.CalledProcessError(
        1, "gh", stderr="error"
    )
    reviewers = get_potential_reviewers()
    assert reviewers == []


def test_get_potential_reviewers_invalid_json(mock_subprocess_run):
    """Test handling of invalid JSON response."""
    mock_subprocess_run.return_value.stdout = "invalid json"
    reviewers = get_potential_reviewers()
    assert reviewers == []


def test_get_pr_url(mock_subprocess_run):
    """Test getting PR URL."""
    mock_subprocess_run.return_value.stdout = (
        '{"url":"https://github.com/user/repo/pull/123"}'
    )
    assert get_pr_url("feature") == "https://github.com/user/repo/pull/123"
    mock_subprocess_run.assert_called_once_with(
        ["gh", "pr", "view", "feature", "--json", "url"],
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )


def test_update_pr_base_success(mock_subprocess_run):
    """Test successful PR base update."""
    mock_subprocess_run.return_value.stdout = "PR updated"
    assert update_pr_base("feature", "development") is True
    mock_subprocess_run.assert_called_once_with(
        ["gh", "pr", "edit", "feature", "--base", "development"],
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )


def test_update_pr_base_failure(mock_subprocess_run):
    """Test failed PR base update."""
    mock_subprocess_run.side_effect = subprocess.CalledProcessError(
        1, "gh", stderr="error"
    )
    assert update_pr_base("feature", "development") is False


def test_merge_pr_success(mock_subprocess_run):
    """Test successful PR merge."""
    mock_subprocess_run.return_value.stdout = "PR merged"
    assert merge_pr("feature", "squash") is True
    mock_subprocess_run.assert_called_once_with(
        ["gh", "pr", "merge", "feature", "--squash"],
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )


def test_merge_pr_failure(mock_subprocess_run):
    """Test failed PR merge."""
    mock_subprocess_run.side_effect = subprocess.CalledProcessError(
        1, "gh", stderr="error"
    )
    assert merge_pr("feature") is False


def test_merge_pr_different_method(mock_subprocess_run):
    """Test PR merge with different merge method."""
    mock_subprocess_run.return_value.stdout = "PR merged"
    assert merge_pr("feature", "rebase") is True
    mock_subprocess_run.assert_called_once_with(
        ["gh", "pr", "merge", "feature", "--rebase"],
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )


@pytest.mark.parametrize(
    "gh_output,expected_result",
    [
        # All checks passed
        (
            '{"statusCheckRollup": [{"conclusion": "SUCCESS"}, {"conclusion": "SUCCESS"}]}',
            True,
        ),
        # Some checks failed
        (
            '{"statusCheckRollup": [{"conclusion": "SUCCESS"}, {"conclusion": "FAILURE"}]}',
            False,
        ),
        # No checks
        (
            '{"statusCheckRollup": []}',
            True,
        ),
        # Invalid JSON
        (
            "Invalid JSON",
            False,
        ),
        # Empty result
        (
            None,
            False,
        ),
    ],
)
def test_get_pr_checks_status(gh_output, expected_result):
    """Test the get_pr_checks_status function."""
    with patch("panqake.utils.github.run_gh_command", return_value=gh_output):
        result = get_pr_checks_status("test-branch")
        assert result == expected_result
