"""Command for updating remote branches and pull requests.

Uses dependency injection for testability.
Core logic is pure - no sys.exit, no direct filesystem/git calls.
"""

from dataclasses import replace

from panqake.commands.pr import create_pr_for_branch_core
from panqake.ports import (
    BranchNotFoundError,
    ConfigPort,
    GitHubCLINotFoundError,
    GitHubPort,
    GitPort,
    PRJsonUI,
    RealConfig,
    RealGit,
    RealGitHub,
    RealUI,
    SubmitResult,
    UIPort,
    emit_json_success,
    run_command,
)
from panqake.utils.questionary_prompt import format_branch
from panqake.utils.types import BranchName


def submit_branch_core(
    git: GitPort,
    github: GitHubPort,
    config: ConfigPort,
    ui: UIPort,
    branch_name: BranchName | None = None,
    create_pr: bool | None = None,
) -> SubmitResult:
    """Update a remote branch and its associated PR.

    This is the pure core logic that can be tested without mocking.
    Raises PanqakeError subclasses on failure instead of calling sys.exit.

    Args:
        git: Git operations interface
        github: GitHub CLI operations interface
        config: Stack configuration interface
        ui: User interaction interface
        branch_name: Branch to submit (uses current branch if None)
        create_pr: Whether to create PR when one doesn't exist.
            None means prompt.

    Returns:
        SubmitResult with push and PR metadata

    Raises:
        GitHubCLINotFoundError: If GitHub CLI is not installed
        BranchNotFoundError: If branch doesn't exist
        PushError: If push fails
        UserCancelledError: If user cancels a prompt
    """
    if not github.is_cli_installed():
        raise GitHubCLINotFoundError(
            "GitHub CLI (gh) is required but not installed. "
            "Please install GitHub CLI: https://cli.github.com"
        )

    if not branch_name:
        branch_name = git.get_current_branch()
        if not branch_name:
            raise BranchNotFoundError("Could not determine current branch")

    git.validate_branch(branch_name)

    ui.print_info("Analyzing branch status...")

    is_amended = git.is_last_commit_amended()
    needs_force = is_amended

    if not needs_force:
        needs_force = git.is_force_push_needed(branch_name)
        if needs_force:
            ui.print_info(
                "Detected non-fast-forward update. Force push with lease will be used."
            )

    git.push_branch(branch_name, force_with_lease=needs_force)

    pr_existed = github.branch_has_pr(branch_name)
    pr_created = False
    pr_url: str | None = None

    if pr_existed:
        pr_url = github.get_pr_url(branch_name)
    else:
        should_create = (
            create_pr
            if create_pr is not None
            else ui.prompt_confirm("Do you want to create a PR?")
        )
        if should_create:
            pr_created = True

    return SubmitResult(
        branch_name=branch_name,
        force_pushed=needs_force,
        pr_existed=pr_existed,
        pr_created=pr_created,
        pr_url=pr_url,
    )


def update_pull_request_core(
    git: GitPort,
    github: GitHubPort,
    config: ConfigPort,
    ui: UIPort,
    branch_name: BranchName | None = None,
    create_pr: bool | None = None,
) -> SubmitResult:
    """Submit a branch and return normalized final PR state."""
    result = submit_branch_core(
        git=git,
        github=github,
        config=config,
        ui=ui,
        branch_name=branch_name,
        create_pr=create_pr,
    )

    if not result.pr_created:
        return result

    parent = config.get_parent_branch(result.branch_name) or "main"
    pr_result = create_pr_for_branch_core(
        git=git,
        github=github,
        ui=ui,
        branch=result.branch_name,
        base=parent,
        draft=False,
    )

    if pr_result.status == "created":
        return replace(
            result,
            pr_existed=False,
            pr_created=True,
            pr_url=pr_result.pr_url or github.get_pr_url(result.branch_name),
        )

    if pr_result.status == "already_exists":
        return replace(
            result,
            pr_existed=True,
            pr_created=False,
            pr_url=pr_result.pr_url or github.get_pr_url(result.branch_name),
        )

    return replace(result, pr_existed=False, pr_created=False, pr_url=None)


def update_pull_request(
    branch_name: BranchName | None = None,
    create_pr: bool | None = None,
    *,
    json_output: bool = False,
) -> None:
    """CLI entrypoint that wraps core logic with real implementations.

    This thin wrapper:
    1. Instantiates real dependencies
    2. Calls the core logic
    3. Handles printing output
    4. Converts exceptions to sys.exit via run_command
    """
    git = RealGit()
    github = RealGitHub()
    config = RealConfig()
    ui = PRJsonUI() if json_output else RealUI()

    def core() -> SubmitResult:
        result = update_pull_request_core(
            git=git,
            github=github,
            config=config,
            ui=ui,
            branch_name=branch_name,
            create_pr=create_pr,
        )

        if not json_output:
            if result.pr_existed:
                ui.print_success(
                    f"PR for {format_branch(result.branch_name)} has been updated"
                )
                if result.pr_url:
                    ui.print_info(f"Pull request URL: {result.pr_url}")
            elif result.pr_created:
                ui.print_success(
                    f"PR created successfully for {format_branch(result.branch_name)}"
                )
                if result.pr_url:
                    ui.print_info(f"Pull request URL: {result.pr_url}")
            else:
                ui.print_info(
                    f"Branch {format_branch(result.branch_name)} updated on remote. "
                    "No PR exists yet."
                )
                ui.print_info("To create a PR, run: pq pr")

        return result

    result = run_command(ui, core, json_output=json_output, command="submit")
    if json_output and result is not None:
        emit_json_success("submit", result)
