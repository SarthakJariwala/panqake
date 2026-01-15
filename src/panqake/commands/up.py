"""Command for navigating to parent branch in stack.

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
    UpResult,
    run_command,
)
from panqake.utils.questionary_prompt import format_branch


def up_core(
    git: GitPort,
    config: ConfigPort,
    ui: UIPort,
) -> UpResult:
    """Navigate to the parent branch in the stack.

    This is the pure core logic that can be tested without mocking.
    Raises PanqakeError subclasses on failure instead of calling sys.exit.

    Args:
        git: Git operations interface
        config: Stack configuration interface
        ui: User interaction interface

    Returns:
        UpResult with navigation metadata

    Raises:
        BranchNotFoundError: If current branch cannot be determined or has no parent
    """
    current = git.get_current_branch()
    if not current:
        raise BranchNotFoundError("Could not determine current branch")

    parent = config.get_parent_branch(current)
    if not parent:
        raise BranchNotFoundError(f"Branch '{current}' has no parent branch")

    worktree_path = git.get_worktree_path(parent)
    if worktree_path:
        ui.print_info(f"Parent branch '{parent}' is in a worktree. To switch to it:")
        ui.print_info(f"cd {worktree_path}")
        return UpResult(
            target_branch=parent,
            previous_branch=current,
            switched=False,
            worktree_path=worktree_path,
        )

    git.checkout_branch(parent)
    return UpResult(
        target_branch=parent,
        previous_branch=current,
        switched=True,
    )


def up() -> None:
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
        result = up_core(git=git, config=config, ui=ui)

        if result.switched:
            ui.print_success(
                f"Moved up to parent branch {format_branch(result.target_branch)}"
            )

    run_command(ui, core)
