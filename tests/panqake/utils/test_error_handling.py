"""Tests for error handling utilities."""

from unittest.mock import patch

from panqake.utils.error_handling import (
    exit_with_error,
    exit_with_warning,
    exit_with_success,
    print_error,
    print_warning,
)


class TestErrorHandling:
    """Test error handling utility functions."""

    @patch("panqake.utils.error_handling.print_formatted_text")
    @patch("panqake.utils.error_handling.sys.exit")
    def test_exit_with_error(self, mock_exit, mock_print):
        """Test exit_with_error function."""
        exit_with_error("[warning]Test error[/warning]")

        mock_print.assert_called_once_with("[warning]Test error[/warning]")
        mock_exit.assert_called_once_with(1)

    @patch("panqake.utils.error_handling.print_formatted_text")
    @patch("panqake.utils.error_handling.sys.exit")
    def test_exit_with_error_custom_code(self, mock_exit, mock_print):
        """Test exit_with_error with custom exit code."""
        exit_with_error("[warning]Test error[/warning]", exit_code=2)

        mock_print.assert_called_once_with("[warning]Test error[/warning]")
        mock_exit.assert_called_once_with(2)

    @patch("panqake.utils.error_handling.print_formatted_text")
    @patch("panqake.utils.error_handling.sys.exit")
    def test_exit_with_warning(self, mock_exit, mock_print):
        """Test exit_with_warning function."""
        exit_with_warning("Test warning message")

        mock_print.assert_called_once_with("[warning]Test warning message[/warning]")
        mock_exit.assert_called_once_with(1)

    @patch("panqake.utils.error_handling.print_formatted_text")
    @patch("panqake.utils.error_handling.sys.exit")
    def test_exit_with_success(self, mock_exit, mock_print):
        """Test exit_with_success function."""
        exit_with_success("Operation completed successfully")

        mock_print.assert_called_once_with(
            "[success]Operation completed successfully[/success]"
        )
        mock_exit.assert_called_once_with(0)

    @patch("panqake.utils.error_handling.print_formatted_text")
    def test_print_error(self, mock_print):
        """Test print_error function."""
        print_error("Test error message")

        mock_print.assert_called_once_with("[warning]Test error message[/warning]")

    @patch("panqake.utils.error_handling.print_formatted_text")
    def test_print_warning(self, mock_print):
        """Test print_warning function."""
        print_warning("Test warning message")

        mock_print.assert_called_once_with("[warning]Test warning message[/warning]")
