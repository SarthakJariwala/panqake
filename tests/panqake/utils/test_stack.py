"""Tests for the stack module."""

import json
import os
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

from panqake.utils.stack import Branch, Stacks, STACK_FILE


def test_branch_init():
    """Test Branch initialization."""
    branch = Branch("feature", "main")
    assert branch.name == "feature"
    assert branch.parent == "main"


def test_branch_to_dict():
    """Test Branch serialization to dict."""
    branch = Branch("feature", "main")
    data = branch.to_dict()
    assert data == {"parent": "main"}


def test_branch_from_dict():
    """Test Branch deserialization from dict."""
    branch = Branch.from_dict("feature", {"parent": "main"})
    assert branch.name == "feature"
    assert branch.parent == "main"


@pytest.fixture
def mock_repo_id():
    """Fixture to mock the get_repo_id function."""
    with patch("panqake.utils.stack.get_repo_id") as mock:
        mock.return_value = "test-repo"
        yield mock


@pytest.fixture
def temp_stack_file(tmp_path):
    """Fixture to create a temporary stack file."""
    panqake_dir = tmp_path / ".panqake"
    stack_file = panqake_dir / "stacks.json"
    panqake_dir.mkdir()
    
    test_data = {
        "test-repo": {
            "main": {"parent": ""},
            "feature": {"parent": "main"},
            "child1": {"parent": "feature"},
            "child2": {"parent": "feature"},
            "sibling": {"parent": "main"}
        }
    }
    
    with open(stack_file, "w") as f:
        json.dump(test_data, f)
    
    with patch("panqake.utils.stack.STACK_FILE", stack_file):
        with patch("panqake.utils.stack.PANQAKE_DIR", panqake_dir):
            yield stack_file


def test_stacks_load(temp_stack_file, mock_repo_id):
    """Test loading stacks from file."""
    stacks = Stacks()
    assert stacks.load() is True
    
    # Verify data was loaded correctly
    assert stacks.get_parent("feature") == "main"
    assert stacks.get_parent("child1") == "feature"
    assert sorted(stacks.get_children("feature")) == ["child1", "child2"]


def test_stacks_save(temp_stack_file, mock_repo_id):
    """Test saving stacks to file."""
    stacks = Stacks()
    stacks.load()
    
    # Add a new branch
    stacks.add_branch("new-branch", "main")
    
    # Load stacks again to verify data was saved
    new_stacks = Stacks()
    new_stacks.load()
    assert "new-branch" in new_stacks.get_all_branches()
    assert new_stacks.get_parent("new-branch") == "main"


def test_stacks_get_parent(temp_stack_file, mock_repo_id):
    """Test getting parent branch."""
    stacks = Stacks()
    assert stacks.get_parent("feature") == "main"
    assert stacks.get_parent("child1") == "feature"
    assert stacks.get_parent("main") == ""
    assert stacks.get_parent("nonexistent") == ""


def test_stacks_get_children(temp_stack_file, mock_repo_id):
    """Test getting child branches."""
    stacks = Stacks()
    assert sorted(stacks.get_children("main")) == ["feature", "sibling"]
    assert sorted(stacks.get_children("feature")) == ["child1", "child2"]
    assert stacks.get_children("child1") == []
    assert stacks.get_children("nonexistent") == []


def test_stacks_add_branch(temp_stack_file, mock_repo_id):
    """Test adding a branch to the stack."""
    stacks = Stacks()
    
    # Add a new branch
    assert stacks.add_branch("new-feature", "main") is True
    assert stacks.get_parent("new-feature") == "main"
    assert "new-feature" in stacks.get_children("main")


def test_stacks_remove_branch(temp_stack_file, mock_repo_id):
    """Test removing a branch from the stack."""
    stacks = Stacks()
    
    # Remove a branch with children
    assert stacks.remove_branch("feature") is True
    
    # Verify children were updated to point to the parent
    assert stacks.get_parent("child1") == "main"
    assert stacks.get_parent("child2") == "main"
    assert "feature" not in stacks.get_all_branches()


