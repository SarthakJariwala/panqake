"""Tests for interrupt handling in questionary prompts."""

from unittest.mock import patch

import pytest

from panqake.utils.exit import clean_exit
from panqake.utils.questionary_prompt import (
    prompt_confirm,
    prompt_input,
    prompt_select,
)


def test_clean_exit():
    """Test clean_exit function."""
    with (
        patch("sys.exit") as mock_exit,
        patch("panqake.utils.questionary_prompt.console") as mock_console,
    ):
        clean_exit()
        mock_console.print.assert_called_once_with(
            "\n[muted]Interrupted by user[/muted]"
        )
        mock_exit.assert_called_once_with(130)


def test_clean_exit_custom_code():
    """Test clean_exit with custom exit code."""
    with (
        patch("sys.exit") as mock_exit,
        patch("panqake.utils.questionary_prompt.console"),
    ):
        clean_exit(code=1)
        mock_exit.assert_called_once_with(1)


@patch("panqake.utils.questionary_prompt.questionary.text")
def test_prompt_input_keyboard_interrupt(mock_text):
    """Test that prompt_input handles KeyboardInterrupt properly."""
    mock_text.return_value.ask.side_effect = KeyboardInterrupt()

    with pytest.raises(SystemExit) as exc_info:
        prompt_input("Test message")
    assert exc_info.value.code == 130


@patch("panqake.utils.questionary_prompt.questionary.text")
def test_prompt_input_none_result(mock_text):
    """Test that prompt_input handles None return from questionary (user interrupted)."""
    mock_text.return_value.ask.return_value = None

    with pytest.raises(SystemExit) as exc_info:
        prompt_input("Test message")
    assert exc_info.value.code == 130


@patch("panqake.utils.questionary_prompt.questionary.confirm")
def test_prompt_confirm_keyboard_interrupt(mock_confirm):
    """Test that prompt_confirm handles KeyboardInterrupt properly."""
    mock_confirm.return_value.ask.side_effect = KeyboardInterrupt()

    with pytest.raises(SystemExit) as exc_info:
        prompt_confirm("Test message")
    assert exc_info.value.code == 130


@patch("panqake.utils.questionary_prompt.questionary.confirm")
def test_prompt_confirm_none_result(mock_confirm):
    """Test that prompt_confirm handles None return from questionary."""
    mock_confirm.return_value.ask.return_value = None

    with pytest.raises(SystemExit) as exc_info:
        prompt_confirm("Test message")
    assert exc_info.value.code == 130


@patch("panqake.utils.questionary_prompt.questionary.select")
def test_prompt_select_keyboard_interrupt(mock_select):
    """Test that prompt_select handles KeyboardInterrupt properly."""
    mock_select.return_value.ask.side_effect = KeyboardInterrupt()

    with pytest.raises(SystemExit) as exc_info:
        prompt_select("Test message", ["choice1", "choice2"])
    assert exc_info.value.code == 130


@patch("panqake.utils.questionary_prompt.questionary.select")
def test_prompt_select_none_result(mock_select):
    """Test that prompt_select handles None return from questionary."""
    mock_select.return_value.ask.return_value = None

    with pytest.raises(SystemExit) as exc_info:
        prompt_select("Test message", ["choice1", "choice2"])
    assert exc_info.value.code == 130
