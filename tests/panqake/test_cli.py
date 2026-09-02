"""Tests for cli.py module."""

import json
from unittest.mock import call, patch

import pytest
from click import unstyle
from typer.testing import CliRunner

from panqake.cli import app, main
from panqake.ports.results import PRAttachment


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
    output = unstyle(result.stdout)
    assert "Usage" in output
    assert "Commands" in output or "command" in output.lower()
    assert "Options" in output or "option" in output.lower()
    # Check for some common commands to make sure help text is generated properly
    assert "new" in output
    assert "list" in output
    assert "Examples" in output
    assert "pq <command> --help" in output


@pytest.mark.parametrize(
    "command",
    [
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
        "move",
        "reparent",
        "up",
        "down",
    ],
)
def test_command_help_includes_copy_pasteable_examples(runner, command):
    """Every command should expose examples through layered help."""
    result = runner.invoke(app, [command, "--help"])

    assert result.exit_code == 0
    assert "Examples" in result.stdout
    assert f"pq {command}" in result.stdout


def test_main_not_git_repo(mock_git_utils, mock_config, mock_rich):
    """Test main() when not in a git repository."""
    # Setup
    mock_git_utils["is_repo"].return_value = False

    # Execute
    with patch("sys.argv", ["panqake", "list"]):
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
    mock_git_utils["is_repo"].assert_called_once()
    mock_git_utils["run_git"].assert_not_called()


def test_main_not_git_repo_json_mode(mock_git_utils, mock_config, mock_rich, capsys):
    """Test main() emits a JSON error envelope for startup failures in --json mode."""
    mock_git_utils["run_git"].return_value = None

    with patch("sys.argv", ["panqake", "list", "--json"]):
        with pytest.raises(SystemExit) as exc_info:
            main()

    assert exc_info.value.code == 1
    mock_config.assert_called_once()
    mock_git_utils["run_git"].assert_called_once_with(
        ["rev-parse", "--is-inside-work-tree"],
        silent_fail=True,
    )
    mock_git_utils["is_repo"].assert_not_called()
    mock_rich["print"].assert_not_called()
    mock_rich["formatted_print"].assert_not_called()

    payload = json.loads(capsys.readouterr().out)
    assert payload["ok"] is False
    assert payload["command"] == "list"
    assert payload["error"]["type"] == "GitOperationError"
    assert payload["error"]["message"] == "Not in a git repository"
    assert payload["error"]["exit_code"] == 1


def test_main_no_args(mock_git_utils, mock_config):
    """Help with no arguments should not require or initialize a repository."""
    with patch("sys.argv", ["panqake"]):
        with pytest.raises(SystemExit) as exc_info:
            main()
        assert exc_info.value.code == 0

    mock_config.assert_not_called()
    mock_git_utils["is_repo"].assert_not_called()
    mock_git_utils["run_git"].assert_not_called()


def test_main_subcommand_help_skips_repository_check(mock_git_utils, mock_config):
    """Layered help should work outside a Git repository."""
    with patch("sys.argv", ["panqake", "track", "--help"]):
        with pytest.raises(SystemExit) as exc_info:
            main()
        assert exc_info.value.code == 0

    mock_config.assert_not_called()
    mock_git_utils["is_repo"].assert_not_called()
    mock_git_utils["run_git"].assert_not_called()


def test_main_completion_option_skips_repository_check(mock_git_utils, mock_config):
    """Shell completion discovery should work outside a Git repository."""
    with (
        patch("sys.argv", ["panqake", "--show-completion"]),
        patch("panqake.cli.app") as mock_app,
    ):
        main()

    mock_app.assert_called_once_with(["--show-completion"])
    mock_config.assert_not_called()
    mock_git_utils["is_repo"].assert_not_called()
    mock_git_utils["run_git"].assert_not_called()


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


def test_main_known_command_with_leading_option(mock_git_utils, mock_config):
    """Leading options should not break panqake command dispatch."""
    mock_git_utils["run_git"].return_value = "true"

    with patch("sys.argv", ["panqake", "--json", "list"]):
        with patch("panqake.cli.app") as mock_app:
            main()
            mock_app.assert_called_once_with(["list", "--json"])

    mock_git_utils["run_git"].assert_called_once_with(
        ["rev-parse", "--is-inside-work-tree"],
        silent_fail=True,
    )


def test_main_unknown_command_with_leading_option_goes_to_git(
    mock_git_utils, mock_config, mock_rich
):
    """Unknown commands still pass through even with leading options."""
    mock_git_utils["run_git"].side_effect = ["true", "git output"]

    with patch("sys.argv", ["panqake", "--json", "status"]):
        main()

    mock_git_utils["run_git"].assert_has_calls(
        [
            call(["rev-parse", "--is-inside-work-tree"], silent_fail=True),
            call(["--json", "status"]),
        ]
    )
    assert mock_git_utils["run_git"].call_count == 2
    mock_rich["formatted_print"].assert_called_once_with(
        "[info]Passing command to git...[/info]"
    )


