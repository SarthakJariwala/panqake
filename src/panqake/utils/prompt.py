"""Prompt toolkit utilities for interactive CLI."""

from typing import Optional

from prompt_toolkit import prompt
from prompt_toolkit.completion import Completer
from prompt_toolkit.document import Document
from prompt_toolkit.formatted_text import HTML
from prompt_toolkit.shortcuts import confirm
from prompt_toolkit.styles import Style
from prompt_toolkit.validation import ValidationError, Validator

# Default style for prompt_toolkit elements
style = Style.from_dict(
    {
        "prompt": "ansiyellow bold",
        "input": "ansiwhite",
        "default": "ansigreen italic",
        "warning": "ansired",
        "branch": "ansigreen",
        "danger": "#ff0000 bold",
        "info": "ansiblue",
        "success": "ansigreen",
    }
)


def prompt_input(
    message: str,
    validator: Optional[Validator] = None,
    completer: Optional[Completer] = None,
    default: str = "",
) -> str:
    """Get user input with prompt_toolkit."""
    return prompt(
        HTML(f"<prompt>{message}</prompt>"),
        validator=validator,
        completer=completer,
        default=default,
        style=style,
    )


def prompt_confirm(message: str) -> bool:
    """Prompt for confirmation with yes/no options."""
    # confirm() doesn't accept default or style parameters in prompt_toolkit 3.0.51
    result = confirm(HTML(f"<prompt>{message}</prompt>"))
    return result


def format_branch(
    branch_name: str, current: bool = False, danger: bool = False
) -> HTML:
    """Format branch name with appropriate style."""
    if danger:
        return HTML(f"<danger>{branch_name}</danger>")
    elif current:
        return HTML(f"<branch>* {branch_name}</branch>")
    else:
        return HTML(f"<branch>{branch_name}</branch>")


class BranchNameValidator(Validator):
    """Validator for branch names."""

    def validate(self, document: Document) -> None:
        """Validate branch name."""
        text = document.text
        if not text:
            raise ValidationError(message="Branch name cannot be empty")
        if " " in text:
            raise ValidationError(message="Branch name cannot contain spaces")
        if ".." in text:
            raise ValidationError(message="Branch name cannot contain '..'")


class PRTitleValidator(Validator):
    """Validator for PR titles."""

    def validate(self, document: Document) -> None:
        """Validate PR title."""
        text = document.text
        if not text:
            raise ValidationError(message="PR title cannot be empty")
        if len(text) < 10:
            raise ValidationError(message="PR title should be at least 10 characters")
