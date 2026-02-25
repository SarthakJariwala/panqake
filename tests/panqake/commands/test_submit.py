"""Tests for submit command using the ports/fakes testing architecture."""

import json

import pytest

from panqake.commands.submit import submit_branch_core, update_pull_request
from panqake.ports import (
    BranchNotFoundError,
    GitHubCLINotFoundError,
    PushError,
    UserCancelledError,
)
from panqake.testing.fakes import FakeConfig, FakeGit, FakeGitHub, FakeUI


class TestSubmitBranchCore:
    """Test submit_branch_core with fakes."""

    def test_pushes_branch_to_remote(self):
        """Should push branch to remote."""
        git = FakeGit(current_branch="feature-x", branches=["main", "feature-x"])
        github = FakeGitHub(branches_with_pr={"feature-x"})
        config = FakeConfig(stack={"feature-x": {"parent": "main"}})
        ui = FakeUI(strict=False)

        result = submit_branch_core(
            git=git, github=github, config=config, ui=ui, branch_name="feature-x"
        )

        assert result.branch_name == "feature-x"
        assert len(git.push_calls) == 1
        assert git.push_calls[0] == ("feature-x", False)

    def test_uses_current_branch_when_none_specified(self):
        """Should use current branch if branch_name is None."""
        git = FakeGit(current_branch="feature-y", branches=["main", "feature-y"])
        github = FakeGitHub(branches_with_pr={"feature-y"})
        config = FakeConfig()
        ui = FakeUI(strict=False)

        result = submit_branch_core(git=git, github=github, config=config, ui=ui)

        assert result.branch_name == "feature-y"
        assert git.push_calls[0][0] == "feature-y"

    def test_force_push_when_commit_amended(self):
        """Should use force-with-lease when last commit was amended."""
        git = FakeGit(
            current_branch="feature-x",
            branches=["main", "feature-x"],
            last_commit_amended=True,
        )
        github = FakeGitHub(branches_with_pr={"feature-x"})
        config = FakeConfig()
        ui = FakeUI(strict=False)

        result = submit_branch_core(
            git=git, github=github, config=config, ui=ui, branch_name="feature-x"
        )

        assert result.force_pushed is True
        assert git.push_calls[0] == ("feature-x", True)

    def test_force_push_when_non_fast_forward(self):
        """Should use force-with-lease when non-fast-forward is detected."""
        git = FakeGit(
            current_branch="feature-x",
            branches=["main", "feature-x"],
            force_push_needed={"feature-x": True},
        )
        github = FakeGitHub(branches_with_pr={"feature-x"})
        config = FakeConfig()
        ui = FakeUI(strict=False)

        result = submit_branch_core(
            git=git, github=github, config=config, ui=ui, branch_name="feature-x"
        )

        assert result.force_pushed is True
        assert git.push_calls[0] == ("feature-x", True)
        assert any("force" in msg.lower() for msg in ui.info_messages)

    def test_returns_pr_url_when_pr_exists(self):
        """Should return existing PR URL."""
        git = FakeGit(current_branch="feature-x", branches=["main", "feature-x"])
        github = FakeGitHub(
            branches_with_pr={"feature-x"},
            pr_urls={"feature-x": "https://github.com/org/repo/pull/42"},
        )
        config = FakeConfig()
        ui = FakeUI(strict=False)

        result = submit_branch_core(
            git=git, github=github, config=config, ui=ui, branch_name="feature-x"
        )

        assert result.pr_existed is True
        assert result.pr_created is False
        assert result.pr_url == "https://github.com/org/repo/pull/42"

    def test_prompts_to_create_pr_when_none_exists(self):
        """Should prompt user to create PR when none exists."""
        git = FakeGit(current_branch="feature-x", branches=["main", "feature-x"])
        github = FakeGitHub()
        config = FakeConfig()
        ui = FakeUI(confirm_responses=[True], strict=False)

        result = submit_branch_core(
            git=git, github=github, config=config, ui=ui, branch_name="feature-x"
        )

        assert result.pr_existed is False
        assert result.pr_created is True
        assert len(ui.confirm_calls) == 1

    def test_no_pr_created_when_user_declines(self):
        """Should not create PR when user declines."""
        git = FakeGit(current_branch="feature-x", branches=["main", "feature-x"])
        github = FakeGitHub()
        config = FakeConfig()
        ui = FakeUI(confirm_responses=[False], strict=False)

        result = submit_branch_core(
            git=git, github=github, config=config, ui=ui, branch_name="feature-x"
        )

        assert result.pr_existed is False
        assert result.pr_created is False

    def test_create_pr_override_true_skips_prompt(self):
        """Should set pr_created without prompting when create_pr=True."""
        git = FakeGit(current_branch="feature-x", branches=["main", "feature-x"])
        github = FakeGitHub()
        config = FakeConfig()
        ui = FakeUI(strict=False)

        result = submit_branch_core(
            git=git,
            github=github,
            config=config,
            ui=ui,
            branch_name="feature-x",
            create_pr=True,
        )

        assert result.pr_created is True
        assert ui.confirm_calls == []

    def test_create_pr_override_false_skips_prompt(self):
        """Should skip PR creation without prompting when create_pr=False."""
        git = FakeGit(current_branch="feature-x", branches=["main", "feature-x"])
        github = FakeGitHub()
        config = FakeConfig()
        ui = FakeUI(strict=False)

        result = submit_branch_core(
            git=git,
            github=github,
            config=config,
            ui=ui,
            branch_name="feature-x",
            create_pr=False,
        )

        assert result.pr_created is False
        assert ui.confirm_calls == []

    def test_raises_when_github_cli_not_installed(self):
        """Should raise GitHubCLINotFoundError when gh is missing."""
        git = FakeGit(current_branch="feature-x", branches=["main", "feature-x"])
        github = FakeGitHub(cli_installed=False)
        config = FakeConfig()
        ui = FakeUI(strict=False)

        with pytest.raises(GitHubCLINotFoundError) as exc_info:
            submit_branch_core(
                git=git, github=github, config=config, ui=ui, branch_name="feature-x"
            )

        assert "GitHub CLI" in exc_info.value.message

    def test_raises_when_branch_not_found(self):
        """Should raise BranchNotFoundError for non-existent branch."""
        git = FakeGit(current_branch="main", branches=["main"])
        github = FakeGitHub()
        config = FakeConfig()
        ui = FakeUI(strict=False)

        with pytest.raises(BranchNotFoundError):
            submit_branch_core(
                git=git, github=github, config=config, ui=ui, branch_name="nonexistent"
            )

    def test_raises_when_current_branch_cannot_be_determined(self):
        """Should raise when no branch specified and current branch is None."""
        git = FakeGit(current_branch=None, branches=["main"])
        github = FakeGitHub()
        config = FakeConfig()
        ui = FakeUI(strict=False)

        with pytest.raises(BranchNotFoundError) as exc_info:
            submit_branch_core(git=git, github=github, config=config, ui=ui)

        assert "current branch" in exc_info.value.message.lower()

    def test_raises_on_push_failure(self):
        """Should raise PushError when push fails."""
        git = FakeGit(current_branch="feature-x", branches=["main", "feature-x"])
        git.fail_push = True
        github = FakeGitHub()
        config = FakeConfig()
        ui = FakeUI(strict=False)

        with pytest.raises(PushError):
            submit_branch_core(
                git=git, github=github, config=config, ui=ui, branch_name="feature-x"
            )

    def test_user_cancelled_on_pr_prompt(self):
        """Should raise UserCancelledError when user cancels PR prompt."""
        git = FakeGit(current_branch="feature-x", branches=["main", "feature-x"])
        github = FakeGitHub()
        config = FakeConfig()
        ui = FakeUI(cancel_on_confirm=True)

        with pytest.raises(UserCancelledError):
            submit_branch_core(
                git=git, github=github, config=config, ui=ui, branch_name="feature-x"
            )

        assert len(git.push_calls) == 1


