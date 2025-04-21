"""Prompt toolkit utilities for interactive CLI."""

from prompt_toolkit import prompt
from prompt_toolkit.validation import ValidationError, Validator


def prompt_input(message, validator=None, completer=None, default=""):
    """Get user input with prompt_toolkit."""
    return prompt(
        message,
        validator=validator,
        completer=completer,
        default=default,
    )


class BranchNameValidator(Validator):
    """Validator for branch names."""

    def validate(self, document):
        """Validate branch name."""
        text = document.text
        if not text:
            raise ValidationError(message="Branch name cannot be empty")
        if " " in text:
            raise ValidationError(message="Branch name cannot contain spaces")
        if ".." in text:
            raise ValidationError(message="Branch name cannot contain '..'")
