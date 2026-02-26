"""Helper functions for command execution."""

import contextlib
import dataclasses
import io
import json
import sys
import warnings
from collections.abc import Callable
from typing import Any, TypeVar

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


def _to_jsonable(obj: Any) -> Any:
    """Convert an object to a JSON-serializable form."""
    if dataclasses.is_dataclass(obj) and not isinstance(obj, type):
        return dataclasses.asdict(obj)
    warnings.warn(
        f"_to_jsonable fell back to str() for {type(obj).__name__}",
        stacklevel=2,
    )
    return str(obj)


def emit_json_success(command: str, result: Any) -> None:
    """Print a JSON success envelope to stdout."""
    payload: dict[str, Any] = {"ok": True, "command": command}
    if result is not None:
        if dataclasses.is_dataclass(result) and not isinstance(result, type):
            payload["result"] = dataclasses.asdict(result)
        else:
            payload["result"] = result
    print(json.dumps(payload, ensure_ascii=False, default=_to_jsonable))


def _emit_json_error(command: str | None, error: PanqakeError) -> None:
    """Print a JSON error envelope to stdout."""
    payload: dict[str, Any] = {
        "ok": False,
        "command": command,
        "error": {
            "type": type(error).__name__,
            "message": error.message,
            "exit_code": error.exit_code,
        },
    }
    print(json.dumps(payload, ensure_ascii=False))


def run_command(
    ui: UIPort,
    core_fn: Callable[[], T],
    *,
    json_output: bool = False,
    command: str | None = None,
) -> T | None:
    """Run a command core function with standardized error handling.

    Catches PanqakeError and converts to UI output + sys.exit.
    When json_output=True, emits JSON error envelopes instead of rich text.

    Returns:
        The result of core_fn, or None if an error occurred (after sys.exit).
    """
    try:
        if json_output:
            # Suppress incidental stdout from low-level git/gh utilities so
            # --json mode emits a single machine-readable document.
            with contextlib.redirect_stdout(io.StringIO()):
                return core_fn()
        return core_fn()
    except UserCancelledError as e:
        if json_output:
            _emit_json_error(command, e)
            sys.exit(130)
        ui.print_muted("\nInterrupted by user")
        sys.exit(130)
    except PanqakeError as e:
        if json_output:
            _emit_json_error(command, e)
            sys.exit(e.exit_code)
        ui.print_error(f"Error: {e.message}")
        sys.exit(e.exit_code)
