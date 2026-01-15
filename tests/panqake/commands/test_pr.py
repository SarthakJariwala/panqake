"""Tests for pr.py command module using dependency injection pattern."""

import pytest

from panqake.commands.pr import (
    compute_branch_path,
    create_pr_for_branch_core,
    create_pull_requests_core,
    find_oldest_branch_without_pr_core,
)
from panqake.ports import (
    BranchNotFoundError,
    GitHubCLINotFoundError,
    UserCancelledError,
)
from panqake.testing.fakes import FakeConfig, FakeGit, FakeGitHub, FakeUI


class TestFindOldestBranchWithoutPR:
    """Tests for find_oldest_branch_without_pr_core."""

    def test_no_parent_returns_current_branch(self):
        config = FakeConfig()
        github = FakeGitHub()

        result = find_oldest_branch_without_pr_core("feature", config, github)

        assert result == "feature"

    def test_parent_is_main_returns_current_branch(self):
        config = FakeConfig(stack={"feature": {"parent": "main"}})
        github = FakeGitHub()

        result = find_oldest_branch_without_pr_core("feature", config, github)

        assert result == "feature"

    def test_parent_has_pr_returns_current_branch(self):
        config = FakeConfig(stack={"feature": {"parent": "base"}})
        github = FakeGitHub(branches_with_pr={"base"})

        result = find_oldest_branch_without_pr_core("feature", config, github)

        assert result == "feature"

    def test_walks_to_oldest_without_pr(self):
        config = FakeConfig(
            stack={
                "feature": {"parent": "intermediate"},
                "intermediate": {"parent": "oldest"},
                "oldest": {"parent": "main"},
            }
        )
        github = FakeGitHub()

        result = find_oldest_branch_without_pr_core("feature", config, github)

        assert result == "oldest"

    def test_stops_at_branch_with_pr(self):
        config = FakeConfig(
            stack={
                "feature": {"parent": "intermediate"},
                "intermediate": {"parent": "oldest"},
                "oldest": {"parent": "main"},
            }
        )
        github = FakeGitHub(branches_with_pr={"intermediate"})

        result = find_oldest_branch_without_pr_core("feature", config, github)

        assert result == "feature"


class TestComputeBranchPath:
    """Tests for compute_branch_path."""

    def test_same_branch_returns_single_element(self):
        config = FakeConfig()

        result = compute_branch_path("feature", "feature", config)

        assert result == ["feature"]

    def test_computes_path_bottom_up(self):
        config = FakeConfig(
            stack={
                "feature": {"parent": "intermediate"},
                "intermediate": {"parent": "oldest"},
            }
        )

        result = compute_branch_path("oldest", "feature", config)

        assert result == ["oldest", "intermediate", "feature"]

    def test_partial_path(self):
        config = FakeConfig(
            stack={
                "feature": {"parent": "intermediate"},
                "intermediate": {"parent": "base"},
            }
        )

        result = compute_branch_path("intermediate", "feature", config)

        assert result == ["intermediate", "feature"]


