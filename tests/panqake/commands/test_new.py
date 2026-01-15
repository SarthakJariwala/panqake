"""Tests for new.py - refactored with fakes instead of mocks.

These tests verify BEHAVIOR, not implementation details.
No patches required - just inject fakes.
"""

import pytest

from panqake.commands.new import create_new_branch_core
from panqake.ports import (
    BranchExistsError,
    BranchNotFoundError,
    UserCancelledError,
    WorktreeError,
)
from panqake.testing import FakeConfig, FakeFilesystem, FakeGit, FakeUI


class TestCreateNewBranchCore:
    """Tests for the core branch creation logic."""

    def test_creates_branch_with_explicit_args(self):
        """Branch is created and added to stack when args are provided."""
        git = FakeGit(branches=["main", "develop"])
        config = FakeConfig()
        ui = FakeUI()
        fs = FakeFilesystem()

        result = create_new_branch_core(
            git=git,
            config=config,
            ui=ui,
            fs=fs,
            branch_name="feature-x",
            base_branch="main",
        )

        # Verify result
        assert result.branch_name == "feature-x"
        assert result.base_branch == "main"
        assert result.worktree_path is None

        # Verify state changes
        assert "feature-x" in git.branches
        assert git.current_branch == "feature-x"
        assert config.stack["feature-x"] == {"parent": "main"}

    def test_creates_branch_interactively(self):
        """Prompts for branch name and base when not provided."""
        git = FakeGit(branches=["main", "develop"], current_branch="develop")
        config = FakeConfig()
        ui = FakeUI(input_responses=["feature-y", "main"])
        fs = FakeFilesystem()

        result = create_new_branch_core(
            git=git,
            config=config,
            ui=ui,
            fs=fs,
            branch_name=None,
            base_branch=None,
        )

        # Verify prompts were asked with correct data
        assert len(ui.input_calls) == 2
        assert "branch name" in ui.input_calls[0].message.lower()
        assert ui.input_calls[0].has_validator is True  # Validator was passed

        assert "base branch" in ui.input_calls[1].message.lower()
        assert ui.input_calls[1].completer == ["develop", "main"]  # Branch list
        assert ui.input_calls[1].default == "develop"  # Current branch as default

        # Verify outcome
        assert result.branch_name == "feature-y"
        assert result.base_branch == "main"
        assert "feature-y" in git.branches

    def test_uses_current_branch_as_default_base(self):
        """When base not specified, defaults to current branch."""
        git = FakeGit(branches=["main", "develop"], current_branch="develop")
        config = FakeConfig()
        # Second response is "develop" = accept default
        ui = FakeUI(input_responses=["feature-z", "develop"])
        fs = FakeFilesystem()

        result = create_new_branch_core(
            git=git,
            config=config,
            ui=ui,
            fs=fs,
            branch_name=None,
            base_branch=None,
        )

        # Feature created from develop (current branch)
        assert result.base_branch == "develop"
        assert ("feature-z", "develop") in git.created_branches

    def test_raises_when_branch_already_exists(self):
        """Error raised if new branch name already exists."""
        git = FakeGit(branches=["main", "existing-branch"])
        config = FakeConfig()
        ui = FakeUI()
        fs = FakeFilesystem()

        with pytest.raises(BranchExistsError) as exc_info:
            create_new_branch_core(
                git=git,
                config=config,
                ui=ui,
                fs=fs,
                branch_name="existing-branch",
                base_branch="main",
            )

        assert "already exists" in str(exc_info.value)
        # Branch not re-created
        assert len(git.created_branches) == 0
        # Stack not modified
        assert "existing-branch" not in config.stack

    def test_raises_when_base_branch_missing(self):
        """Error raised if base branch doesn't exist."""
        git = FakeGit(branches=["main"])
        config = FakeConfig()
        ui = FakeUI()
        fs = FakeFilesystem()

        with pytest.raises(BranchNotFoundError) as exc_info:
            create_new_branch_core(
                git=git,
                config=config,
                ui=ui,
                fs=fs,
                branch_name="feature-a",
                base_branch="nonexistent",
            )

        assert "nonexistent" in str(exc_info.value)
        assert len(git.created_branches) == 0

    def test_creates_worktree_branch(self):
        """Branch created in worktree with metadata recorded."""
        git = FakeGit(branches=["main"])
        config = FakeConfig()
        ui = FakeUI()
        fs = FakeFilesystem()

        result = create_new_branch_core(
            git=git,
            config=config,
            ui=ui,
            fs=fs,
            branch_name="feature-wt",
            base_branch="main",
            use_worktree=True,
            worktree_path="/tmp/feature-wt",
        )

        assert result.worktree_path is not None
        assert "feature-wt" in result.worktree_path
        assert "feature-wt" in git.worktrees
        assert config.stack["feature-wt"]["parent"] == "main"
        assert "worktree" in config.stack["feature-wt"]

    def test_worktree_path_prompted_when_not_provided(self):
        """Prompts for worktree path when use_worktree=True but path not given."""
        git = FakeGit(branches=["main"])
        config = FakeConfig()
        ui = FakeUI(path_responses=["/custom/path"])
        fs = FakeFilesystem()

        result = create_new_branch_core(
            git=git,
            config=config,
            ui=ui,
            fs=fs,
            branch_name="feature-wt2",
            base_branch="main",
            use_worktree=True,
            worktree_path=None,
        )

        assert len(ui.path_calls) == 1
        assert "worktree path" in ui.path_calls[0].message.lower()
        assert result.worktree_path is not None

    def test_worktree_directory_exists_raises_error(self):
        """Error raised if worktree directory already exists."""
        git = FakeGit(branches=["main"])
        config = FakeConfig()
        ui = FakeUI()
        fs = FakeFilesystem(existing_paths={"/existing/path"})

        with pytest.raises(WorktreeError) as exc_info:
            create_new_branch_core(
                git=git,
                config=config,
                ui=ui,
                fs=fs,
                branch_name="feature-wt",
                base_branch="main",
                use_worktree=True,
                worktree_path="/existing/path",
            )

        assert "already exists" in str(exc_info.value)


