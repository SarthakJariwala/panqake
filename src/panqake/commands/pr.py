"""Command for creating pull requests for branches in the stack.

Uses dependency injection for testability.
Core logic is pure - no sys.exit, no direct filesystem/git calls.
"""

from panqake.ports import (
    BranchNotFoundError,
    BranchPRResult,
    ConfigPort,
    CreatePRStackResult,
    GitHubCLINotFoundError,
    GitHubPort,
    GitPort,
    NoChangesError,
    RealConfig,
    RealGit,
    RealGitHub,
    RealUI,
    UIPort,
    run_command,
)
from panqake.utils.questionary_prompt import PRTitleValidator, format_branch
from panqake.utils.types import BranchName


def find_oldest_branch_without_pr_core(
    branch: BranchName,
    config: ConfigPort,
    github: GitHubPort,
) -> BranchName:
    """Find the bottom-most branch without a PR.

    Walks up the stack from the target branch until finding:
    - A branch with an existing PR (returns child of that branch)
    - main/master (returns the first branch in the stack)
    """
    parent = config.get_parent_branch(branch)

    if not parent or parent in ["main", "master"]:
        return branch

    if github.branch_has_pr(parent):
        return branch
    else:
        return find_oldest_branch_without_pr_core(parent, config, github)


def compute_branch_path(
    starting_branch: BranchName,
    target_branch: BranchName,
    config: ConfigPort,
) -> list[BranchName]:
    """Compute the path from starting_branch up to target_branch.

    Returns branches in bottom-up order (starting_branch first, target_branch last).
    """
    if starting_branch == target_branch:
        return [starting_branch]

    path: list[BranchName] = []
    current: BranchName | None = target_branch
    while current is not None and current != starting_branch:
        path.append(current)
        current = config.get_parent_branch(current)

    if current == starting_branch:
        path.append(starting_branch)

    path.reverse()
    return path


def create_pr_for_branch_core(
    git: GitPort,
    github: GitHubPort,
    ui: UIPort,
    branch: BranchName,
    base: BranchName,
    draft: bool = False,
) -> BranchPRResult:
    """Create a PR for a specific branch.

    This is the pure core logic for creating a single PR.

    Returns:
        BranchPRResult with status of created, already_exists, or skipped
    """
    if github.branch_has_pr(branch):
        pr_url = github.get_pr_url(branch)
        return BranchPRResult(
            branch=branch,
            base=base,
            status="already_exists",
            pr_url=pr_url,
        )

    if not git.is_branch_pushed_to_remote(branch):
        ui.print_info(
            f"Branch {format_branch(branch)} has not been pushed to remote yet"
        )
        if ui.prompt_confirm("Would you like to push it now?"):
            git.push_branch(branch)
        else:
            return BranchPRResult(
                branch=branch,
                base=base,
                status="skipped",
                skip_reason="not_pushed",
            )

    if not git.is_branch_pushed_to_remote(base):
        ui.print_info(
            f"Base branch {format_branch(base)} has not been pushed to remote yet"
        )
        if ui.prompt_confirm("Would you like to push it now?"):
            git.push_branch(base)
        else:
            return BranchPRResult(
                branch=branch,
                base=base,
                status="skipped",
                skip_reason="base_not_pushed",
            )

    commit_base = base
    if not git.branch_has_commits(branch, commit_base):
        ui.print_info(
            f"No commits found between {format_branch(base)} and {format_branch(branch)}"
        )
        return BranchPRResult(
            branch=branch,
            base=base,
            status="skipped",
            skip_reason="no_commits",
        )

    commit_subject = git.get_last_commit_subject(branch)
    default_title = (
        f"[{branch}] {commit_subject}" if commit_subject else f"[{branch}] Stacked PR"
    )

    title = ui.prompt_input(
        "Enter PR title: ",
        validator=PRTitleValidator(),
        default=default_title,
    )

    description = ui.prompt_input_multiline(
        "Enter PR description (optional): ",
        default="",
    )

    if not draft:
        draft = ui.prompt_confirm("Is this a draft PR?")

    potential_reviewers = github.get_potential_reviewers()
    selected_reviewers = ui.prompt_select_reviewers(potential_reviewers)

    ui.print_info(f"Creating PR: {format_branch(base)} ← {format_branch(branch)}")
    ui.print_info(f"Title: {title}")
    if selected_reviewers:
        ui.print_muted(f"Reviewers: {', '.join(selected_reviewers)}")

    if not ui.prompt_confirm("Create this pull request?"):
        return BranchPRResult(
            branch=branch,
            base=base,
            status="skipped",
            skip_reason="user_declined",
        )

    pr_url = github.create_pr(
        base=base,
        head=branch,
        title=title,
        body=description,
        reviewers=selected_reviewers if selected_reviewers else None,
        draft=draft,
    )

    return BranchPRResult(
        branch=branch,
        base=base,
        status="created",
        pr_url=pr_url,
        title=title,
        reviewers=selected_reviewers if selected_reviewers else None,
        draft=draft,
    )


