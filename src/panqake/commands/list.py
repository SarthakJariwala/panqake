"""Command for listing branches in the stack.

Uses dependency injection for testability.
Core logic is pure - no sys.exit, no direct filesystem/git calls.
"""

from panqake.ports import (
    BranchNotFoundError,
    ConfigPort,
    GitPort,
    ListResult,
    RealConfig,
    RealGit,
    RealUI,
    UIPort,
    find_stack_root,
    run_command,
)
from panqake.utils.types import BranchName


def list_branches_core(
    git: GitPort,
    config: ConfigPort,
    ui: UIPort,
    branch_name: BranchName | None = None,
) -> ListResult:
    """List the branch stack.

    This is the pure core logic that can be tested without mocking.

    Args:
        git: Git operations interface
        config: Stack configuration interface
        ui: User interaction interface
        branch_name: Target branch to show stack for (uses current if None)

    Returns:
        ListResult with the root, current, and target branches

    Raises:
        BranchNotFoundError: If branch doesn't exist or no current branch
    """
    current = git.get_current_branch()
    if not current:
        raise BranchNotFoundError("Could not determine current branch")

    if branch_name:
        if not git.branch_exists(branch_name):
            raise BranchNotFoundError(f"Branch '{branch_name}' does not exist")
        target = branch_name
    else:
        target = current

    root_branch = find_stack_root(target, config)

    ui.display_branch_tree(root_branch, current)

    return ListResult(
        root_branch=root_branch,
        current_branch=current,
        target_branch=target,
    )


def list_branches(branch_name: BranchName | None = None) -> None:
    """CLI entrypoint that wraps core logic with real implementations.

    This thin wrapper:
    1. Instantiates real dependencies
    2. Calls the core logic
    3. Converts exceptions to sys.exit via run_command
    """
    git = RealGit()
    config = RealConfig()
    ui = RealUI()

    def core() -> None:
        list_branches_core(
            git=git,
            config=config,
            ui=ui,
            branch_name=branch_name,
        )

    run_command(ui, core)
