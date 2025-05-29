"""Utility module for managing transient status messages with Rich Status."""

import contextlib
import signal
import sys
from typing import Any, Generator

from rich.console import Console
from rich.errors import LiveError
from rich.status import Status

from panqake.utils.questionary_prompt import print_formatted_text, rich_theme

# Global reference to the currently active status for nested forwarding
_active_status: "StatusWithPause | None" = None


class StatusWithPause:
    """Wrapper around Rich Status that adds pause_and_print functionality."""

    def __init__(self, status: Status) -> None:
        self._status = status
        self._is_running = False

    def start(self) -> None:
        """Start the status display."""
        self._status.start()
        self._is_running = True

    def stop(self) -> None:
        """Stop the status display."""
        self._status.stop()
        self._is_running = False

    def update(self, message: str) -> None:
        """Update the status message."""
        self._status.update(message)

    def pause_and_print(self, message: str) -> None:
        """Temporarily pause status, print message, then resume."""
        if self._is_running:
            self._status.stop()
            print_formatted_text(message)
            self._status.start()
        else:
            print_formatted_text(message)


class StatusManager:
    """Context manager for Rich Status with proper cleanup on interrupts."""

    def __init__(self, message: str, spinner: str = "dots") -> None:
        self.message = message
        self.spinner = spinner
        self.status: StatusWithPause | None = None
        self._original_handler: Any = None
        self._is_nested = False
        # Create a new console instance to avoid conflicts
        self.console = Console(theme=rich_theme)

    def __enter__(self) -> StatusWithPause:
        """Start the status display and set up interrupt handling."""
        global _active_status

        raw_status = Status(self.message, console=self.console, spinner=self.spinner)
        self.status = StatusWithPause(raw_status)

        # Store original SIGINT handler
        self._original_handler = signal.signal(signal.SIGINT, self._handle_interrupt)

        try:
            self.status.start()
            _active_status = self.status  # Set as active status
        except LiveError:
            # If another Live display is already active, mark this as nested
            # and create a proxy that forwards updates to the active status
            self._is_nested = True
            nested_status = _NestedStatus(self.message, _active_status)
            self.status = nested_status  # type: ignore[assignment]

        return self.status  # type: ignore[return-value]

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Stop the status display and restore interrupt handling."""
        global _active_status

        if self.status and not self._is_nested:
            self.status.stop()
            _active_status = None  # Clear active status

        # Restore original SIGINT handler
        if self._original_handler is not None:
            signal.signal(signal.SIGINT, self._original_handler)

    def _handle_interrupt(self, signum: int, frame: Any) -> None:
        """Handle keyboard interrupt by cleaning up status and exiting."""
        if self.status and not self._is_nested:
            self.status.stop()

        # Restore original handler and re-raise
        if self._original_handler is not None:
            signal.signal(signal.SIGINT, self._original_handler)

        print("\nOperation cancelled by user.")
        sys.exit(130)  # Standard exit code for SIGINT


class _NestedStatus:
    """Proxy status object for nested status contexts that forwards updates."""

    def __init__(
        self, message: str, active_status: "StatusWithPause | None" = None
    ) -> None:
        self.message = message
        self._active_status = active_status

    def update(self, message: str) -> None:
        """Forward update to the active status if available."""
        if self._active_status:
            self._active_status.update(message)

    def stop(self) -> None:
        """Stop method that does nothing for nested contexts."""
        pass

    def pause_and_print(self, message: str) -> None:
        """Pause status, print message, and resume - forward to active status."""
        if self._active_status and hasattr(self._active_status, "pause_and_print"):
            self._active_status.pause_and_print(message)
        else:
            # Fallback to console print if no active status
            print_formatted_text(message)


@contextlib.contextmanager
def status(
    message: str, spinner: str = "dots"
) -> Generator[StatusWithPause, None, None]:
    """Context manager for showing a status message with spinner.

    Args:
        message: The status message to display
        spinner: The spinner style (default: "dots")

    Yields:
        The Rich Status object for updating the message

    Example:
        with status("Processing files...") as s:
            # Do some work
            s.update("Processing file 1...")
            # Do more work
            s.update("Processing file 2...")
    """
    with StatusManager(message, spinner) as s:
        yield s
