"""Tests for config.py module."""

import json
from unittest.mock import patch

import pytest

from panqake.utils.config import (
    add_to_stack,
    get_child_branches,
    get_parent_branch,
    init_panqake,
    remove_from_stack,
)


@pytest.fixture
def mock_repo_id():
    """Mock git.get_repo_id."""
    with patch("panqake.utils.config.get_repo_id") as mock:
        mock.return_value = "test-repo"
        yield mock


def test_init_panqake_creates_directory_and_file(tmp_path):
    """Test that init_panqake creates the .panqake directory and stacks.json file in tmp_path."""
    # Define paths within tmp_path
    panqake_dir = tmp_path / ".panqake"
    stack_file = panqake_dir / "stacks.json"

    # Patch the global variables used by the config functions
    with (
        patch("panqake.utils.config.PANQAKE_DIR", panqake_dir),
        patch("panqake.utils.config.STACK_FILE", stack_file),
    ):
        # Ensure directory doesn't exist initially
        assert not panqake_dir.exists()

        init_panqake()

        # Verify directory and file were created
        assert panqake_dir.exists()
        assert panqake_dir.is_dir()
        assert stack_file.exists()
        assert stack_file.is_file()

        # Verify file contains empty JSON object
        with open(stack_file) as f:
            content = json.load(f)
            assert content == {}


def test_get_parent_branch_existing(tmp_path, mock_repo_id):
    """Test getting parent branch when it exists."""
    # Define paths within tmp_path
    panqake_dir = tmp_path / ".panqake"
    stack_file = panqake_dir / "stacks.json"

    # Setup test data in the temp file
    panqake_dir.mkdir()
    test_data = {"test-repo": {"feature": {"parent": "main"}}}
    with open(stack_file, "w") as f:
        json.dump(test_data, f)

    # Patch the global STACK_FILE used by the function
    with patch("panqake.utils.config.STACK_FILE", stack_file):
        assert get_parent_branch("feature") == "main"


def test_get_parent_branch_nonexistent(tmp_path, mock_repo_id):
    """Test getting parent branch when branch doesn't exist."""
    panqake_dir = tmp_path / ".panqake"
    stack_file = panqake_dir / "stacks.json"
    panqake_dir.mkdir()
    # Setup empty stacks file
    with open(stack_file, "w") as f:
        json.dump({}, f)

    with patch("panqake.utils.config.STACK_FILE", stack_file):
        assert get_parent_branch("nonexistent") == ""


def test_get_parent_branch_invalid_json(tmp_path, mock_repo_id):
    """Test getting parent branch with invalid JSON."""
    panqake_dir = tmp_path / ".panqake"
    stack_file = panqake_dir / "stacks.json"
    panqake_dir.mkdir()
    # Write invalid JSON
    with open(stack_file, "w") as f:
        f.write("invalid json")

    with patch("panqake.utils.config.STACK_FILE", stack_file):
        # Should return default and not raise error
        assert get_parent_branch("feature") == ""


def test_get_child_branches_multiple(tmp_path, mock_repo_id):
    """Test getting multiple child branches."""
    panqake_dir = tmp_path / ".panqake"
    stack_file = panqake_dir / "stacks.json"
    panqake_dir.mkdir()
    # Setup test data
    test_data = {
        "test-repo": {
            "feature1": {"parent": "main"},
            "feature2": {"parent": "main"},
            "sub-feature": {"parent": "feature1"},
        }
    }
    with open(stack_file, "w") as f:
        json.dump(test_data, f)

    with patch("panqake.utils.config.STACK_FILE", stack_file):
        children = get_child_branches("main")
        assert len(children) == 2
        assert set(children) == {"feature1", "feature2"}


def test_get_child_branches_no_children(tmp_path, mock_repo_id):
    """Test getting child branches when none exist."""
    panqake_dir = tmp_path / ".panqake"
    stack_file = panqake_dir / "stacks.json"
    panqake_dir.mkdir()
    # Setup test data with no children
    test_data = {"test-repo": {"feature": {"parent": "main"}}}
    with open(stack_file, "w") as f:
        json.dump(test_data, f)

    with patch("panqake.utils.config.STACK_FILE", stack_file):
        assert get_child_branches("feature") == []


def test_add_to_stack_new_branch(tmp_path, mock_repo_id):
    """Test adding a new branch to the stack."""
    panqake_dir = tmp_path / ".panqake"
    stack_file = panqake_dir / "stacks.json"
    panqake_dir.mkdir()
    # Setup empty stacks file
    with open(stack_file, "w") as f:
        json.dump({}, f)

    with patch("panqake.utils.config.STACK_FILE", stack_file):
        add_to_stack("feature", "main")

    # Verify branch was added by reading the temp file directly
    with open(stack_file) as f:
        stacks = json.load(f)
        assert "test-repo" in stacks
        assert "feature" in stacks["test-repo"]
        assert stacks["test-repo"]["feature"]["parent"] == "main"


def test_add_to_stack_existing_repo(tmp_path, mock_repo_id):
    """Test adding a branch to existing repo in stack."""
    panqake_dir = tmp_path / ".panqake"
    stack_file = panqake_dir / "stacks.json"
    panqake_dir.mkdir()
    # Setup existing repo
    test_data = {"test-repo": {"existing": {"parent": "main"}}}
    with open(stack_file, "w") as f:
        json.dump(test_data, f)

    with patch("panqake.utils.config.STACK_FILE", stack_file):
        add_to_stack("feature", "main")

    # Verify branch was added while keeping existing data
    with open(stack_file) as f:
        stacks = json.load(f)
        assert "existing" in stacks["test-repo"]
        assert "feature" in stacks["test-repo"]
        assert stacks["test-repo"]["feature"]["parent"] == "main"


def test_remove_from_stack_existing(tmp_path, mock_repo_id):
    """Test removing an existing branch from stack."""
    panqake_dir = tmp_path / ".panqake"
    stack_file = panqake_dir / "stacks.json"
    panqake_dir.mkdir()
    # Setup test data
    test_data = {
        "test-repo": {"feature": {"parent": "main"}, "other": {"parent": "main"}}
    }
    with open(stack_file, "w") as f:
        json.dump(test_data, f)

    with patch("panqake.utils.config.STACK_FILE", stack_file):
        remove_from_stack("feature")

    # Verify branch was removed
    with open(stack_file) as f:
        stacks = json.load(f)
        assert "feature" not in stacks["test-repo"]
        assert "other" in stacks["test-repo"]  # Other branch should remain


def test_remove_from_stack_nonexistent(tmp_path, mock_repo_id):
    """Test removing a nonexistent branch from stack."""
    panqake_dir = tmp_path / ".panqake"
    stack_file = panqake_dir / "stacks.json"
    panqake_dir.mkdir()
    # Setup test data
    test_data = {"test-repo": {"feature": {"parent": "main"}}}
    with open(stack_file, "w") as f:
        json.dump(test_data, f)

    with patch("panqake.utils.config.STACK_FILE", stack_file):
        remove_from_stack("nonexistent")

    # Verify original data unchanged
    with open(stack_file) as f:
        stacks = json.load(f)
        assert stacks == test_data


def test_remove_from_stack_invalid_json(tmp_path, mock_repo_id):
    """Test removing branch with invalid JSON."""
    panqake_dir = tmp_path / ".panqake"
    stack_file = panqake_dir / "stacks.json"
    panqake_dir.mkdir()
    # Write invalid JSON
    with open(stack_file, "w") as f:
        f.write("invalid json")

    # Should not raise exception
    with patch("panqake.utils.config.STACK_FILE", stack_file):
        remove_from_stack("feature")
