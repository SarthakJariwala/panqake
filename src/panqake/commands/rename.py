"""Command for renaming a branch while maintaining stack relationships.

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
    RenameResult,
    UIPort,
    run_command,
)
from panqake.utils.questionary_prompt import BranchNameValidator


def rename_core(
    git: GitPort,
    config: ConfigPort,
    ui: UIPort,
    old_name: str | None = None,
    new_name: str | None = None,
) -> RenameResult:
    """Rename a branch while maintaining its stack relationships.

    This is the pure core logic that can be tested without mocking.
    Raises PanqakeError subclasses on failure instead of calling sys.exit.

    Args:
        git: Git operations interface
        config: Stack configuration interface
        ui: User interaction interface
        old_name: The current name of the branch to rename.
                  If not provided, the current branch will be used.
        new_name: The new name for the branch.
                  If not provided, user will be prompted.

    Returns:
        RenameResult with rename metadata

    Raises:
        BranchNotFoundError: If current branch cannot be determined
        BranchExistsError: If new_name already exists
        GitOperationError: If git rename fails
        UserCancelledError: If user cancels prompt
    """

    if not old_name:
        old_name = git.get_current_branch()
        if not old_name:
            raise BranchNotFoundError("Could not determine the current branch")

    if not new_name:
        validator = BranchNameValidator()
        new_name = ui.prompt_input(
            f"Enter new name for branch '{old_name}': ",
            validator=validator,
        )

    was_tracked = config.branch_exists(old_name)
    was_pushed = git.is_branch_pushed_to_remote(old_name)

    git.rename_branch(old_name, new_name)

    if was_pushed:
        git.delete_remote_branch(old_name)
        git.push_branch(new_name)

    if was_tracked:
        config.rename_branch(old_name, new_name)

    return RenameResult(
        old_name=old_name,
        new_name=new_name,
        was_tracked=was_tracked,
        remote_updated=was_pushed,
    )


def rename(old_name: str | None = None, new_name: str | None = None) -> None:
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
        result = rename_core(
            git=git,
            config=config,
            ui=ui,
            old_name=old_name,
            new_name=new_name,
        )

        ui.print_success(f"Renamed branch '{result.old_name}' to '{result.new_name}'")

        if result.was_tracked:
            ui.print_info("Stack references updated")
        else:
            ui.print_muted("Branch was not tracked by panqake")

        if result.remote_updated:
            ui.print_info("Remote branch updated")

    run_command(ui, core)