class TestSubmitScenarios:
    """Parametrized tests for various submit scenarios."""

    @pytest.mark.parametrize(
        "amended,force_needed,expected_force",
        [
            (True, False, True),
            (False, True, True),
            (True, True, True),
            (False, False, False),
        ],
    )
    def test_force_push_decision_logic(self, amended, force_needed, expected_force):
        """Test the decision logic for force push."""
        git = FakeGit(
            current_branch="feature-x",
            branches=["main", "feature-x"],
            last_commit_amended=amended,
            force_push_needed={"feature-x": force_needed},
        )
        github = FakeGitHub(branches_with_pr={"feature-x"})
        config = FakeConfig()
        ui = FakeUI(strict=False)

        result = submit_branch_core(
            git=git, github=github, config=config, ui=ui, branch_name="feature-x"
        )

        assert result.force_pushed == expected_force
        assert git.push_calls[0] == ("feature-x", expected_force)


def test_update_pull_request_json_suppresses_non_json_stdout(monkeypatch, capsys):
    """JSON mode should emit only one JSON payload on stdout."""

    class NoisyGit:
        def get_current_branch(self):
            return "feature-x"

        def branch_exists(self, branch):
            return branch == "feature-x"

        def validate_branch(self, branch):
            if not self.branch_exists(branch):
                raise BranchNotFoundError(f"Branch '{branch}' does not exist")

        def is_last_commit_amended(self):
            return False

        def is_force_push_needed(self, branch):
            return False

        def push_branch(self, branch, force_with_lease=False):
            print("noisy push output")

    class NoisyGitHub:
        def is_cli_installed(self):
            return True

        def branch_has_pr(self, branch):
            print("noisy gh output")
            return True

        def get_pr_url(self, branch):
            return "https://github.com/org/repo/pull/42"

    class NoopConfig:
        def get_parent_branch(self, branch):
            return "main"

    monkeypatch.setattr("panqake.commands.submit.RealGit", NoisyGit)
    monkeypatch.setattr("panqake.commands.submit.RealGitHub", NoisyGitHub)
    monkeypatch.setattr("panqake.commands.submit.RealConfig", NoopConfig)

    update_pull_request(branch_name="feature-x", json_output=True)

    stdout_lines = [
        line for line in capsys.readouterr().out.strip().splitlines() if line
    ]
    assert len(stdout_lines) == 1

    payload = json.loads(stdout_lines[0])
    assert payload["ok"] is True
    assert payload["command"] == "submit"