def test_stacks_remove_nonexistent_branch(temp_stack_file, mock_repo_id):
    """Test removing a nonexistent branch."""
    stacks = Stacks()
    assert stacks.remove_branch("nonexistent") is False


def test_stacks_get_branch_lineage(temp_stack_file, mock_repo_id):
    """Test getting the branch lineage."""
    stacks = Stacks()
    assert stacks.get_branch_lineage("child1") == ["child1", "feature", "main"]
    assert stacks.get_branch_lineage("main") == ["main"]
    assert stacks.get_branch_lineage("nonexistent") == []


def test_stacks_get_all_descendants(temp_stack_file, mock_repo_id):
    """Test getting all descendants of a branch."""
    stacks = Stacks()
    assert sorted(stacks.get_all_descendants("main")) == ["child1", "child2", "feature", "sibling"]
    assert sorted(stacks.get_all_descendants("feature")) == ["child1", "child2"]
    assert stacks.get_all_descendants("child1") == []
    assert stacks.get_all_descendants("nonexistent") == []


def test_stacks_change_parent(temp_stack_file, mock_repo_id):
    """Test changing the parent of a branch."""
    stacks = Stacks()
    
    # Change parent
    assert stacks.change_parent("child1", "sibling") is True
    assert stacks.get_parent("child1") == "sibling"
    
    # Verify lineage updated
    assert stacks.get_branch_lineage("child1") == ["child1", "sibling", "main"]


def test_stacks_change_parent_circular(temp_stack_file, mock_repo_id):
    """Test changing parent would create a circular reference."""
    stacks = Stacks()
    
    # First make sure we have the correct test data
    assert stacks.get_branch_lineage("child1") == ["child1", "feature", "main"]
    
    # Attempt to create a circular reference
    assert stacks.change_parent("main", "child1") is False
    assert stacks.get_parent("main") == ""  # Unchanged


def test_stacks_get_common_ancestor(temp_stack_file, mock_repo_id):
    """Test finding the common ancestor of two branches."""
    stacks = Stacks()
    assert stacks.get_common_ancestor("child1", "child2") == "feature"
    assert stacks.get_common_ancestor("child1", "sibling") == "main"
    assert stacks.get_common_ancestor("nonexistent", "child1") is None


def test_stacks_visualize_tree(temp_stack_file, mock_repo_id):
    """Test generating a tree visualization."""
    stacks = Stacks()
    tree = stacks.visualize_tree()
    
    # Basic checks on tree structure
    assert "main" in tree
    assert "  feature" in tree  # Two spaces for indentation
    assert "    child1" in tree  # Four spaces for indentation
    assert "    child2" in tree
    assert "  sibling" in tree


def test_stacks_get_all_branches(temp_stack_file, mock_repo_id):
    """Test getting all branches."""
    stacks = Stacks()
    branches = stacks.get_all_branches()
    assert sorted(branches) == ["child1", "child2", "feature", "main", "sibling"]


def test_stacks_branch_exists(temp_stack_file, mock_repo_id):
    """Test checking if a branch exists."""
    stacks = Stacks()
    assert stacks.branch_exists("feature") is True
    assert stacks.branch_exists("nonexistent") is False


def test_stacks_context_manager(temp_stack_file, mock_repo_id):
    """Test using Stacks as a context manager."""
    with Stacks() as stacks:
        stacks.add_branch("new-branch", "main")
    
    # Verify data was saved
    new_stacks = Stacks()
    assert "new-branch" in new_stacks.get_all_branches()
    assert new_stacks.get_parent("new-branch") == "main"


def test_stacks_nonexistent_file(tmp_path, mock_repo_id):
    """Test initialization with nonexistent file."""
    panqake_dir = tmp_path / ".panqake"
    stack_file = panqake_dir / "stacks.json"
    
    with patch("panqake.utils.stack.STACK_FILE", stack_file):
        with patch("panqake.utils.stack.PANQAKE_DIR", panqake_dir):
            stacks = Stacks()
            assert stacks.load() is True
            assert stacks._branches == {}