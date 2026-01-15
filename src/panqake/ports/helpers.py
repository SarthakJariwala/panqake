"""Helper functions for command execution."""

import sys
from collections.abc import Callable
from typing import TypeVar

from panqake.utils.types import BranchName

from .exceptions import PanqakeError, UserCancelledError
from .protocols import ConfigPort, UIPort

T = TypeVar("T")


def find_stack_root(branch: BranchName, config: ConfigPort) -> BranchName:
    """Find the root of the stack for a given branch.

    Recursively traverses parent branches until finding one with no parent.

    Args:
        branch: Branch to find root for
        config: Stack configuration interface

    Returns:
        The root branch of the stack
    """
    parent = config.get_parent_branch(branch)
    if not parent:
        return branch
    return find_stack_root(parent, config)


def run_command(
    ui: UIPort,
    core_fn: Callable[[], T],
) -> T | None:
    """Run a command core function with standardized error handling.

    Catches PanqakeError and converts to UI output + sys.exit.

    Returns:
        The result of core_fn, or None if an error occurred (after sys.exit).
    """
    try:
        return core_fn()
    except UserCancelledError:
        ui.print_muted("\nInterrupted by user")
        sys.exit(130)
    except PanqakeError as e:
        ui.print_error(f"Error: {e.message}")
        sys.exit(e.exit_code)
