"""Standardized error handling utilities for panqake commands."""

import sys

from panqake.utils.questionary_prompt import print_formatted_text


def exit_with_error(message: str, exit_code: int = 1) -> None:
    """Exit the program with a standardized error message.

    Args:
        message: Error message to display (should include Rich markup tags)
        exit_code: Exit code to use (default: 1)
    """
    print_formatted_text(message)
    sys.exit(exit_code)


def exit_with_warning(message: str, exit_code: int = 1) -> None:
    """Exit the program with a warning message in standard format.

    Args:
        message: Warning message content (Rich markup will be added)
        exit_code: Exit code to use (default: 1)
    """
    formatted_message = f"[warning]{message}[/warning]"
    print_formatted_text(formatted_message)
    sys.exit(exit_code)


def exit_with_success(message: str, exit_code: int = 0) -> None:
    """Exit the program with a success message.

    Args:
        message: Success message content (Rich markup will be added)
        exit_code: Exit code to use (default: 0)
    """
    formatted_message = f"[success]{message}[/success]"
    print_formatted_text(formatted_message)
    sys.exit(exit_code)


def print_error(message: str) -> None:
    """Print an error message without exiting.

    Args:
        message: Error message content (Rich markup will be added)
    """
    formatted_message = f"[warning]{message}[/warning]"
    print_formatted_text(formatted_message)


def print_warning(message: str) -> None:
    """Print a warning message without exiting.

    Args:
        message: Warning message content (Rich markup will be added)
    """
    formatted_message = f"[warning]{message}[/warning]"
    print_formatted_text(formatted_message)
