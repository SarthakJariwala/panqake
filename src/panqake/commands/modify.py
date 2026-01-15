"""Command for modifying/amending commits in the stack.

Uses dependency injection for testability.
Core logic is pure - no sys.exit, no direct filesystem/git calls.
"""

from panqake.ports import (
    CommitError,
    ConfigPort,
    GitPort,
    ModifyResult,
    NoChangesError,
    RealConfig,
    RealGit,
    RealUI,
    UIPort,
    run_command,
)


def modify_commit_core(
    git: GitPort,
    config: ConfigPort,
    ui: UIPort,
    commit_flag: bool = False,
    message: str | None = None,
    no_amend: bool = False,
) -> ModifyResult:
    """Modify/amend the current commit or create a new one.

    This is the pure core logic that can be tested without mocking.
    Raises PanqakeError subclasses on failure instead of calling sys.exit.

    Args:
        git: Git operations interface
        config: Stack configuration interface
        ui: User interaction interface
        commit_flag: Force creation of a new commit
        message: Commit message to use
        no_amend: Don't amend, always create a new commit

    Returns:
        ModifyResult with commit metadata

    Raises:
        NoChangesError: If no staged or unstaged changes exist
        CommitError: If commit/amend fails
        UserCancelledError: If user cancels a prompt
    """
    current_branch = git.get_current_branch()
    if not current_branch:
        raise NoChangesError("Failed to get current branch")

    staged_files = git.get_staged_files()
    unstaged_files = git.get_unstaged_files()

    if not staged_files and not unstaged_files:
        raise NoChangesError("No changes (staged or unstaged) to commit")

    ui.print_info(f"Modifying branch: {current_branch}")

    if staged_files:
        ui.print_info("The following changes are already staged:")
        for file_info in staged_files:
            ui.print_muted(f"  {file_info.display}")

    files_staged: list[str] = []

    if unstaged_files:
        ui.print_info("The following files have unstaged changes:")
        for file_info in unstaged_files:
            ui.print_muted(f"  {file_info.display}")

        selected_paths = ui.prompt_select_files(
            unstaged_files,
            "Select files to stage (optional):",
            default_all=True,
        )

        if selected_paths:
            files_to_stage = [f for f in unstaged_files if f.path in selected_paths]
            git.stage_files(files_to_stage)
            files_staged = selected_paths

    has_anything_staged = bool(staged_files) or bool(files_staged)

    if not has_anything_staged:
        raise NoChangesError("No changes staged")

    parent_branch = config.get_parent_branch(current_branch)
    branch_has_commits = git.branch_has_commits(current_branch, parent_branch)

    should_amend = branch_has_commits
    reason_for_new_commit = ""

    if commit_flag:
        should_amend = False
        reason_for_new_commit = "the --commit flag was specified"
    elif no_amend:
        should_amend = False
        reason_for_new_commit = "the --no-amend flag was specified"
    elif not branch_has_commits:
        should_amend = False
        reason_for_new_commit = "this branch has no commits yet"

    commit_message = message

    if should_amend:
        git.amend_commit(commit_message)
        return ModifyResult(
            branch_name=current_branch,
            amended=True,
            files_staged=files_staged,
            message=commit_message,
        )
    else:
        if reason_for_new_commit:
            ui.print_info(
                f"Creating a new commit instead of amending because {reason_for_new_commit}"
            )

        if not commit_message:
            commit_message = ui.prompt_input("Enter commit message: ")
            if not commit_message:
                raise CommitError("Commit message cannot be empty")

        git.commit(commit_message)
        return ModifyResult(
            branch_name=current_branch,
            amended=False,
            files_staged=files_staged,
            message=commit_message,
        )


def modify_commit(
    commit_flag: bool = False, message: str | None = None, no_amend: bool = False
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

    def core() -> None:
        result = modify_commit_core(
            git=git,
            config=config,
            ui=ui,
            commit_flag=commit_flag,
            message=message,
            no_amend=no_amend,
        )

        if result.amended:
            ui.print_success("Commit amended successfully")
        else:
            ui.print_success("New commit created successfully")

        ui.print_info(
            "Changes have been committed. To update the remote branch and PR, run:"
        )
        ui.print_info(f"  pq submit {result.branch_name}")

    run_command(ui, core)
