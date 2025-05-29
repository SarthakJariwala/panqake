"""Tests for the status utility module."""

import signal
from unittest.mock import MagicMock, patch

from rich.errors import LiveError

from panqake.utils.status import StatusManager, StatusWithPause, _NestedStatus, status


class TestStatusManager:
    """Test cases for StatusManager context manager."""

    def test_status_manager_basic_usage(self):
        """Test basic usage of StatusManager."""
        with patch("panqake.utils.status.Status") as mock_status_class:
            mock_status = MagicMock()
            mock_status_class.return_value = mock_status

            with StatusManager("Test message") as s:
                assert isinstance(s, StatusWithPause)

            mock_status_class.assert_called_once()
            mock_status.start.assert_called_once()
            mock_status.stop.assert_called_once()

    def test_status_manager_with_custom_spinner(self):
        """Test StatusManager with custom spinner."""
        with patch("panqake.utils.status.Status") as mock_status_class:
            mock_status = MagicMock()
            mock_status_class.return_value = mock_status

            with StatusManager("Test message", spinner="line"):
                pass

            # Verify Status was created with correct parameters
            args, kwargs = mock_status_class.call_args
            assert args[0] == "Test message"
            assert "spinner" in kwargs and kwargs["spinner"] == "line"

    def test_status_manager_interrupt_handling(self):
        """Test that StatusManager properly handles interrupts."""
        with patch("panqake.utils.status.Status") as mock_status_class:
            mock_status = MagicMock()
            mock_status_class.return_value = mock_status

            # Mock signal handling
            original_handler = MagicMock()

            with patch("signal.signal", return_value=original_handler) as mock_signal:
                manager = StatusManager("Test message")

                # Enter the context
                status_obj = manager.__enter__()
                assert isinstance(status_obj, StatusWithPause)

                # Verify signal handler was set
                mock_signal.assert_called_with(signal.SIGINT, manager._handle_interrupt)

                # Exit the context
                manager.__exit__(None, None, None)

                # Verify signal handler was restored
                mock_signal.assert_called_with(signal.SIGINT, original_handler)

    def test_status_manager_interrupt_cleanup(self):
        """Test that interrupt handler properly cleans up."""
        with patch("panqake.utils.status.Status") as mock_status_class:
            mock_status = MagicMock()
            mock_status_class.return_value = mock_status

            original_handler = MagicMock()

            with patch("signal.signal", return_value=original_handler) as mock_signal:
                with patch("sys.exit") as mock_exit:
                    manager = StatusManager("Test message")
                    manager.__enter__()

                    # Simulate interrupt
                    manager._handle_interrupt(signal.SIGINT, None)

                    # Verify cleanup occurred
                    mock_status.stop.assert_called_once()
                    mock_signal.assert_called_with(signal.SIGINT, original_handler)
                    mock_exit.assert_called_once_with(130)

    def test_status_manager_exception_cleanup(self):
        """Test that StatusManager cleans up properly on exceptions."""
        with patch("panqake.utils.status.Status") as mock_status_class:
            mock_status = MagicMock()
            mock_status_class.return_value = mock_status

            original_handler = MagicMock()

            with patch("signal.signal", return_value=original_handler):
                try:
                    with StatusManager("Test message"):
                        raise ValueError("Test exception")
                except ValueError:
                    pass

                # Verify cleanup occurred even with exception
                mock_status.stop.assert_called_once()


