"""Questionary prompt utilities for panqake git-stacking utility.

This module provides styled prompt utilities for user interaction using Rich.

Rich Style Names (defined in rich_theme):
- warning: Yellow
- danger: Red bold
- info: Cyan
- success: Green
- branch: Green
- muted: Grey70
- prompt: Purple bold (used for interactive prompt messages)

Usage example:
    from panqake.utils.questionary_prompt import console, print_formatted_text

    # Print styled text using Rich markup
    print_formatted_text("[info]This is an informational message[/info]")
    print_formatted_text("[warning]This is a warning[/warning]")

    # Format branch names (returns Rich markup string)
    from panqake.utils.questionary_prompt import format_branch
    formatted = format_branch("main", current=True)
    print_formatted_text(f"Current branch: {formatted}")

    # Or print directly using the themed console
    console.print("[success]Operation successful![/success]")
"""

from typing import Any, List, Optional, Union

import questionary
from questionary import Choice, ValidationError, Validator
from rich.console import Console
from rich.theme import Theme

# Create a Rich theme that will be used across the application
rich_theme = Theme(
    {
        "warning": "yellow",
        "danger": "red bold",
        "info": "cyan",
        "success": "green",
        "branch": "green",
        "muted": "grey70",
        "prompt": "white bold",  # For questionary elements/prompts
        "highlight": "white italic",  # Used in rich_prompt, could be used elsewhere
        "selected": "cyan bold",  # Used in rich_prompt, could be used elsewhere
    }
)

# Create a console instance with the theme.
# Rich markup parsing is enabled by default.
console = Console(theme=rich_theme)

# Create a questionary style that visually aligns with our rich theme
# Note: This uses prompt_toolkit style syntax, not Rich markup.
style = questionary.Style(
    [
        ("qmark", "white bold"),  # token in front of the question
        ("question", "bold"),  # question text
        ("answer", "orange bold"),  # submitted answer text
        ("pointer", "orange bold"),  # pointer used in select and checkbox prompts
        (
            "highlighted",
            "orange bold",
        ),  # pointed-at choice in select and checkbox prompts
        ("selected", "orange bold"),  # style for a selected item of a checkbox
        ("separator", "red"),  # separator in lists
        ("instruction", ""),  # user instructions for select, rawselect, checkbox
        ("text", ""),  # plain text
        ("disabled", "gray italic"),  # disabled choices for select and checkbox prompts
    ]
)


def print_formatted_text(text: str) -> None:
    """Prints text assuming it contains Rich markup (e.g., [info]text[/info]).

    The console is themed, so Rich handles the markup automatically.
    """
    console.print(text, markup=True)  # Explicitly ensure markup is enabled


def format_branch(branch_name: str, current: bool = False, danger: bool = False) -> str:
    """Format branch name with Rich markup tags.

    Returns a string ready for printing with rich.console.Console.
    """
    if danger:
        # Use the 'danger' style from the theme
        return f"[danger]{branch_name}[/danger]"
    elif current:
        # Use 'branch' style, make it bold for emphasis
        return f"[branch]* {branch_name}[/branch]"
    else:
        # Use the standard 'branch' style
        return f"{branch_name}"


def rich_prompt(message: str, style_name: str = "prompt") -> None:
    """Print a prompt message with Rich styling before questionary input."""
    # Ensure the style_name exists in the theme for safety, though console.print handles it
    style_to_use = style_name if style_name in rich_theme.styles else "none"
    console.print(f"[{style_to_use}]{message}[/{style_to_use}]")


def prompt_input(
    message: str,
    validator: Optional[Validator] = None,
    completer: Optional[Union[List[str], Any]] = None,
    default: str = "",
) -> str:
    """Get user input using questionary with Rich styling for the prompt."""
    rich_prompt(f"{message}", "prompt")  # Display prompt using Rich

    choices = None
    if completer:
        if isinstance(completer, list):
            choices = completer
        elif hasattr(completer, "words"):
            choices = completer.words

    if choices:
        # Pass empty message to questionary as Rich handled it
        return questionary.autocomplete(
            "", choices=choices, default=default, validate=validator, style=style
        ).ask()
    else:
        # Pass empty message to questionary
        return questionary.text(
            "", default=default, validate=validator, style=style
        ).ask()


def prompt_confirm(message: str) -> bool:
    """Prompt for confirmation with yes/no options, using Rich for the prompt."""
    rich_prompt(f"{message}", "prompt")  # Display prompt using Rich
    # Pass empty message to questionary
    return questionary.confirm("", default=False, style=style).ask()


def prompt_checkbox(
    message: str,
    choices: List[Union[str, dict]],
    default: Optional[List[Union[str, dict]]] = None,
) -> List[str]:
    """Prompt user to select multiple items from a list, using Rich for the prompt."""
    rich_prompt(f"{message}", "prompt")  # Display prompt using Rich

    default_values = []
    if default is not None:
        for d in default:
            value = (
                d.get("path")
                if isinstance(d, dict) and "path" in d
                else d.get("value")
                if isinstance(d, dict) and "value" in d
                else d
            )
            default_values.append(value)

    processed_choices = []
    for choice in choices:
        if isinstance(choice, dict) and "display" in choice:
            value = choice["path"]
            name = choice["display"]
            checked = default is None or value in default_values
            processed_choices.append(Choice(name, value=value, checked=checked))
        elif isinstance(choice, dict) and "name" in choice and "value" in choice:
            value = choice["value"]
            name = choice["name"]
            checked = default is None or value in default_values
            processed_choices.append(Choice(name, value=value, checked=checked))
        else:
            value = choice
            name = str(choice)
            checked = default is None or value in default_values
            processed_choices.append(Choice(name, value=value, checked=checked))

    # Use the Choice objects with checked state (no default parameter needed)
    result = questionary.checkbox("", choices=processed_choices, style=style).ask()

    return result


def prompt_select(
    message: str, choices: List[Union[str, dict]], default: Optional[str] = None
) -> str:
    """Display a select prompt with the given choices.

    Args:
        message: The message to display
        choices: List of choice dictionaries with 'display', 'value', and optional 'disabled' keys
        default: Default selected item

    Returns:
        The value of the selected choice
    """
    # Format choices for questionary
    questionary_choices = []
    for choice in choices:
        if isinstance(choice, dict):
            if choice.get("disabled", False):
                questionary_choices.append(
                    questionary.Choice(
                        title=choice["display"],
                        value=choice["value"],
                    )
                )
            else:
                questionary_choices.append(
                    questionary.Choice(title=choice["display"], value=choice["value"])
                )
        else:
            # Handle simple string choices
            questionary_choices.append(choice)

    # Show the prompt with rich styling
    rich_prompt(f"{message}", "prompt")

    # Use questionary's select with empty message since we displayed it with rich_prompt
    result = questionary.select(
        "",
        choices=questionary_choices,
        style=style,
    ).ask()

    return result


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

    # Use rich to style the prompt message
    rich_prompt("Select a parent branch (autocomplete or arrow keys)", "prompt")

    # Use questionary with empty message since we've already displayed it
    selected = questionary.select("", choices=potential_parents, style=style).ask()

    return selected
