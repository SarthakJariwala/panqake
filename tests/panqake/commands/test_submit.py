"""Tests for submit command using the ports/fakes testing architecture."""

import pytest

from panqake.commands.submit import submit_branch_core
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