def test_main_git_passthrough_with_option_argument_not_treated_as_command(
    mock_git_utils, mock_config, mock_rich
):
    """Option arguments matching command names should still route to git."""
    mock_git_utils["is_repo"].return_value = True
    mock_git_utils["run_git"].return_value = "git output"

    with patch("sys.argv", ["panqake", "-C", "list", "status"]):
        with patch("panqake.cli.app") as mock_app:
            main()
            mock_app.assert_not_called()

    mock_config.assert_called_once()
    mock_git_utils["is_repo"].assert_called_once()
    mock_git_utils["run_git"].assert_called_once_with(["-C", "list", "status"])
    mock_rich["formatted_print"].assert_called_once_with(
        "[info]Passing command to git...[/info]"
    )


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


def test_pr_command_with_draft_flag(runner):
    """Test PR command with draft flag."""
    with patch("panqake.cli.create_pull_requests") as mock_create_prs:
        result = runner.invoke(app, ["pr", "--draft"])

        assert result.exit_code == 0
        mock_create_prs.assert_called_once_with(
            None,
            draft=True,
            push=None,
            title=None,
            body=None,
            reviewers=None,
            use_defaults=False,
            assume_yes=False,
            attachments=None,
            json_output=False,
        )


def test_pr_command_with_branch_and_draft(runner):
    """Test PR command with branch name and draft flag."""
    with patch("panqake.cli.create_pull_requests") as mock_create_prs:
        result = runner.invoke(app, ["pr", "feature-branch", "--draft"])

        assert result.exit_code == 0
        mock_create_prs.assert_called_once_with(
            "feature-branch",
            draft=True,
            push=None,
            title=None,
            body=None,
            reviewers=None,
            use_defaults=False,
            assume_yes=False,
            attachments=None,
            json_output=False,
        )


def test_pr_command_without_draft_flag(runner):
    """Test PR command without draft flag."""
    with patch("panqake.cli.create_pull_requests") as mock_create_prs:
        result = runner.invoke(app, ["pr"])

        assert result.exit_code == 0
        mock_create_prs.assert_called_once_with(
            None,
            draft=None,
            push=None,
            title=None,
            body=None,
            reviewers=None,
            use_defaults=False,
            assume_yes=False,
            attachments=None,
            json_output=False,
        )


def test_pr_command_accepts_all_prompt_inputs(runner):
    """PR creation decisions should all have a non-interactive CLI path."""
    with patch("panqake.cli.create_pull_requests") as mock_create_prs:
        result = runner.invoke(
            app,
            [
                "pr",
                "feature-branch",
                "--push",
                "--no-draft",
                "--title",
                "Add authentication",
                "--body",
                "Implements login support",
                "--reviewer",
                "alice",
                "--reviewer",
                "bob",
                "--defaults",
                "--yes",
                "--json",
            ],
        )

    assert result.exit_code == 0
    mock_create_prs.assert_called_once_with(
        "feature-branch",
        draft=False,
        push=True,
        title="Add authentication",
        body="Implements login support",
        reviewers=["alice", "bob"],
        use_defaults=True,
        assume_yes=True,
        attachments=None,
        json_output=True,
    )


def test_pr_command_reads_body_from_stdin_and_skips_reviewers(runner):
    """A PR body can be piped without triggering reviewer selection."""
    with patch("panqake.cli.create_pull_requests") as mock_create_prs:
        result = runner.invoke(
            app,
            ["pr", "feature-branch", "--body-file", "-", "--no-reviewers"],
            input="Body from stdin\n",
        )

    assert result.exit_code == 0
    assert mock_create_prs.call_args.kwargs["body"] == "Body from stdin\n"
    assert mock_create_prs.call_args.kwargs["reviewers"] == []


def test_pr_command_forwards_attach_flags(runner, tmp_path):
    shot = tmp_path / "login.png"
    shot.write_bytes(b"\x89PNG\r\n\x1a\n")
    after = tmp_path / "after.png"
    after.write_bytes(b"\x89PNG\r\n\x1a\n")

    with patch("panqake.cli.create_pull_requests") as mock_create_prs:
        result = runner.invoke(
            app,
            [
                "pr",
                "feature-branch",
                "--attach",
                f"{shot}#The login error state",
                "--attach",
                str(after),
            ],
        )

    assert result.exit_code == 0
    assert mock_create_prs.call_args.kwargs["attachments"] == [
        PRAttachment(path=str(shot), alt_text="The login error state"),
        PRAttachment(path=str(after), alt_text=None),
    ]


