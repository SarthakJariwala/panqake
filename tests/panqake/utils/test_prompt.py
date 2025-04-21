"""Tests for the prompt module."""

import pytest
from prompt_toolkit.document import Document
from prompt_toolkit.validation import ValidationError

from panqake.utils.prompt import BranchNameValidator


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
