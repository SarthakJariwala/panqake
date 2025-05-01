"""Tests for cli.py module."""

import io
from contextlib import redirect_stdout
from unittest.mock import patch

import pytest
import rich_click as click

from panqake.cli import cli, main


@pytest.fixture
def mock_git_utils():
    """Mock git utility functions."""
    with (
        patch("panqake.cli.is_git_repo") as mock_is_repo,
        patch("panqake.cli.run_git_command") as mock_run_git,
    ):
        yield {
            "is_repo": mock_is_repo,
            "run_git": mock_run_git,
        }


@pytest.fixture
def mock_config():
    """Mock config utility functions."""
    with patch("panqake.cli.init_panqake") as mock_init:
        yield mock_init


@pytest.fixture
def mock_click():
    """Mock click utility functions."""
    with (
        patch("rich_click.echo") as mock_echo,
        patch("panqake.cli.print_formatted_text") as mock_print,
    ):
        yield {
            "echo": mock_echo,
            "print": mock_print,
        }


def test_cli_help(mock_click):
    """Test CLI help text generation."""
    # Use redirect_stdout to capture output
    f = io.StringIO()
    try:
        with redirect_stdout(f):
            cli.main(args=["--help"], standalone_mode=False)
    except SystemExit as e:
        assert e.code == 0  # --help should exit cleanly

    # Verify help text was printed to stdout
    output = f.getvalue()
    assert "Usage: " in output
    assert "Panqake - Git Branch Stacking Utility" in output
    assert "Options" in output
    assert "Commands" in output
    # Ensure mocks weren't called unexpectedly (they shouldn't be for help)
    mock_click["echo"].assert_not_called()
    mock_click["print"].assert_not_called()


def test_main_not_git_repo(mock_git_utils, mock_config, mock_click):
    """Test main() when not in a git repository."""
    # Setup
    mock_git_utils["is_repo"].return_value = False

    # Execute
    with pytest.raises(SystemExit) as exc_info:
        main()

    # Verify
    assert exc_info.value.code == 1
    mock_click["echo"].assert_called_once_with("Error: Not in a git repository")
    mock_config.assert_called_once()


def test_main_no_args(mock_git_utils, mock_config):
    """Test main() with no arguments."""
    # Setup
    mock_git_utils["is_repo"].return_value = True
    with patch("sys.argv", ["panqake"]):
        # Execute and expect SystemExit(0) because help is shown
        with pytest.raises(SystemExit) as exc_info:
            main()
        assert exc_info.value.code == 0

    # Help should be shown when no args provided
    mock_config.assert_called_once()
    mock_git_utils["is_repo"].assert_called_once()


def test_main_known_command(mock_git_utils, mock_config):
    """Test main() with a known panqake command."""
    # Setup
    mock_git_utils["is_repo"].return_value = True
    with patch("sys.argv", ["panqake", "list"]):
        # Execute
        main()

    # Verify panqake command was handled
    mock_config.assert_called_once()
    mock_git_utils["is_repo"].assert_called_once()
    assert not mock_git_utils["run_git"].called


def test_main_git_passthrough(mock_git_utils, mock_config, mock_click):
    """Test main() with unknown command passed to git."""
    # Setup
    mock_git_utils["is_repo"].return_value = True
    mock_git_utils["run_git"].return_value = "git command output"

    with patch("sys.argv", ["panqake", "status"]):
        # Execute
        main()

    # Verify command was passed to git
    mock_config.assert_called_once()
    mock_git_utils["is_repo"].assert_called_once()
    mock_git_utils["run_git"].assert_called_once_with(["status"])
    mock_click["print"].assert_called_once_with(
        "[info]Passing command to git...[/info]"
    )
    mock_click["echo"].assert_called_once_with("git command output")


def test_main_git_passthrough_no_output(mock_git_utils, mock_config, mock_click):
    """Test main() with git command that produces no output."""
    # Setup
    mock_git_utils["is_repo"].return_value = True
    mock_git_utils["run_git"].return_value = None

    with patch("sys.argv", ["panqake", "add", "."]):
        # Execute
        main()

    # Verify command was passed to git but no output was echoed
    mock_git_utils["run_git"].assert_called_once_with(["add", "."])
    mock_click["print"].assert_called_once_with(
        "[info]Passing command to git...[/info]"
    )
    assert not mock_click["echo"].called


def test_command_registration():
    """Test that all expected commands are registered."""
    # Get all registered command names
    commands = cli.list_commands(ctx=None)

    # Verify all expected commands are present
    expected_commands = {
        "new",
        "list",
        "ls",
        "update",
        "delete",
        "pr",
        "switch",
        "co",
        "track",
        "modify",
        "submit",
        "merge",
        "sync",
    }

    assert set(commands) == expected_commands


def test_command_help_texts():
    """Test that all commands have help text."""
    ctx = click.Context(cli)

    for cmd_name in cli.list_commands(ctx):
        cmd = cli.get_command(ctx, cmd_name)
        assert cmd.help is not None, f"Command '{cmd_name}' is missing help text"
