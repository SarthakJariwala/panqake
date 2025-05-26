"""Tests for cli.py module."""

from unittest.mock import patch

import pytest
from typer.testing import CliRunner

from panqake.cli import app, main

runner = CliRunner()


@pytest.fixture
def mock_git_utils():
    """Mock git utility functions."""
    with (
        patch("panqake.cli.is_git_repo", return_value=True) as mock_is_repo,
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
def mock_console_print():
    """Mocks console.print and panqake.cli.print_formatted_text."""
    with (
        patch("panqake.cli.console.print") as mock_rich_print,
        patch("panqake.cli.print_formatted_text") as mock_custom_print,
    ):
        yield {
            "rich_print": mock_rich_print,
            "custom_print": mock_custom_print,
        }


def test_cli_help(mock_console_print):
    """Test CLI help text generation."""
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    # Check for 'Usage:' which may include ANSI color codes
    assert "Usage" in result.stdout
    assert "Panqake - Git Branch Stacking Utility" in result.stdout
    # Options and Commands may include color codes too, so simplify the check
    assert "Options" in result.stdout or "option" in result.stdout.lower()
    # Typer groups commands under "Commands" or lists them if no groups.
    # With a flat structure, all commands are listed under "Commands".
    assert "Commands" in result.stdout or "command" in result.stdout.lower()
    # Check for a sample of commands that should now be top-level
    assert "new" in result.stdout
    assert "list" in result.stdout
    assert "update" in result.stdout
    # Ensure mocks weren't called unexpectedly (they shouldn't be for help by default)
    mock_console_print["rich_print"].assert_not_called()
    mock_console_print["custom_print"].assert_not_called()


def test_main_not_git_repo(mock_git_utils, mock_config, mock_console_print):
    """Test main() when not in a git repository."""
    # Setup
    mock_git_utils["is_repo"].return_value = False

    # Execute
    # We call main directly here because CliRunner(app) would not include the initial is_git_repo check
    # that happens in main() before app() is called.
    with patch("sys.argv", ["panqake"]), pytest.raises(SystemExit) as exc_info:
        main()

    # Verify
    assert exc_info.value.code == 1
    mock_console_print["rich_print"].assert_called_once_with(
        "Error: Not in a git repository"
    )
    mock_config.assert_called_once()


def test_main_no_args(mock_git_utils, mock_config):
    """Test main() with no arguments (shows help)."""
    # Setup
    mock_git_utils["is_repo"].return_value = True  # Ensure git repo check passes

    # patch sys.argv for the main() call.
    # We expect main() to call app(), which for no args, shows help and exits.
    with patch("sys.argv", ["panqake"]), pytest.raises(SystemExit):
        main()

    # After main() runs, init_panqake and is_git_repo should have been called.
    mock_config.assert_called_once()
    mock_git_utils["is_repo"].assert_called_once()


def test_main_known_command(mock_git_utils, mock_config):
    """Test main() with a known panqake command."""
    # Setup
    mock_git_utils["is_repo"].return_value = True

    # Patch sys.argv to simulate command line arguments for main().
    # Mock the actual command function (list_branches) that would be called by Typer app.
    # Expect main() to call app(), which then dispatches to the command.
    # The command itself (list_branches) is mocked to prevent full execution.
    # app() will likely cause a SystemExit.
    # The list_branches function is imported into panqake.cli module,
    # so we need to patch it there.
    with (
        patch("sys.argv", ["panqake", "list"]),
        patch(  # Changed from "nav", "list"
            "panqake.cli.list_branches"
        ) as mock_list_branches_func,
        pytest.raises(SystemExit),
    ):
        main()

    # init_panqake and is_git_repo are called by main()
    mock_config.assert_called_once()
    mock_git_utils["is_repo"].assert_called_once()
    # Check that the intended command's underlying function was called by the app.
    mock_list_branches_func.assert_called_once()


def test_main_git_passthrough(mock_git_utils, mock_config, mock_console_print):
    """Test main() with unknown command passed to git."""
    # Setup
    mock_git_utils["is_repo"].return_value = True
    mock_git_utils["run_git"].return_value = "git command output"

    # We need to call main() directly to test the passthrough logic in main()
    with patch("sys.argv", ["panqake", "status"]):
        main()

    # Verify command was passed to git
    mock_config.assert_called_once()
    mock_git_utils["is_repo"].assert_called_once()
    mock_git_utils["run_git"].assert_called_once_with(["status"])
    mock_console_print["custom_print"].assert_called_once_with(
        "[info]Passing command to git...[/info]"
    )
    mock_console_print["rich_print"].assert_called_once_with("git command output")


def test_main_git_passthrough_no_output(
    mock_git_utils, mock_config, mock_console_print
):
    """Test main() with git command that produces no output."""
    # Setup
    mock_git_utils["is_repo"].return_value = True
    mock_git_utils["run_git"].return_value = None

    with patch("sys.argv", ["panqake", "add", "."]):
        main()

    # Verify command was passed to git but no output was echoed
    mock_git_utils["run_git"].assert_called_once_with(["add", "."])
    mock_console_print["custom_print"].assert_called_once_with(
        "[info]Passing command to git...[/info]"
    )
    mock_console_print["rich_print"].assert_not_called()


def test_command_registration_and_help_texts():
    """Test that all expected commands are registered and have help text."""
    # Expected top-level commands and their short help texts (from @app.command(help="..."))
    expected_commands = {
        "list": "List the branch stack.",
        "new": "Create a new branch in the stack.",
        "ls": "Alias for 'list' - List the branch stack.",
        "update": "Update branches after changes and push to remote.",
        "delete": "Delete a branch and relink the stack.",
        "pr": "Create PRs for the branch stack.",
        "switch": "Interactively switch between branches.",
        "co": "Alias for 'switch' - Interactively switch between branches.",
        "track": "Track an existing Git branch in the panqake stack.",
        "untrack": "Untrack a branch (does not delete git branch).",
        "modify": "Modify/amend the current commit or create a new one.",
        "submit": "Update remote branch and PR after changes.",
        "merge": "Merge a PR and manage the branch stack after merge.",
        "sync": "Sync branches with remote repository changes.",
        "rename": "Rename a branch while maintaining stack relationships.",
        "up": "Navigate to the parent branch in the stack.",
        "down": "Navigate to a child branch in the stack.",
    }

    # Check top-level app help for command registration and short help texts
    result_app_help = runner.invoke(app, ["--help"])
    assert result_app_help.exit_code == 0
    for cmd_name, short_help in expected_commands.items():
        assert cmd_name in result_app_help.stdout
        assert short_help in result_app_help.stdout

    # Check each command's own help page
    for cmd_name in expected_commands:
        result_cmd_help = runner.invoke(app, [cmd_name, "--help"])
        assert result_cmd_help.exit_code == 0, (
            f"Failed to get help for command '{cmd_name}'. "
            f"Output: {result_cmd_help.stdout}"
        )
        # Basic check that help text is not empty or just usage
        assert cmd_name in result_cmd_help.stdout
        assert "Usage:" in result_cmd_help.stdout
        # Check if the short help is also present in the command's own help output (Typer usually includes it)
        # This might be part of the docstring which Typer displays.
        # For example, if @app.command(help="Short help.") and docstring is "Longer help.",
        # Typer shows "Short help. Longer help." or similar.
        # A simple check for the short help text is reasonable.
        assert expected_commands[cmd_name] in result_cmd_help.stdout
