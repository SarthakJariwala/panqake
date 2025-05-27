"""Tests for cli.py module."""

from unittest.mock import patch

import pytest
from typer.testing import CliRunner

from panqake.cli import app, main


@pytest.fixture
def runner():
    """Provide a CLI runner for testing."""
    return CliRunner()


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
def mock_rich():
    """Mock rich printing functions."""
    with (
        patch("panqake.cli.console.print") as mock_print,
        patch("panqake.cli.print_formatted_text") as mock_formatted_print,
    ):
        yield {
            "print": mock_print,
            "formatted_print": mock_formatted_print,
        }


def test_cli_help(runner):
    """Test CLI help text generation."""
    # Use typer's CliRunner to invoke the app with --help
    result = runner.invoke(app, ["--help"])
    
    # Verify exit code is 0 (success)
    assert result.exit_code == 0
    
    # Verify help text contains expected content
    output = result.stdout
    assert "Usage" in output
    assert "Commands" in output or "command" in output.lower()
    assert "Options" in output or "option" in output.lower()
    # Check for some common commands to make sure help text is generated properly
    assert "new" in output
    assert "list" in output


def test_main_not_git_repo(mock_git_utils, mock_config, mock_rich):
    """Test main() when not in a git repository."""
    # Setup
    mock_git_utils["is_repo"].return_value = False

    # Execute
    with pytest.raises(SystemExit) as exc_info:
        main()

    # Verify
    assert exc_info.value.code == 1
    mock_rich["print"].assert_called_once()
    # Check that error message was printed (the exact format with style may vary)
    assert any(
        "Not in a git repository" in str(call)
        for call in mock_rich["print"].call_args_list
    )
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
        # For Typer, we need to patch the app's __call__ method
        with patch("panqake.cli.app") as mock_app:
            # Execute
            main()
            # Verify app was called (standalone mode)
            mock_app.assert_called_once()

    # Verify initialization
    mock_config.assert_called_once()
    mock_git_utils["is_repo"].assert_called_once()
    # Git command should not be called
    assert not mock_git_utils["run_git"].called


def test_main_git_passthrough(mock_git_utils, mock_config, mock_rich):
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
    mock_rich["formatted_print"].assert_called_once_with(
        "[info]Passing command to git...[/info]"
    )
    mock_rich["print"].assert_called_once_with("git command output")


def test_main_git_passthrough_no_output(mock_git_utils, mock_config, mock_rich):
    """Test main() with git command that produces no output."""
    # Setup
    mock_git_utils["is_repo"].return_value = True
    mock_git_utils["run_git"].return_value = None

    with patch("sys.argv", ["panqake", "add", "."]):
        # Execute
        main()

    # Verify command was passed to git but no output was echoed
    mock_git_utils["run_git"].assert_called_once_with(["add", "."])
    mock_rich["formatted_print"].assert_called_once_with(
        "[info]Passing command to git...[/info]"
    )
    # No output to print when git command returns None
    assert mock_rich["print"].call_count == 0


def test_command_registration(runner):
    """Test that all expected commands are registered."""
    # Get registered commands from help output
    result = runner.invoke(app, ["--help"])
    output = result.stdout

    # Check for presence of each command in the help output
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
        "untrack",
        "modify",
        "submit",
        "merge",
        "sync",
        "rename",
        "up",
        "down",
    }

    for cmd in expected_commands:
        assert cmd in output, f"Command '{cmd}' not found in help output"