class TestCancellation:
    """Tests for user cancellation handling."""

    def test_cancel_on_branch_name_prompt(self):
        """UserCancelledError raised when user cancels branch name prompt."""
        git = FakeGit(branches=["main"])
        config = FakeConfig()
        ui = FakeUI(cancel_on_input=True)
        fs = FakeFilesystem()

        with pytest.raises(UserCancelledError):
            create_new_branch_core(
                git=git,
                config=config,
                ui=ui,
                fs=fs,
                branch_name=None,
                base_branch="main",
            )

        # No changes made
        assert len(git.created_branches) == 0

    def test_cancel_on_path_prompt(self):
        """UserCancelledError raised when user cancels path prompt."""
        git = FakeGit(branches=["main"])
        config = FakeConfig()
        ui = FakeUI(cancel_on_path=True)
        fs = FakeFilesystem()

        with pytest.raises(UserCancelledError):
            create_new_branch_core(
                git=git,
                config=config,
                ui=ui,
                fs=fs,
                branch_name="feature",
                base_branch="main",
                use_worktree=True,
                worktree_path=None,
            )


class TestBehaviorMatrix:
    """Matrix of scenarios for regression catching."""

    @pytest.mark.parametrize(
        "branches,current,new_name,base,expected_base",
        [
            # Create from main
            (["main"], "main", "feature-1", "main", "main"),
            # Create from develop
            (["main", "develop"], "develop", "feature-2", "develop", "develop"),
            # Explicit base different from current
            (["main", "develop"], "develop", "feature-3", "main", "main"),
            # Deep stack: feature on feature
            (["main", "feat-a"], "feat-a", "feat-b", "feat-a", "feat-a"),
        ],
    )
    def test_branch_creation_scenarios(
        self, branches, current, new_name, base, expected_base
    ):
        """Various branch creation scenarios produce correct results."""
        git = FakeGit(branches=branches, current_branch=current)
        config = FakeConfig()
        ui = FakeUI()
        fs = FakeFilesystem()

        result = create_new_branch_core(
            git=git,
            config=config,
            ui=ui,
            fs=fs,
            branch_name=new_name,
            base_branch=base,
        )

        assert result.branch_name == new_name
        assert result.base_branch == expected_base
        assert new_name in git.branches
        assert config.stack[new_name]["parent"] == expected_base

    @pytest.mark.parametrize(
        "scenario,setup,error_type",
        [
            (
                "branch exists",
                {"branches": ["main", "existing"], "new": "existing", "base": "main"},
                BranchExistsError,
            ),
            (
                "base missing",
                {"branches": ["main"], "new": "feature", "base": "missing"},
                BranchNotFoundError,
            ),
        ],
    )
    def test_error_scenarios(self, scenario, setup, error_type):
        """Error scenarios raise appropriate exceptions."""
        git = FakeGit(branches=setup["branches"])
        config = FakeConfig()
        ui = FakeUI()
        fs = FakeFilesystem()

        with pytest.raises(error_type):
            create_new_branch_core(
                git=git,
                config=config,
                ui=ui,
                fs=fs,
                branch_name=setup["new"],
                base_branch=setup["base"],
            )

        # State unchanged on error
        if setup["new"] not in setup["branches"]:
            assert setup["new"] not in git.branches
        assert setup["new"] not in config.stack


class TestFakeUIStrictMode:
    """Tests for FakeUI strict mode behavior."""

    def test_strict_mode_raises_on_missing_response(self):
        """In strict mode, missing responses raise AssertionError."""
        ui = FakeUI(strict=True)

        with pytest.raises(AssertionError) as exc_info:
            ui.prompt_input("What is your name?")

        assert "No response queued" in str(exc_info.value)

    def test_non_strict_mode_returns_default(self):
        """In non-strict mode, missing responses return default."""
        ui = FakeUI(strict=False)

        result = ui.prompt_input("What is your name?", default="anonymous")

        assert result == "anonymous"