class TestCreatePRForBranchCore:
    """Tests for create_pr_for_branch_core."""

    def test_returns_already_exists_when_pr_exists(self):
        git = FakeGit(branches=["main", "feature"], pushed_branches={"feature", "main"})
        github = FakeGitHub(
            branches_with_pr={"feature"},
            pr_urls={"feature": "https://github.com/test/repo/pull/1"},
        )
        ui = FakeUI(strict=False)

        result = create_pr_for_branch_core(
            git=git,
            github=github,
            ui=ui,
            branch="feature",
            base="main",
        )

        assert result.status == "already_exists"
        assert result.pr_url == "https://github.com/test/repo/pull/1"
        assert len(github.create_pr_calls) == 0

    def test_prompts_to_push_when_not_pushed(self):
        git = FakeGit(
            branches=["main", "feature"],
            pushed_branches={"main"},
            branch_commits={"feature": True},
            commit_subjects={"feature": "feat: test"},
        )
        github = FakeGitHub(potential_reviewers=["alice"])
        ui = FakeUI(
            confirm_responses=[True, False, True],  # push, not draft, confirm create
            input_responses=["My PR title"],
            input_multiline_responses=["Description"],
            select_reviewers_responses=[[]],
        )

        result = create_pr_for_branch_core(
            git=git,
            github=github,
            ui=ui,
            branch="feature",
            base="main",
        )

        assert result.status == "created"
        assert ("feature", False) in git.push_calls

    def test_skips_when_user_declines_push(self):
        git = FakeGit(branches=["main", "feature"], pushed_branches={"main"})
        github = FakeGitHub()
        ui = FakeUI(confirm_responses=[False])  # decline push

        result = create_pr_for_branch_core(
            git=git,
            github=github,
            ui=ui,
            branch="feature",
            base="main",
        )

        assert result.status == "skipped"
        assert result.skip_reason == "not_pushed"

    def test_skips_when_no_commits(self):
        git = FakeGit(
            branches=["main", "feature"],
            pushed_branches={"main", "feature"},
            branch_commits={"feature": False},
        )
        github = FakeGitHub()
        ui = FakeUI(strict=False)

        result = create_pr_for_branch_core(
            git=git,
            github=github,
            ui=ui,
            branch="feature",
            base="main",
        )

        assert result.status == "skipped"
        assert result.skip_reason == "no_commits"

    def test_skips_when_user_declines_creation(self):
        git = FakeGit(
            branches=["main", "feature"],
            pushed_branches={"main", "feature"},
            branch_commits={"feature": True},
            commit_subjects={"feature": "feat: test"},
        )
        github = FakeGitHub(potential_reviewers=[])
        ui = FakeUI(
            confirm_responses=[False, False],  # not draft, decline create
            input_responses=["Title"],
            input_multiline_responses=[""],
            select_reviewers_responses=[[]],
        )

        result = create_pr_for_branch_core(
            git=git,
            github=github,
            ui=ui,
            branch="feature",
            base="main",
        )

        assert result.status == "skipped"
        assert result.skip_reason == "user_declined"

    def test_creates_pr_with_all_details(self):
        git = FakeGit(
            branches=["main", "feature"],
            pushed_branches={"main", "feature"},
            branch_commits={"feature": True},
            commit_subjects={"feature": "feat: test commit"},
        )
        github = FakeGitHub(potential_reviewers=["alice", "bob"])
        ui = FakeUI(
            confirm_responses=[True, True],  # draft, confirm create
            input_responses=["My Custom Title"],
            input_multiline_responses=["PR description here"],
            select_reviewers_responses=[["alice"]],
        )

        result = create_pr_for_branch_core(
            git=git,
            github=github,
            ui=ui,
            branch="feature",
            base="main",
        )

        assert result.status == "created"
        assert result.title == "My Custom Title"
        assert result.draft is True
        assert result.reviewers == ["alice"]
        assert result.pr_url is not None

        assert len(github.create_pr_calls) == 1
        call = github.create_pr_calls[0]
        assert call[0] == "main"  # base
        assert call[1] == "feature"  # head
        assert call[2] == "My Custom Title"  # title
        assert call[3] == "PR description here"  # body
        assert call[4] == ["alice"]  # reviewers
        assert call[5] is True  # draft

    def test_uses_default_title_from_commit(self):
        git = FakeGit(
            branches=["main", "feature"],
            pushed_branches={"main", "feature"},
            branch_commits={"feature": True},
            commit_subjects={"feature": "feat: awesome feature"},
        )

        assert git.get_last_commit_subject("feature") == "feat: awesome feature"