def test_pr_command_keeps_relative_attach_spelling(runner, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    shot = tmp_path / "login.png"
    shot.write_bytes(b"\x89PNG\r\n\x1a\n")

    with patch("panqake.cli.create_pull_requests") as mock_create_prs:
        result = runner.invoke(
            app, ["pr", "feature-branch", "--attach", "./login.png"]
        )

    assert result.exit_code == 0
    assert mock_create_prs.call_args.kwargs["attachments"] == [
        PRAttachment(path="./login.png", alt_text=None)
    ]


def test_pr_command_rejects_missing_attachment(runner, tmp_path):
    missing = tmp_path / "nope.png"
    result = runner.invoke(app, ["pr", "feature-branch", "--attach", str(missing)])

    assert result.exit_code == 2
    assert "not a file" in unstyle(result.output)


def test_pr_command_rejects_duplicate_attachments(runner, tmp_path):
    shot = tmp_path / "login.png"
    shot.write_bytes(b"\x89PNG\r\n\x1a\n")
    result = runner.invoke(
        app,
        ["pr", "feature-branch", "--attach", str(shot), "--attach", str(shot)],
    )

    assert result.exit_code == 2
    assert "same file twice" in unstyle(result.output)


def test_pr_command_rejects_too_many_attachments(runner, tmp_path):
    args = ["pr", "feature-branch"]
    for index in range(51):
        path = tmp_path / f"shot-{index}.png"
        path.write_bytes(b"\x89PNG\r\n\x1a\n")
        args.extend(["--attach", str(path)])

    result = runner.invoke(app, args)

    assert result.exit_code == 2
    assert "cannot attach more than 50 files" in unstyle(result.output)


def test_submit_command_forwards_attach_flags(runner, tmp_path):
    shot = tmp_path / "login.png"
    shot.write_bytes(b"\x89PNG\r\n\x1a\n")

    with patch("panqake.cli.update_pull_request") as mock_submit:
        result = runner.invoke(
            app,
            ["submit", "feature-branch", "--create-pr", "--attach", str(shot)],
        )

    assert result.exit_code == 0
    assert mock_submit.call_args.kwargs["attachments"] == [
        PRAttachment(path=str(shot), alt_text=None)
    ]


@pytest.mark.parametrize(
    "options",
    [
        ["--body", "inline", "--body-file", "body.md"],
        ["--reviewer", "alice", "--no-reviewers"],
    ],
)
def test_pr_command_rejects_conflicting_non_interactive_inputs(runner, options):
    result = runner.invoke(app, ["pr", "feature-branch", *options])

    assert result.exit_code == 2


def test_delete_command_with_yes_flag(runner):
    """Test delete command with explicit confirmation override."""
    with patch("panqake.cli.delete_branch") as mock_delete:
        result = runner.invoke(app, ["delete", "feature-branch", "--yes"])

        assert result.exit_code == 0
        mock_delete.assert_called_once_with(
            "feature-branch", assume_yes=True, json_output=False
        )


def test_update_command_with_yes_flag(runner):
    """Test update command with explicit confirmation override."""
    with patch("panqake.cli.update_branches") as mock_update:
        result = runner.invoke(app, ["update", "feature-branch", "--yes"])

        assert result.exit_code == 0
        mock_update.assert_called_once_with(
            "feature-branch",
            skip_push=False,
            assume_yes=True,
            json_output=False,
        )


def test_track_command_with_parent_flag(runner):
    """Track accepts an explicit parent for non-interactive use."""
    with patch("panqake.cli.track") as mock_track:
        result = runner.invoke(
            app,
            ["track", "feature-branch", "--parent", "main", "--json"],
        )

        assert result.exit_code == 0
        mock_track.assert_called_once_with(
            "feature-branch", parent_branch="main", json_output=True
        )


def test_modify_command_accepts_explicit_files(runner):
    """Modify forwards repeatable file selection without prompting."""
    with patch("panqake.cli.modify_commit") as mock_modify:
        result = runner.invoke(
            app,
            [
                "modify",
                "--file",
                "src/a.py",
                "--file",
                "src/b.py",
                "--message",
                "Update files",
                "--json",
            ],
        )

    assert result.exit_code == 0
    mock_modify.assert_called_once_with(
        False,
        "Update files",
        no_amend=False,
        selected_files=["src/a.py", "src/b.py"],
        stage_all=False,
        json_output=True,
    )


def test_modify_command_accepts_staged_only(runner):
    """Modify can leave all unstaged paths untouched without prompting."""
    with patch("panqake.cli.modify_commit") as mock_modify:
        result = runner.invoke(
            app,
            ["modify", "--staged-only", "--message", "Update staged", "--json"],
        )

    assert result.exit_code == 0
    mock_modify.assert_called_once_with(
        False,
        "Update staged",
        no_amend=False,
        selected_files=[],
        stage_all=False,
        json_output=True,
    )


@pytest.mark.parametrize(
    "options",
    [
        ["--all", "--file", "src/a.py"],
        ["--staged-only", "--file", "src/a.py"],
        ["--staged-only", "--all"],
    ],
)
def test_modify_command_rejects_conflicting_staging_modes(runner, options):
    result = runner.invoke(app, ["modify", *options])

    assert result.exit_code == 2
    assert "cannot be combined" in result.stderr


def test_down_command_accepts_explicit_child(runner):
    """Down forwards a child branch for ambiguous stacks."""
    with patch("panqake.cli.down_command") as mock_down:
        result = runner.invoke(app, ["down", "feature-b", "--json"])

    assert result.exit_code == 0
    mock_down.assert_called_once_with("feature-b", json_output=True)


def test_submit_command_with_create_pr_flag(runner):
    """Test submit command with explicit PR creation behavior."""
    with patch("panqake.cli.update_pull_request") as mock_submit:
        result = runner.invoke(app, ["submit", "feature-branch", "--create-pr"])

        assert result.exit_code == 0
        mock_submit.assert_called_once_with(
            "feature-branch",
            create_pr=True,
            draft=None,
            push=None,
            title=None,
            body=None,
            reviewers=None,
            use_defaults=False,
            assume_yes=False,
            attachments=None,
            json_output=False,
        )


def test_submit_command_with_no_create_pr_flag(runner):
    """Test submit command with explicit PR non-creation behavior."""
    with patch("panqake.cli.update_pull_request") as mock_submit:
        result = runner.invoke(app, ["submit", "feature-branch", "--no-create-pr"])

        assert result.exit_code == 0
        mock_submit.assert_called_once_with(
            "feature-branch",
            create_pr=False,
            draft=None,
            push=None,
            title=None,
            body=None,
            reviewers=None,
            use_defaults=False,
            assume_yes=False,
            attachments=None,
            json_output=False,
        )


def test_submit_command_accepts_new_pr_inputs(runner):
    """Submit exposes metadata for its nested PR creation path."""
    with patch("panqake.cli.update_pull_request") as mock_submit:
        result = runner.invoke(
            app,
            [
                "submit",
                "feature-branch",
                "--create-pr",
                "--push",
                "--draft",
                "--title",
                "Add authentication",
                "--body",
                "Implements login support",
                "--reviewer",
                "alice",
                "--defaults",
                "--yes",
                "--json",
            ],
        )

    assert result.exit_code == 0
    mock_submit.assert_called_once_with(
        "feature-branch",
        create_pr=True,
        draft=True,
        push=True,
        title="Add authentication",
        body="Implements login support",
        reviewers=["alice"],
        use_defaults=True,
        assume_yes=True,
        attachments=None,
        json_output=True,
    )


def test_merge_command_with_allow_failed_checks_flag(runner):
    """Test merge command with failed-check override."""
    with patch("panqake.cli.merge_branch") as mock_merge:
        result = runner.invoke(
            app, ["merge", "feature-branch", "--allow-failed-checks"]
        )

        assert result.exit_code == 0
        mock_merge.assert_called_once_with(
            "feature-branch",
            True,
            True,
            allow_failed_checks=True,
            assume_yes=False,
            method=None,
            json_output=False,
        )


def test_merge_command_with_yes_flag(runner):
    """Test merge command with explicit confirmation override."""
    with patch("panqake.cli.merge_branch") as mock_merge:
        result = runner.invoke(app, ["merge", "feature-branch", "--yes"])

        assert result.exit_code == 0
        mock_merge.assert_called_once_with(
            "feature-branch",
            True,
            True,
            allow_failed_checks=False,
            assume_yes=True,
            method=None,
            json_output=False,
        )


def test_merge_command_with_method_flag(runner):
    """Test merge command with explicit merge method."""
    with patch("panqake.cli.merge_branch") as mock_merge:
        result = runner.invoke(app, ["merge", "feature-branch", "--method", "rebase"])

        assert result.exit_code == 0
        mock_merge.assert_called_once_with(
            "feature-branch",
            True,
            True,
            allow_failed_checks=False,
            assume_yes=False,
            method="rebase",
            json_output=False,
        )


def test_sync_command_with_delete_merged_flag(runner):
    """Test sync command with merged-branch deletion override."""
    with patch("panqake.cli.sync_with_remote") as mock_sync:
        result = runner.invoke(app, ["sync", "--delete-merged"])

        assert result.exit_code == 0
        mock_sync.assert_called_once_with(
            "main",
            skip_push=False,
            delete_merged=True,
            json_output=False,
        )