def test_update_pull_request_json_create_pr_creates_pr(monkeypatch, capsys):
    """JSON mode with --create-pr should create PR and report real URL."""
    state: dict[str, object] = {}

    class NoisyGit:
        def get_current_branch(self):
            return "feature-x"

        def branch_exists(self, branch):
            return branch == "feature-x"

        def validate_branch(self, branch):
            if not self.branch_exists(branch):
                raise BranchNotFoundError(f"Branch '{branch}' does not exist")

        def is_last_commit_amended(self):
            return False

        def is_force_push_needed(self, branch):
            return False

        def push_branch(self, branch, force_with_lease=False):
            print("noisy push output")

        def is_branch_pushed_to_remote(self, branch):
            return branch in {"main", "feature-x"}

        def branch_has_commits(self, branch, parent_branch):
            return True

        def get_last_commit_subject(self, branch):
            return "Implement submit json flow"

    class CreatingGitHub:
        def is_cli_installed(self):
            return True

        def branch_has_pr(self, branch):
            return False

        def get_pr_url(self, branch):
            return "https://github.com/org/repo/pull/fallback"

        def get_potential_reviewers(self):
            return []

        def create_pr(self, base, head, title, body="", reviewers=None, draft=False):
            state["create_pr"] = (base, head, title, body, reviewers, draft)
            return "https://github.com/org/repo/pull/99"

    class NoopConfig:
        def get_parent_branch(self, branch):
            return "main"

    monkeypatch.setattr("panqake.commands.submit.RealGit", NoisyGit)
    monkeypatch.setattr("panqake.commands.submit.RealGitHub", CreatingGitHub)
    monkeypatch.setattr("panqake.commands.submit.RealConfig", NoopConfig)

    update_pull_request(branch_name="feature-x", create_pr=True, json_output=True)

    stdout_lines = [
        line for line in capsys.readouterr().out.strip().splitlines() if line
    ]
    assert len(stdout_lines) == 1

    payload = json.loads(stdout_lines[0])
    assert payload["ok"] is True
    assert payload["command"] == "submit"
    assert payload["result"]["pr_created"] is True
    assert payload["result"]["pr_url"] == "https://github.com/org/repo/pull/99"
    assert state["create_pr"] == (
        "main",
        "feature-x",
        "[feature-x] Implement submit json flow",
        "",
        None,
        False,
    )


def test_update_pull_request_json_create_pr_skips_when_no_commits(monkeypatch, capsys):
    """JSON mode should preserve no-commits preflight skip semantics."""
    state: dict[str, int] = {"create_pr_calls": 0}

    class NoisyGit:
        def get_current_branch(self):
            return "feature-x"

        def branch_exists(self, branch):
            return branch == "feature-x"

        def validate_branch(self, branch):
            if not self.branch_exists(branch):
                raise BranchNotFoundError(f"Branch '{branch}' does not exist")

        def is_last_commit_amended(self):
            return False

        def is_force_push_needed(self, branch):
            return False

        def push_branch(self, branch, force_with_lease=False):
            print("noisy push output")

        def is_branch_pushed_to_remote(self, branch):
            return branch in {"main", "feature-x"}

        def branch_has_commits(self, branch, parent_branch):
            return False

        def get_last_commit_subject(self, branch):
            return "No-op change"

    class CreatingGitHub:
        def is_cli_installed(self):
            return True

        def branch_has_pr(self, branch):
            return False

        def get_pr_url(self, branch):
            return None

        def get_potential_reviewers(self):
            return []

        def create_pr(self, base, head, title, body="", reviewers=None, draft=False):
            state["create_pr_calls"] = state["create_pr_calls"] + 1
            return "https://github.com/org/repo/pull/99"

    class NoopConfig:
        def get_parent_branch(self, branch):
            return "main"

    monkeypatch.setattr("panqake.commands.submit.RealGit", NoisyGit)
    monkeypatch.setattr("panqake.commands.submit.RealGitHub", CreatingGitHub)
    monkeypatch.setattr("panqake.commands.submit.RealConfig", NoopConfig)

    update_pull_request(branch_name="feature-x", create_pr=True, json_output=True)

    stdout_lines = [
        line for line in capsys.readouterr().out.strip().splitlines() if line
    ]
    assert len(stdout_lines) == 1

    payload = json.loads(stdout_lines[0])
    assert payload["ok"] is True
    assert payload["command"] == "submit"
    assert payload["result"]["pr_created"] is False
    assert payload["result"]["pr_url"] is None
    assert state["create_pr_calls"] == 0
