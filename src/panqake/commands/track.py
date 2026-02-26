"""Command for tracking existing Git branches in the panqake stack.

Uses dependency injection for testability.
Core logic is pure - no sys.exit, no direct filesystem/git calls.
"""

from panqake.ports import (
    BranchNotFoundError,
    ConfigPort,
    GitPort,
    JsonUI,
    NonInteractiveError,
    RealConfig,
    RealGit,
    RealUI,
    TrackResult,
    UIPort,
    UserCancelledError,
    emit_json_success,
    run_command,
)
from panqake.utils.questionary_prompt import format_branch
from panqake.utils.types import BranchName


class _TrackJsonUI(JsonUI):
    """Non-interactive UI policy for JSON-mode branch tracking."""

    def prompt_select_branch(
        self,
        branches: list[str],
        message: str,
        current_branch: str | None = None,
        exclude_protected: bool = False,
        enable_search: bool = True,
    ) -> str | None:
        filtered = [b for b in branches if b != current_branch]
        if exclude_protected:
            filtered = [b for b in filtered if b not in ("main", "master")]

        if len(filtered) == 1:
            return filtered[0]

        if not filtered:
            raise NonInteractiveError("parent branch selection")

        candidates = ", ".join(filtered)
        raise NonInteractiveError(
            f"parent branch selection (multiple candidates: {candidates})"
        )


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


def track(branch_name: BranchName | None = None, *, json_output: bool = False) -> None:
    """CLI entrypoint that wraps core logic with real implementations.

    This thin wrapper:
    1. Instantiates real dependencies
    2. Calls the core logic
    3. Handles printing output
    4. Converts exceptions to sys.exit via run_command
    """
    git = RealGit()
    config = RealConfig()
    ui = _TrackJsonUI() if json_output else RealUI()

    def core() -> TrackResult:
        result = track_branch_core(
            git=git,
            config=config,
            ui=ui,
            branch_name=branch_name,
        )

        if not json_output:
            ui.print_success(
                f"Successfully added branch '{result.branch_name}' to the stack "
                f"with parent '{result.parent_branch}'"
            )

        return result

    result = run_command(ui, core, json_output=json_output, command="track")
    if json_output and result is not None:
        emit_json_success("track", result)
