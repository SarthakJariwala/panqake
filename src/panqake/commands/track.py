"""Command for tracking existing Git branches in the panqake stack.

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
    TrackResult,
    UIPort,
    UserCancelledError,
    run_command,
)
from panqake.utils.questionary_prompt import format_branch
from panqake.utils.types import BranchName


def track_branch_core(
    git: GitPort,
    config: ConfigPort,
    ui: UIPort,
    branch_name: BranchName | None = None,
) -> TrackResult:
    """Track an existing Git branch in the panqake stack.

    This is the pure core logic that can be tested without mocking.
    Raises PanqakeError subclasses on failure instead of calling sys.exit.

    Args:
        git: Git operations interface
        config: Stack configuration interface
        ui: User interaction interface
        branch_name: Branch to track (uses current if None)

    Returns:
        TrackResult with branch and parent metadata

    Raises:
        BranchNotFoundError: If branch cannot be determined or no parents found
        UserCancelledError: If user cancels parent selection
    """
    if not branch_name:
        branch_name = git.get_current_branch()
        if not branch_name:
            raise BranchNotFoundError("Could not determine the current branch")

    ui.print_info(f"Tracking branch: {format_branch(branch_name)}")

    potential_parents = git.get_potential_parents(branch_name)

    if not potential_parents:
        raise BranchNotFoundError(
            f"No potential parent branches found in the history of '{branch_name}'"
        )

    selected_parent = ui.prompt_select_branch(
        potential_parents,
        "Select a parent branch:",
        current_branch=branch_name,
        exclude_protected=False,
        enable_search=True,
    )

    if not selected_parent:
        raise UserCancelledError()

    config.add_to_stack(branch_name, selected_parent)

    return TrackResult(
        branch_name=branch_name,
        parent_branch=selected_parent,
    )


def track(branch_name: BranchName | None = None) -> None:
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
        result = track_branch_core(
            git=git,
            config=config,
            ui=ui,
            branch_name=branch_name,
        )

        ui.print_success(
            f"Successfully added branch '{result.branch_name}' to the stack "
            f"with parent '{result.parent_branch}'"
        )

    run_command(ui, core)
