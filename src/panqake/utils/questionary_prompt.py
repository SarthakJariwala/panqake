"""Questionary prompt utilities for panqake git-stacking utility.

This module provides styled prompt utilities for user interaction.

Styling options:
- warning: bright yellow for warnings
- danger: bright red for dangerous actions
- info: cyan for informational messages
- success: bright green for success messages
- branch: green for branch names
- muted: gray for less important text

Usage example:
    from panqake.utils.questionary_prompt import print_formatted_text

    # Print styled text
    print_formatted_text("<info>This is an informational message</info>")
    print_formatted_text("<warning>This is a warning</warning>")

    # Format branch names
    from panqake.utils.questionary_prompt import format_branch
    formatted = format_branch("main", current=True)
    print_formatted_text(formatted)
"""

from typing import Any, List, Optional, Union

import questionary
from questionary import ValidationError, Validator

# Define a style with colors that match terminal's native appearance
style = questionary.Style(
    [
        ("qmark", "fg:#FFCC00 bold"),  # yellow question mark
        ("question", "bold"),  # bold question text
        ("answer", "fg:#FFFFFF"),  # white answers
        ("pointer", "fg:#00FF00 bold"),  # green pointer
        ("highlighted", "fg:#00FF00 bold"),  # green highlighted item
        ("selected", "fg:#00FF00"),  # green selected items
        ("danger", "fg:#FF5555 bold"),  # bright red for dangerous actions
        ("warning", "fg:#FFFF00"),  # bright yellow for warnings
        ("info", "fg:#00CCFF"),  # cyan for info
        ("success", "fg:#00FF00"),  # bright green for success
        ("branch", "fg:#00FF00"),  # green for branch names
        ("muted", "fg:#888888"),  # gray for less important text
    ]
)

# Mapping for style classes to questionary print style strings
# These colors match the terminal's native appearance
STYLE_MAP = {
    "warning": "fg:#FFFF00",  # bright yellow
    "danger": "fg:#FF5555 bold",  # bright red bold
    "info": "fg:#00CCFF",  # cyan
    "success": "fg:#00FF00",  # bright green
    "branch": "fg:#00FF00",  # green
    "muted": "fg:#888888",  # gray
}


def prompt_input(
    message: str,
    validator: Optional[Validator] = None,
    completer: Optional[Union[List[str], Any]] = None,
    default: str = "",
) -> str:
    """Get user input using questionary."""
    # Extract choices from different completer types
    choices = None
    if completer:
        if isinstance(completer, list):
            # Direct list of choices
            choices = completer
        elif hasattr(completer, "words"):
            # WordCompleter from prompt_toolkit
            choices = completer.words

    # If we have choices, use autocomplete
    if choices:
        return questionary.autocomplete(
            message, choices=choices, default=default, validate=validator, style=style
        ).ask()

    # Otherwise use regular text input
    return questionary.text(
        message, default=default, validate=validator, style=style
    ).ask()


def prompt_confirm(message: str) -> bool:
    """Prompt for confirmation with yes/no options."""
    return questionary.confirm(message, default=False, style=style).ask()


def prompt_checkbox(
    message: str,
    choices: List[Union[str, dict]],
    default: Optional[List[Union[str, dict]]] = None,
) -> List[str]:
    """Prompt user to select multiple items from a list.

    Args:
        message: The prompt message
        choices: List of choices (strings or dicts with 'name' and 'value' keys)
        default: Default selected choices

    Returns:
        List of selected values
    """
    from questionary import Choice

    # Process default values to match the expected format
    default_values = []
    if default is not None:
        for d in default:
            if isinstance(d, dict) and "path" in d:
                default_values.append(d["path"])
            elif isinstance(d, dict) and "value" in d:
                default_values.append(d["value"])
            else:
                default_values.append(d)

    # Convert choices to Choice objects with checked state
    processed_choices = []

    for choice in choices:
        if isinstance(choice, dict) and "display" in choice:
            # For our unstaged files format
            value = choice["path"]
            name = choice["display"]
            checked = default is None or value in default_values
            processed_choices.append(Choice(name, value=value, checked=checked))
        elif isinstance(choice, dict) and "name" in choice and "value" in choice:
            # If already in questionary format
            name = choice["name"]
            value = choice["value"]
            checked = default is None or value in default_values
            processed_choices.append(Choice(name, value=value, checked=checked))
        else:
            # Simple string choice
            name = str(choice)
            value = choice
            checked = default is None or value in default_values
            processed_choices.append(Choice(name, value=value, checked=checked))

    # Use the Choice objects with checked state (no default parameter needed)
    result = questionary.checkbox(message, choices=processed_choices, style=style).ask()

    return result


def prompt_select(
    message: str, choices: List[str], default: Optional[str] = None
) -> str:
    """Prompt user to select from a list of choices."""
    return questionary.select(
        message, choices=choices, default=default, style=style
    ).ask()


def format_branch(branch_name: str, current: bool = False, danger: bool = False) -> str:
    """Format branch name with HTML-like style tags.

    This function does not print, it just returns the formatted string.
    Use print_formatted_text to display it.
    """
    if danger:
        return f"<danger>{branch_name}</danger>"
    elif current:
        return f"<branch>* {branch_name}</branch>"
    else:
        # Return plain branch name without style tags for non-current branches
        return branch_name


def print_formatted_text(text: Any) -> None:
    """Print formatted text using questionary's print function."""
    # If text is a string, check for HTML-like tags
    if isinstance(text, str):
        for style_class in STYLE_MAP:
            open_tag = f"<{style_class}>"
            close_tag = f"</{style_class}>"

            if open_tag in text and close_tag in text:
                # Extract the content between tags
                start_idx = text.find(open_tag) + len(open_tag)
                end_idx = text.find(close_tag)
                content = text[start_idx:end_idx]

                # Print with the corresponding style
                questionary.print(content, style=STYLE_MAP[style_class])
                return

        # If no tags found, print as normal text
        print(text)
        return

    # Handle prompt_toolkit HTML objects
    if hasattr(text, "value") and isinstance(text.value, str):
        html_text = text.value
        # Basic parsing of HTML-like format from prompt_toolkit
        for style_class in STYLE_MAP:
            if f"<{style_class}>" in html_text and f"</{style_class}>" in html_text:
                content = html_text.split(f"<{style_class}>")[1].split(
                    f"</{style_class}>"
                )[0]
                questionary.print(content, style=STYLE_MAP[style_class])
                return

    # Fallback for simple text
    print(str(text))


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


class PRTitleValidator(Validator):
    """Validator for PR titles."""

    def validate(self, document):
        """Validate PR title."""
        text = document.text
        if not text:
            raise ValidationError(message="PR title cannot be empty")
        if len(text) < 10:
            raise ValidationError(message="PR title should be at least 10 characters")


def prompt_for_parent(potential_parents: List[str]) -> Optional[str]:
    """Prompt the user to select a parent branch from a list of potential parents.

    Args:
        potential_parents: List of potential parent branch names

    Returns:
        The selected parent branch name, or None if no selection was made
    """
    if not potential_parents:
        return None

    print_formatted_text("<info>Select a parent branch for the current branch:</info>")

    selected = questionary.select(
        "Select a parent branch (autocomplete or arrow keys)",
        choices=potential_parents,
        style=style,
    ).ask()

    return selected
