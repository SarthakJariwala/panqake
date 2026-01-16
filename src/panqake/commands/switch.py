"""Command for switching between Git branches.

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
    SwitchResult,
    UIPort,
    find_stack_root,
    run_command,
)
from panqake.utils.questionary_prompt import format_branch
from panqake.utils.types import BranchName


def switch_branch_core(
    git: GitPort,
    config: ConfigPort,
    ui: UIPort,
    branch_name: BranchName | None = None,
    show_tree: bool = True,
) -> SwitchResult:
    """Switch to another git branch.

    This is the pure core logic that can be tested without mocking.
    Raises PanqakeError subclasses on failure instead of calling sys.exit.

    Args:
        git: Git operations interface
        config: Stack configuration interface
        ui: User interaction interface
        branch_name: Target branch to switch to (prompts if None)
        show_tree: Whether to display the branch tree before/after switch

    Returns:
        SwitchResult with switch metadata

    Raises:
        BranchNotFoundError: If branch doesn't exist or no branches available
        UserCancelledError: If user cancels a prompt
    """
    current = git.get_current_branch()
    branches = git.list_all_branches()

    if branch_name:
        if branch_name not in branches:
            raise BranchNotFoundError(f"Branch '{branch_name}' does not exist")

        if branch_name == current:
            ui.print_info(f"Already on branch '{branch_name}'")
            return SwitchResult(
                target_branch=branch_name,
                previous_branch=current,
                switched=False,
            )

        worktree_path = git.get_worktree_path(branch_name)
        if worktree_path:
            ui.print_info(
                f"Branch '{branch_name}' is in a worktree. To switch to it, run:"
            )
            ui.print_info(f"cd {worktree_path}")
            return SwitchResult(
                target_branch=branch_name,
                previous_branch=current,
                switched=False,
                worktree_path=worktree_path,
            )

        git.checkout_branch(branch_name)
        return SwitchResult(
            target_branch=branch_name,
            previous_branch=current,
            switched=True,
        )

    if not branches:
        raise BranchNotFoundError("No branches found in repository")

    if show_tree and current:
        root = find_stack_root(current, config)
        ui.display_branch_tree(root, current)
        ui.print_info("")

    selected = ui.prompt_select_branch(
        branches,
        "Select a branch to switch to:",
        current_branch=current,
        exclude_protected=False,
        enable_search=True,
    )

    if not selected:
        ui.print_error("No other branches available to switch to")
        raise BranchNotFoundError("No branches available to switch to")

    worktree_path = git.get_worktree_path(selected)
    if worktree_path:
        ui.print_info(f"Branch '{selected}' is in a worktree. To switch to it, run:")
        ui.print_info(f"cd {worktree_path}")
        return SwitchResult(
            target_branch=selected,
            previous_branch=current,
            switched=False,
            worktree_path=worktree_path,
        )

    git.checkout_branch(selected)

    if show_tree:
        ui.print_info("")
        root = find_stack_root(selected, config)
        ui.display_branch_tree(root, selected)

    return SwitchResult(
        target_branch=selected,
        previous_branch=current,
        switched=True,
    )


def switch_branch(branch_name: BranchName | None = None) -> None:
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
        result = switch_branch_core(
            git=git,
            config=config,
            ui=ui,
            branch_name=branch_name,
        )

        if result.switched:
            ui.print_success(
                f"Switched to branch {format_branch(result.target_branch)}"
            )

    run_command(ui, core)