class TestCreatePullRequestsCore:
    """Tests for create_pull_requests_core."""

    def test_raises_when_cli_not_installed(self):
        git = FakeGit(branches=["main", "feature"], current_branch="feature")
        github = FakeGitHub(cli_installed=False)
        config = FakeConfig()
        ui = FakeUI(strict=False)

        with pytest.raises(GitHubCLINotFoundError):
            create_pull_requests_core(
                git=git,
                github=github,
                config=config,
                ui=ui,
            )

    def test_raises_when_branch_not_exists(self):
        git = FakeGit(branches=["main"])
        github = FakeGitHub()
        config = FakeConfig()
        ui = FakeUI(strict=False)

        with pytest.raises(BranchNotFoundError):
            create_pull_requests_core(
                git=git,
                github=github,
                config=config,
                ui=ui,
                branch_name="nonexistent",
            )

    def test_uses_current_branch_when_none_specified(self):
        git = FakeGit(
            branches=["main", "feature"],
            current_branch="feature",
            pushed_branches={"main", "feature"},
            branch_commits={"feature": True},
            commit_subjects={"feature": "test"},
        )
        github = FakeGitHub()
        config = FakeConfig(stack={"feature": {"parent": "main"}})
        ui = FakeUI(
            confirm_responses=[False, True],
            input_responses=["Title"],
            input_multiline_responses=[""],
            select_reviewers_responses=[[]],
        )

        result = create_pull_requests_core(
            git=git,
            github=github,
            config=config,
            ui=ui,
        )

        assert result.target_branch == "feature"

    def test_returns_already_exists_for_target_with_pr(self):
        git = FakeGit(branches=["main", "feature"], current_branch="feature")
        github = FakeGitHub(branches_with_pr={"feature"})
        config = FakeConfig(stack={"feature": {"parent": "main"}})
        ui = FakeUI(strict=False)

        result = create_pull_requests_core(
            git=git,
            github=github,
            config=config,
            ui=ui,
            branch_name="feature",
        )

        assert len(result.results) == 1
        assert result.results[0].status == "already_exists"

    def test_creates_prs_bottom_up(self):
        git = FakeGit(
            branches=["main", "base", "feature"],
            current_branch="feature",
            pushed_branches={"main", "base", "feature"},
            branch_commits={"base": True, "feature": True},
            commit_subjects={"base": "base commit", "feature": "feature commit"},
        )
        github = FakeGitHub()
        config = FakeConfig(
            stack={
                "feature": {"parent": "base"},
                "base": {"parent": "main"},
            }
        )
        ui = FakeUI(
            confirm_responses=[
                False,
                True,
                False,
                True,
            ],  # base: draft/confirm, feature: draft/confirm
            input_responses=["Base PR", "Feature PR"],
            input_multiline_responses=["", ""],
            select_reviewers_responses=[[], []],
        )

        result = create_pull_requests_core(
            git=git,
            github=github,
            config=config,
            ui=ui,
            branch_name="feature",
        )

        assert len(result.results) == 2
        assert result.results[0].branch == "base"
        assert result.results[0].status == "created"
        assert result.results[1].branch == "feature"
        assert result.results[1].status == "created"

    def test_stops_and_marks_remaining_as_blocked_when_parent_skipped(self):
        git = FakeGit(
            branches=["main", "base", "feature"],
            current_branch="feature",
            pushed_branches={"main"},  # base and feature not pushed
            branch_commits={"base": True, "feature": True},
        )
        github = FakeGitHub()
        config = FakeConfig(
            stack={
                "feature": {"parent": "base"},
                "base": {"parent": "main"},
            }
        )
        ui = FakeUI(
            confirm_responses=[False],  # decline to push base
            strict=False,
        )

        result = create_pull_requests_core(
            git=git,
            github=github,
            config=config,
            ui=ui,
            branch_name="feature",
        )

        assert len(result.results) == 2
        assert result.results[0].branch == "base"
        assert result.results[0].status == "skipped"
        assert result.results[0].skip_reason == "not_pushed"
        assert result.results[1].branch == "feature"
        assert result.results[1].status == "skipped"
        assert result.results[1].skip_reason == "blocked_by_parent"


class TestUserCancellation:
    """Tests for user cancellation handling."""

    def test_cancel_on_title_input(self):
        git = FakeGit(
            branches=["main", "feature"],
            pushed_branches={"main", "feature"},
            branch_commits={"feature": True},
        )
        github = FakeGitHub()
        ui = FakeUI(cancel_on_input=True)

        with pytest.raises(UserCancelledError):
            create_pr_for_branch_core(
                git=git,
                github=github,
                ui=ui,
                branch="feature",
                base="main",
            )

    def test_cancel_on_confirm(self):
        git = FakeGit(
            branches=["main", "feature"],
            pushed_branches={"main", "feature"},
            branch_commits={"feature": True},
            commit_subjects={"feature": "test"},
        )
        github = FakeGitHub()
        ui = FakeUI(
            input_responses=["Title"],
            input_multiline_responses=[""],
            select_reviewers_responses=[[]],
            cancel_on_confirm=True,
        )

        with pytest.raises(UserCancelledError):
            create_pr_for_branch_core(
                git=git,
                github=github,
                ui=ui,
                branch="feature",
                base="main",
            )