def create_pull_requests_core(
    git: GitPort,
    github: GitHubPort,
    config: ConfigPort,
    ui: UIPort,
    branch_name: BranchName | None = None,
    draft: bool = False,
) -> CreatePRStackResult:
    """Create pull requests for branches in the stack.

    This is the pure core logic that can be tested without mocking.
    Processes branches bottom-up from oldest branch without PR to target.

    Args:
        git: Git operations interface
        github: GitHub CLI operations interface
        config: Stack configuration interface
        ui: User interaction interface
        branch_name: Target branch (uses current branch if None)
        draft: Whether to create all PRs as drafts

    Returns:
        CreatePRStackResult with results for each branch processed

    Raises:
        GitHubCLINotFoundError: If GitHub CLI is not installed
        BranchNotFoundError: If branch doesn't exist
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

    ui.print_info("Analyzing branch stack for PR creation...")

    starting_branch = find_oldest_branch_without_pr_core(branch_name, config, github)

    if github.branch_has_pr(starting_branch) and starting_branch == branch_name:
        ui.print_info(f"Branch {format_branch(branch_name)} already has an open PR")
        return CreatePRStackResult(
            target_branch=branch_name,
            starting_branch=starting_branch,
            results=[
                BranchPRResult(
                    branch=branch_name,
                    base=config.get_parent_branch(branch_name) or "main",
                    status="already_exists",
                    pr_url=github.get_pr_url(branch_name),
                )
            ],
        )

    branch_path = compute_branch_path(starting_branch, branch_name, config)

    if not branch_path:
        raise NoChangesError("No branches found that need PRs")

    ui.print_info(
        f"Creating PRs from bottom of stack up to: {format_branch(branch_name)}"
    )

    results: list[BranchPRResult] = []

    for branch in branch_path:
        parent = config.get_parent_branch(branch)
        base = parent if parent else "main"

        ui.print_info(f"\nProcessing branch: {format_branch(branch)}")

        result = create_pr_for_branch_core(
            git=git,
            github=github,
            ui=ui,
            branch=branch,
            base=base,
            draft=draft,
        )

        results.append(result)

        if result.status == "skipped":
            remaining = branch_path[branch_path.index(branch) + 1 :]
            for remaining_branch in remaining:
                remaining_parent = config.get_parent_branch(remaining_branch)
                remaining_base = remaining_parent if remaining_parent else "main"
                results.append(
                    BranchPRResult(
                        branch=remaining_branch,
                        base=remaining_base,
                        status="skipped",
                        skip_reason="blocked_by_parent",
                    )
                )
            break

    return CreatePRStackResult(
        target_branch=branch_name,
        starting_branch=starting_branch,
        results=results,
    )


def create_pull_requests(
    branch_name: BranchName | None = None, draft: bool = False
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
    ui = RealUI()

    def core() -> None:
        result = create_pull_requests_core(
            git=git,
            github=github,
            config=config,
            ui=ui,
            branch_name=branch_name,
            draft=draft,
        )

        created_count = sum(1 for r in result.results if r.status == "created")
        existing_count = sum(1 for r in result.results if r.status == "already_exists")
        skipped_count = sum(1 for r in result.results if r.status == "skipped")

        if created_count > 0:
            ui.print_success(f"Created {created_count} pull request(s)")
        if existing_count > 0:
            ui.print_info(f"{existing_count} PR(s) already existed")
        if skipped_count > 0:
            ui.print_info(f"{skipped_count} branch(es) skipped")

        for r in result.results:
            if r.status == "created" and r.pr_url:
                ui.print_info(f"  {format_branch(r.branch)}: {r.pr_url}")

    run_command(ui, core)


def create_pr_for_branch(
    branch: BranchName, parent: BranchName, draft: bool = False
) -> bool:
    """Create a PR for a specific branch.

    This is a convenience function used by submit.py.
    Returns True if PR was created, False otherwise.
    """
    git = RealGit()
    github = RealGitHub()
    ui = RealUI()

    try:
        result = create_pr_for_branch_core(
            git=git,
            github=github,
            ui=ui,
            branch=branch,
            base=parent,
            draft=draft,
        )
        if result.status == "created":
            ui.print_success(f"PR created successfully for {format_branch(branch)}")
            if result.pr_url:
                ui.print_info(f"Pull request URL: {result.pr_url}")
            return True
        elif result.status == "already_exists":
            ui.print_info(f"Branch {format_branch(branch)} already has an open PR")
            return True
        else:
            ui.print_info(f"PR creation skipped: {result.skip_reason}")
            return False
    except Exception as e:
        ui.print_error(f"Failed to create PR: {e}")
        return False
