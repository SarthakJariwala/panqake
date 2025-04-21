"""Tests for the prompt module."""

from unittest.mock import patch

import pytest
from prompt_toolkit.document import Document
from prompt_toolkit.validation import ValidationError

from panqake.utils.prompt import (
    BranchNameValidator,
    PRTitleValidator,
    format_branch,
    prompt_confirm,
)


def test_branch_name_validator():
    """Test BranchNameValidator."""
    validator = BranchNameValidator()

    # Valid branch names should pass
    validator.validate(Document("feature-branch"))
    validator.validate(Document("hotfix/bug-123"))
    validator.validate(Document("release-1.0.0"))

    # Empty branch name should fail
    with pytest.raises(ValidationError):
        validator.validate(Document(""))

    # Branch name with spaces should fail
    with pytest.raises(ValidationError):
        validator.validate(Document("feature branch"))

    # Branch name with '..' should fail
    with pytest.raises(ValidationError):
        validator.validate(Document("feature..branch"))


def test_pr_title_validator():
    """Test PRTitleValidator."""
    validator = PRTitleValidator()

    # Valid PR titles should pass
    validator.validate(Document("Add new feature for branch stacking"))
    validator.validate(Document("Fix bug in rebase operation"))

    # Empty PR title should fail
    with pytest.raises(ValidationError):
        validator.validate(Document(""))

    # PR title too short should fail
    with pytest.raises(ValidationError):
        validator.validate(Document("Fix bug"))


@patch("panqake.utils.prompt.confirm")
def test_prompt_confirm(mock_confirm):
    """Test prompt_confirm function."""
    mock_confirm.return_value = True

    # Test with default settings
    result = prompt_confirm("Are you sure?")
    assert result is True
    mock_confirm.assert_called_once()

    # Reset mock
    mock_confirm.reset_mock()

    # Test with explicit default
    mock_confirm.return_value = False
    result = prompt_confirm("Delete branch?", default=True)
    assert result is False
    mock_confirm.assert_called_once()


def test_format_branch():
    """Test format_branch function."""
    # Normal branch formatting
    result = format_branch("feature")
    assert "feature" in str(result)
    assert "branch" in str(result)

    # Current branch formatting
    result = format_branch("main", current=True)
    assert "main" in str(result)
    assert "*" in str(result)

    # Danger branch formatting
    result = format_branch("to-delete", danger=True)
    assert "to-delete" in str(result)
    assert "danger" in str(result)