class TestStatusFunction:
    """Test cases for the status context manager function."""

    def test_status_function(self):
        """Test the status context manager function."""
        with patch("panqake.utils.status.StatusManager") as mock_manager_class:
            mock_manager = MagicMock()
            mock_status = MagicMock()
            mock_manager.__enter__.return_value = mock_status
            mock_manager_class.return_value = mock_manager

            with status("Test message") as s:
                assert s == mock_status

            mock_manager_class.assert_called_once_with("Test message", "dots")
            mock_manager.__enter__.assert_called_once()
            mock_manager.__exit__.assert_called_once()

    def test_status_function_with_custom_spinner(self):
        """Test the status function with custom spinner."""
        with patch("panqake.utils.status.StatusManager") as mock_manager_class:
            mock_manager = MagicMock()
            mock_manager_class.return_value = mock_manager

            with status("Test message", spinner="line"):
                pass

            mock_manager_class.assert_called_once_with("Test message", "line")

    def test_status_manager_nested_handling(self):
        """Test that StatusManager handles nested contexts gracefully."""
        with patch("panqake.utils.status.Status") as mock_status_class:
            mock_status = MagicMock()
            mock_status_class.return_value = mock_status

            # First call succeeds
            mock_status.start.side_effect = [None, LiveError("Already active")]

            with StatusManager("First message") as s1:
                assert isinstance(s1, StatusWithPause)

                # Second call should create a nested status proxy
                with StatusManager("Second message") as s2:
                    assert isinstance(s2, _NestedStatus)
                    assert s2.message == "Second message"
                    assert isinstance(s2._active_status, StatusWithPause)

            # Only the first status should have been started and stopped
            mock_status.start.assert_called()
            mock_status.stop.assert_called_once()


class TestNestedStatus:
    """Test cases for the _NestedStatus mock object."""

    def test_nested_status_creation(self):
        """Test creating a nested status object."""
        nested = _NestedStatus("Test message")
        assert nested.message == "Test message"
        assert nested._active_status is None

    def test_nested_status_with_active_status(self):
        """Test nested status with an active status to forward to."""
        mock_active = MagicMock()
        nested = _NestedStatus("Test message", mock_active)
        assert nested.message == "Test message"
        assert nested._active_status == mock_active

    def test_nested_status_update_forwards(self):
        """Test that update method forwards to active status."""
        mock_active = MagicMock()
        nested = _NestedStatus("Test message", mock_active)

        nested.update("New message")
        mock_active.update.assert_called_once_with("New message")

    def test_nested_status_update_no_active(self):
        """Test that update method works when no active status."""
        nested = _NestedStatus("Test message")
        # Should not raise any exception when no active status
        nested.update("New message")

    def test_nested_status_stop(self):
        """Test that stop method works but does nothing."""
        nested = _NestedStatus("Test message")
        # Should not raise any exception
        nested.stop()

    def test_nested_update_forwarding_integration(self):
        """Test that nested contexts forward updates to the outer status."""
        with patch("panqake.utils.status.Status") as mock_status_class:
            mock_status = MagicMock()
            mock_status_class.return_value = mock_status

            # Simulate outer status succeeding, inner status getting LiveError
            mock_status.start.side_effect = [None, LiveError("Already active")]

            with status("Outer operation") as outer:
                # This should be the real status
                assert isinstance(outer, StatusWithPause)

                with status("Inner operation") as inner:
                    # This should be a nested proxy
                    assert isinstance(inner, _NestedStatus)

                    # Update through nested should forward to outer
                    inner.update("Processing item 1...")
                    mock_status.update.assert_called_with("Processing item 1...")

                    inner.update("Processing item 2...")
                    mock_status.update.assert_called_with("Processing item 2...")


class TestStatusWithPause:
    """Test cases for the StatusWithPause wrapper."""

    def test_pause_and_print_while_running(self):
        """Test pause_and_print when status is running."""
        with patch("panqake.utils.status.Status") as mock_status_class:
            mock_status = MagicMock()
            mock_status_class.return_value = mock_status

            with patch("panqake.utils.status.print_formatted_text") as mock_print:
                wrapper = StatusWithPause(mock_status)
                wrapper.start()

                wrapper.pause_and_print("[info]Test message[/info]")

                # Should stop, print, then start again
                assert mock_status.stop.call_count == 1
                mock_print.assert_called_once_with("[info]Test message[/info]")
                assert mock_status.start.call_count == 2  # Initial + restart

    def test_pause_and_print_while_stopped(self):
        """Test pause_and_print when status is not running."""
        with patch("panqake.utils.status.Status") as mock_status_class:
            mock_status = MagicMock()
            mock_status_class.return_value = mock_status

            with patch("panqake.utils.status.print_formatted_text") as mock_print:
                wrapper = StatusWithPause(mock_status)
                # Don't start the status

                wrapper.pause_and_print("[info]Test message[/info]")

                # Should only print, no stop/start
                mock_status.stop.assert_not_called()
                mock_print.assert_called_once_with("[info]Test message[/info]")
                mock_status.start.assert_not_called()
