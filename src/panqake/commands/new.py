"""Command for creating a new branch in the stack.

Uses dependency injection for testability.
Core logic is pure - no sys.exit, no direct filesystem/git calls.
"""

from pathlib import Path

from panqake.ports import (
    BranchExistsError,
    BranchNotFoundError,
    ConfigPort,
    FilesystemPort,
    GitPort,
    NewBranchResult,
    RealConfig,
    RealFilesystem,
    RealGit,
    RealUI,
    UIPort,
    WorktreeError,
    run_command,
)
from panqake.utils.questionary_prompt import BranchNameValidator, format_branch
from panqake.utils.types import BranchName


def create_new_branch_core(
    git: GitPort,
    config: ConfigPort,
    ui: UIPort,
    fs: FilesystemPort,
    branch_name: BranchName | None = None,
    base_branch: BranchName | None = None,
    use_worktree: bool = False,
    worktree_path: str | None = None,
) -> NewBranchResult:
    """Create a new branch in the stack.

    This is the pure core logic that can be tested without mocking.
    Raises PanqakeError subclasses on failure instead of calling sys.exit.

    Args:
        git: Git operations interface
        config: Stack configuration interface
        ui: User interaction interface
        fs: Filesystem operations interface
        branch_name: Name for the new branch (prompts if None)
        base_branch: Parent branch to base off (prompts if None)
        use_worktree: Whether to create in a worktree
        worktree_path: Explicit worktree path (prompts if None and use_worktree=True)

    Returns:
        NewBranchResult with branch metadata

    Raises:
        BranchExistsError: If branch_name already exists
        BranchNotFoundError: If base_branch doesn't exist
        WorktreeError: If worktree creation fails
        UserCancelledError: If user cancels a prompt
    """
    # Resolve branch name
    if not branch_name:
        validator = BranchNameValidator()
        branch_name = ui.prompt_input("Enter new branch name: ", validator=validator)

    # Check new branch doesn't already exist (before prompting for base)
    if git.branch_exists(branch_name):
        raise BranchExistsError(f"Branch '{branch_name}' already exists")

    # Resolve base branch
    current = git.get_current_branch()
    if not base_branch:
        base_branch = current
        branches = git.list_all_branches()
        if branches:
            base_branch = ui.prompt_input(
                f"Enter base branch [default: {current or ''}]: ",
                completer=branches,
                default=current or "",
            )

    # Validate base branch exists
    if not base_branch:
        raise BranchNotFoundError("Base branch is required")

    git.validate_branch(base_branch)

    # Handle worktree path resolution
    resolved_worktree_path: str | None = None
    if use_worktree:
        default_path = str(Path.cwd().parent / branch_name)

        if worktree_path:
            input_path = worktree_path
        else:
            input_path = ui.prompt_path("Enter worktree path", default=default_path)

        # Resolve path using filesystem port
        expanded_path = fs.resolve_path(input_path)

        # If input ends with / or is an existing directory, append branch name
        if (
            input_path.endswith("/")
            or input_path.endswith("\\")
            or (fs.path_exists(expanded_path) and fs.is_directory(expanded_path))
        ):
            resolved_worktree_path = fs.resolve_path(f"{expanded_path}/{branch_name}")
        else:
            resolved_worktree_path = expanded_path

        if fs.path_exists(resolved_worktree_path):
            raise WorktreeError(f"Directory '{resolved_worktree_path}' already exists")

    # Execute the branch creation
    if use_worktree and resolved_worktree_path:
        git.add_worktree(branch_name, resolved_worktree_path, base_branch)
        config.add_to_stack(branch_name, base_branch, resolved_worktree_path)

        return NewBranchResult(
            branch_name=branch_name,
            base_branch=base_branch,
            worktree_path=resolved_worktree_path,
        )
    else:
        git.create_branch(branch_name, base_branch)
        config.add_to_stack(branch_name, base_branch)

        return NewBranchResult(
            branch_name=branch_name,
            base_branch=base_branch,
        )


def create_new_branch(
    branch_name: BranchName | None = None,
    base_branch: BranchName | None = None,
    use_worktree: bool = False,
    worktree_path: str | None = None,
) -> None:
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
    fs = RealFilesystem()

    def core() -> None:
        result = create_new_branch_core(
            git=git,
            config=config,
            ui=ui,
            fs=fs,
            branch_name=branch_name,
            base_branch=base_branch,
            use_worktree=use_worktree,
            worktree_path=worktree_path,
        )

        # Print success output
        if result.worktree_path:
            ui.print_success(
                f"Created new branch '{result.branch_name}' "
                f"in worktree at '{result.worktree_path}'"
            )
        else:
            ui.print_success(f"Created new branch '{result.branch_name}' in the stack")

        ui.print_info(f"Parent branch: {format_branch(result.base_branch)}")

        if result.worktree_path:
            ui.print_info("\nTo switch to the new worktree, run:")
            ui.print_info(f"cd {result.worktree_path}")

    run_command(ui, core)
