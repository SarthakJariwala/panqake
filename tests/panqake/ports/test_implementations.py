"""Tests for concrete port implementations."""

import pytest

from panqake.ports import JsonUI, PRJsonUI, RealGit, RealGitHub, RealUI
from panqake.ports.exceptions import NonInteractiveError, PRCreationError
from panqake.ports.protocols import UIPort
from panqake.ports.results import PRAttachment
from panqake.utils.github import CreatePRAttempt


def test_json_ui_prompt_confirm_raises_non_interactive_error():
    ui = JsonUI()

    with pytest.raises(NonInteractiveError, match="confirmation"):
        ui.prompt_confirm("Proceed?", default=True)


class TestRealGit:
    """Tests for RealGit command construction."""

    def test_rebase_onto_disables_git_update_refs(self, monkeypatch):
        """Panqake rebases descendants itself, so Git must not auto-move refs."""
        calls: list[tuple[list[str], dict[str, object]]] = []

        def fake_run_git_command(command, **kwargs):
            calls.append((command, kwargs))
            return ""

        monkeypatch.setattr("panqake.utils.git.run_git_command", fake_run_git_command)

        RealGit().rebase_onto("feature", "main", upstream="old-feature")

        assert calls == [
            (["checkout", "feature"], {"silent_fail": True}),
            (
                [
                    "-c",
                    "rebase.updateRefs=false",
                    "rebase",
                    "--autostash",
                    "--onto",
                    "main",
                    "old-feature",
                ],
                {"silent_fail": True},
            ),
        ]

    def test_rebase_onto_in_worktree_disables_git_update_refs(self, monkeypatch):
        """Worktree rebases must also opt out of Git's auto ref updates."""
        calls: list[tuple[str, list[str]]] = []

        def fake_run_git_command_for_branch_context(branch, command, **kwargs):
            calls.append((branch, command))
            return ""

        monkeypatch.setattr(
            "panqake.utils.git.run_git_command_for_branch_context",
            fake_run_git_command_for_branch_context,
        )

        RealGit().rebase_onto_in_worktree("feature", "main", upstream="old-feature")

        assert calls == [
            (
                "feature",
                [
                    "-c",
                    "rebase.updateRefs=false",
                    "rebase",
                    "--autostash",
                    "--onto",
                    "main",
                    "old-feature",
                ],
            )
        ]


class TestRuntimeCheckable:
    """Verify that implementations satisfy the runtime_checkable protocols."""

    def test_real_ui_is_ui_port(self):
        assert isinstance(RealUI(), UIPort)

    def test_json_ui_is_ui_port(self):
        assert isinstance(JsonUI(), UIPort)

    def test_pr_json_ui_is_ui_port(self):
        assert isinstance(PRJsonUI(), UIPort)


class TestPRJsonUI:
    """Tests for PRJsonUI behavior."""

    def test_prompt_input_returns_default(self):
        ui = PRJsonUI()
        assert ui.prompt_input("Title:", default="my-title") == "my-title"

    def test_prompt_input_multiline_returns_default(self):
        ui = PRJsonUI()
        assert ui.prompt_input_multiline("Body:", default="body") == "body"

    def test_prompt_confirm_approves_create_pr(self):
        ui = PRJsonUI()
        assert ui.prompt_confirm("Create this pull request?") is True

    def test_prompt_confirm_rejects_other_prompts(self):
        ui = PRJsonUI()
        assert ui.prompt_confirm("Push to remote?") is False

    def test_prompt_select_reviewers_returns_empty(self):
        ui = PRJsonUI()
        assert ui.prompt_select_reviewers(["alice", "bob"]) == []

    def test_print_methods_are_noops(self):
        ui = PRJsonUI()
        ui.print_success("ok")
        ui.print_error("err")
        ui.print_info("info")
        ui.print_muted("muted")


class TestRealGitHub:
    def test_create_pr_includes_stderr(self, monkeypatch):
        monkeypatch.setattr(
            "panqake.utils.github.create_pr",
            lambda *args, **kwargs: CreatePRAttempt(
                False, None, "GraphQL: Resource not accessible\n"
            ),
        )
        with pytest.raises(PRCreationError, match="Resource not accessible"):
            RealGitHub().create_pr("main", "feature", "Title")

    def test_create_pr_hints_unknown_attach_flag(self, monkeypatch):
        monkeypatch.setattr(
            "panqake.utils.github.create_pr",
            lambda *args, **kwargs: CreatePRAttempt(
                False, None, "unknown flag: --attach\n"
            ),
        )
        with pytest.raises(PRCreationError, match="2.99.0"):
            RealGitHub().create_pr(
                "main",
                "feature",
                "Title",
                attachments=[PRAttachment(path="./login.png")],
            )

    def test_create_pr_skips_version_hint_for_other_attach_failures(self, monkeypatch):
        monkeypatch.setattr(
            "panqake.utils.github.create_pr",
            lambda *args, **kwargs: CreatePRAttempt(
                False, None, "failed to upload --attach ./login.png\n"
            ),
        )
        with pytest.raises(PRCreationError) as error:
            RealGitHub().create_pr(
                "main",
                "feature",
                "Title",
                attachments=[PRAttachment(path="./login.png")],
            )
        assert "2.99.0" not in str(error.value)
