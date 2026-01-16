"""Command for untracking a branch from the panqake stack.

Uses dependency injection for testability.
Core logic is pure - no sys.exit, no direct filesystem/git calls.
"""

from panqake.ports import (
    BranchNotFoundError,
    ConfigPort,
    GitPort,
    RealConfig,
    RealGit,
    RealUI,
    UIPort,
    UntrackResult,
    run_command,
)
from panqake.utils.questionary_prompt import format_branch
from panqake.utils.types import BranchName


def untrack_branch_core(
    git: GitPort,
    config: ConfigPort,
    ui: UIPort,
    branch_name: BranchName | None = None,
) -> UntrackResult:
    """Remove a branch from the panqake stack (does not delete the branch in git).

    This is the pure core logic that can be tested without mocking.
    Raises PanqakeError subclasses on failure instead of calling sys.exit.

    Args:
        git: Git operations interface
        config: Stack configuration interface
        ui: User interaction interface
        branch_name: Branch to untrack (uses current if None)

    Returns:
        UntrackResult with branch name and whether it was tracked

    Raises:
        BranchNotFoundError: If branch cannot be determined
    """
    if not branch_name:
        branch_name = git.get_current_branch()
        if not branch_name:
            raise BranchNotFoundError("Could not determine the current branch")

    ui.print_info(f"Untracking branch: {format_branch(branch_name)}")

    was_tracked = config.remove_from_stack(branch_name)

    return UntrackResult(
        branch_name=branch_name,
        was_tracked=was_tracked,
    )


def untrack(branch_name: BranchName | None = None) -> None:
    """CLI entrypoint that wraps core logic with real implementations.

    This thin wrapper:
    1. Instantiates real dependencies
    2. Calls the core logic
    3. Handles printing output
    4. Converts exceptions to sys.exit via run_command
    """
    git = RealGit()
    config = RealConfig()
    ui = RealUI()

    def core() -> None:
        result = untrack_branch_core(
            git=git,
            config=config,
            ui=ui,
            branch_name=branch_name,
        )

        if result.was_tracked:
            ui.print_success(
                f"Successfully removed branch '{result.branch_name}' from the stack"
            )
        else:
            ui.print_error(f"Branch '{result.branch_name}' was not found in the stack")

    run_command(ui, core)
