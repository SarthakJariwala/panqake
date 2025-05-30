"""Reusable selection utility functions for panqake CLI.

This module provides common interactive selection patterns used across multiple commands,
ensuring consistent behavior and reducing code duplication.
"""

from typing import Any

from panqake.utils.git import get_current_branch, list_all_branches
from panqake.utils.questionary_prompt import (
    prompt_checkbox,
    prompt_for_parent,
    prompt_select,
)


def select_branch_excluding_current(
    message: str = "Select a branch",
    exclude_protected: bool = True,
    enable_search: bool = True,
) -> str | None:
    """Select a branch from available branches, excluding the current branch.

    Args:
        message: Message to display to the user
        exclude_protected: Whether to exclude protected branches (main, master)
        enable_search: Whether to enable search functionality

    Returns:
        Selected branch name or None if no selection made or no branches available
    """
    # Get all available branches
    branches = list_all_branches()
    if not branches:
        return None

    current = get_current_branch()

    # Filter out current branch
    filtered_branches = [branch for branch in branches if branch != current]

    # Filter out protected branches if requested
    if exclude_protected:
        protected_branches = ["main", "master"]
        filtered_branches = [
            branch for branch in filtered_branches if branch not in protected_branches
        ]

    if not filtered_branches:
        return None

    # Format branches for display
    choices = [{"display": branch, "value": branch} for branch in filtered_branches]

    return prompt_select(message, choices, enable_search=enable_search)


def select_branches_excluding_current(
    message: str = "Select branches",
    exclude_protected: bool = True,
    enable_search: bool = True,
    default_all: bool = False,
) -> list[str]:
    """Select multiple branches from available branches, excluding the current branch.

    Args:
        message: Message to display to the user
        exclude_protected: Whether to exclude protected branches (main, master)
        enable_search: Whether to enable search functionality
        default_all: Whether to select all branches by default

    Returns:
        List of selected branch names
    """
    # Get all available branches
    branches = list_all_branches()
    if not branches:
        return []

    current = get_current_branch()

    # Filter out current branch
    filtered_branches = [branch for branch in branches if branch != current]

    # Filter out protected branches if requested
    if exclude_protected:
        protected_branches = ["main", "master"]
        filtered_branches = [
            branch for branch in filtered_branches if branch not in protected_branches
        ]

    if not filtered_branches:
        return []

    # Format branches for checkbox selection
    choices = [{"display": branch, "value": branch} for branch in filtered_branches]

    default = choices if default_all else None

    return prompt_checkbox(
        message, choices, default=default, enable_search=enable_search
    )


def select_parent_branch(
    potential_parents: list[str], message: str = "Select a parent branch"
) -> str | None:
    """Select a parent branch from a list of potential parents.

    Args:
        potential_parents: List of potential parent branch names
        message: Message to display to the user (search will be auto-enabled)

    Returns:
        Selected parent branch name or None if no selection made
    """
    if not potential_parents:
        return None

    return prompt_for_parent(potential_parents)


def select_files_for_staging(
    files: list[dict[str, Any]],
    message: str = "Select files to stage",
    default_all: bool = True,
    search_threshold: int = 10,
) -> list[str]:
    """Select files from a list for staging operations.

    Args:
        files: List of file dictionaries with 'display' and 'path' keys
        message: Message to display to the user
        default_all: Whether to select all files by default
        search_threshold: Enable search if more than this many files

    Returns:
        List of selected file paths
    """
    if not files:
        return []

    # Enable search if there are many files
    enable_search = len(files) > search_threshold

    # Set default selection
    default = files if default_all else None

    return prompt_checkbox(
        message,
        files,
        default=default,
        enable_search=enable_search,
    )


def select_reviewers(
    potential_reviewers: list[str],
    message: str = "Select reviewers (optional)",
    include_skip_option: bool = True,
) -> list[str]:
    """Select reviewers from a list of potential reviewers.

    Args:
        potential_reviewers: List of potential reviewer usernames
        message: Message to display to the user
        include_skip_option: Whether to include a skip option

    Returns:
        List of selected reviewer usernames
    """
    if not potential_reviewers:
        return []

    # Build choices list
    choices = []
    if include_skip_option:
        choices.append({"name": "(Skip - no reviewers)", "value": ""})

    choices.extend(
        [{"name": reviewer, "value": reviewer} for reviewer in potential_reviewers]
    )

    selected = prompt_checkbox(
        message,
        choices,
        default=[],
        enable_search=True,
    )

    # Filter out empty selections (skip option)
    return [reviewer for reviewer in selected if reviewer]


def select_from_options(
    options: list[str],
    message: str = "Select an option",
    default: str | None = None,
    enable_search: bool = False,
) -> str | None:
    """Select a single option from a predefined list.

    Args:
        options: List of available options
        message: Message to display to the user
        default: Default selection
        enable_search: Whether to enable search functionality

    Returns:
        Selected option or None if no selection made
    """
    if not options:
        return None

    return prompt_select(
        message,
        choices=options,
        default=default,
        enable_search=enable_search,
    )


def select_multiple_from_options(
    options: list[str],
    message: str = "Select options",
    default: list[str] | None = None,
    enable_search: bool = False,
) -> list[str]:
    """Select multiple options from a predefined list.

    Args:
        options: List of available options
        message: Message to display to the user
        default: Default selections
        enable_search: Whether to enable search functionality

    Returns:
        List of selected options
    """
    if not options:
        return []

    return prompt_checkbox(
        message,
        options,
        default=default,
        enable_search=enable_search,
    )
