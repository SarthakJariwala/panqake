"""Command for navigating to child branch in stack.

Uses dependency injection for testability.
Core logic is pure - no sys.exit, no direct filesystem/git calls.
"""

from panqake.ports import (
    BranchNotFoundError,
    ConfigPort,
    DownResult,
    GitPort,
    RealConfig,
    RealGit,
    RealUI,
    UIPort,
    run_command,
)
from panqake.utils.questionary_prompt import format_branch


def down_core(
    git: GitPort,
    config: ConfigPort,
    ui: UIPort,
) -> DownResult:
    """Navigate to a child branch in the stack.

    This is the pure core logic that can be tested without mocking.
    Raises PanqakeError subclasses on failure instead of calling sys.exit.

    If the current branch has:
    - No children: Raises BranchNotFoundError
    - One child: Directly switches to that child branch
    - Multiple children: Prompts user to select which child to navigate to

    Args:
        git: Git operations interface
        config: Stack configuration interface
        ui: User interaction interface

    Returns:
        DownResult with navigation metadata

    Raises:
        BranchNotFoundError: If current branch cannot be determined or has no children
        UserCancelledError: If user cancels selection prompt
    """
    current = git.get_current_branch()
    if not current:
        raise BranchNotFoundError("Could not determine current branch")

    children = config.get_child_branches(current)
    if not children:
        raise BranchNotFoundError(f"Branch '{current}' has no child branches")

    # Determine which child to switch to
    if len(children) == 1:
        child = children[0]
    else:
        ui.print_info(f"Branch '{current}' has multiple children")
        child = ui.prompt_select_branch(
            branches=children,
            message="Select a child branch to switch to:",
            current_branch=current,
            exclude_protected=False,
            enable_search=True,
        )
        if not child:
            raise BranchNotFoundError("No child branch selected")

    worktree_path = git.get_worktree_path(child)
    if worktree_path:
        ui.print_info(f"Child branch '{child}' is in a worktree. To switch to it:")
        ui.print_info(f"cd {worktree_path}")
        return DownResult(
            target_branch=child,
            previous_branch=current,
            switched=False,
            worktree_path=worktree_path,
        )

    git.checkout_branch(child)
    return DownResult(
        target_branch=child,
        previous_branch=current,
        switched=True,
    )


def down() -> None:
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
        result = down_core(git=git, config=config, ui=ui)

        if result.switched:
            ui.print_success(
                f"Moved down to child branch {format_branch(result.target_branch)}"
            )

    run_command(ui, core)
