"""Command for modifying/amending commits in the stack."""

import sys
from typing import List

from panqake.utils.config import get_parent_branch
from panqake.utils.git import (
    branch_has_commits,
    get_current_branch,
    get_staged_files,
    get_unstaged_files,
    run_git_command,
)
from panqake.utils.questionary_prompt import (
    print_formatted_text,
    prompt_checkbox,
    prompt_input,
)


def has_staged_changes():
    """Check if there are any staged changes."""
    result = run_git_command(["diff", "--staged", "--name-only"])
    return bool(result and result.strip())


def has_unstaged_changes():
    """Check if there are any unstaged changes."""
    result = run_git_command(["diff", "--name-only"])
    return bool(result and result.strip())


def stage_selected_files(files: List[dict]) -> bool:
    """Stage selected files.

    Args:
        files: List of file detail dictionaries to stage.
               Each dict should have at least a 'path' key.
               For renames/copies, it should also have an 'original_path' key.

    Returns:
        True if staging was successful for all files, False otherwise
    """
    if not files:
        print_formatted_text("[warning]No files selected to stage[/warning]")
        return False

    print_formatted_text("[info]Staging selected files...[/info]")
    all_success = True

    for file_info in files:
        file_path = file_info["path"]  # Main path (new path for rename/copy)
        original_path = file_info.get("original_path")  # Old path for rename/copy

        # Handle renamed/copied files
        if original_path:
            print_formatted_text(
                f"[muted]  Adding renamed/copied file: {original_path} → {file_path}[/muted]"
            )
            # For renamed/copied files, add both the old and new path
            result_old = run_git_command(["add", "--", original_path])
            result_new = run_git_command(["add", "--", file_path])

            if result_old is None or result_new is None:
                print_formatted_text(
                    f"[warning]Error: Failed to stage rename/copy {original_path} → {file_path}[/warning]"
                )
                all_success = False
        else:
            # Handle regular added/modified/deleted files
            print_formatted_text(f"[muted]  Adding {file_path}[/muted]")
            result = run_git_command(["add", "--", file_path])

            if result is None:
                print_formatted_text(
                    f"[warning]Error: Failed to stage {file_path}[/warning]"
                )
                all_success = False

    return all_success


def create_new_commit(message=None):
    """Create a new commit with the staged changes."""
    if not message:
        message = prompt_input("Enter commit message: ")
        if not message:
            print_formatted_text(
                "[warning]Error: Commit message cannot be empty[/warning]"
            )
            sys.exit(1)

    print_formatted_text("[info]Creating new commit...[/info]")
    commit_result = run_git_command(["commit", "-m", message])
    if commit_result is None:
        print_formatted_text("[warning]Error: Failed to create commit[/warning]")
        sys.exit(1)
    print_formatted_text("[success]New commit created successfully[/success]")


def amend_existing_commit(message=None):
    """Amend the existing commit with staged changes."""
    commit_cmd = ["commit", "--amend"]
    if message:
        commit_cmd.extend(["-m", message])
        print_formatted_text("[info]Amending commit with new message...[/info]")
    else:
        print_formatted_text("[info]Amending commit...[/info]")
        # If no message specified, use the existing commit message
        commit_cmd.append("--no-edit")

    commit_result = run_git_command(commit_cmd)
    if commit_result is None:
        print_formatted_text("[warning]Error: Failed to amend commit[/warning]")
        sys.exit(1)
    print_formatted_text("[success]Commit amended successfully[/success]")


def modify_commit(commit_flag=False, message=None, no_amend=False):
    """Modify/amend the current commit or create a new one.

    Args:
        commit_flag: Force creation of a new commit
        message: Commit message to use
        no_amend: Don't amend, always create a new commit
    """
    current_branch = get_current_branch()
    if not current_branch:
        print_formatted_text("[warning]Error: Failed to get current branch[/warning]")
        sys.exit(1)

    print_formatted_text(
        f"[info]Modifying branch[/info]: [branch]{current_branch}[/branch]"
    )

    # Get staged and unstaged files using the new direct functions
    staged_files = get_staged_files()
    unstaged_files = get_unstaged_files()

    # Exit condition: No changes at all
    if not staged_files and not unstaged_files:
        print_formatted_text(
            "[warning]Error: No changes (staged or unstaged) to commit[/warning]"
        )
        sys.exit(1)

    # Inform about staged changes
    if staged_files:
        print_formatted_text("[info]The following changes are already staged:[/info]")
        for file_info in staged_files:
            print_formatted_text(f"[muted]  {file_info['display']}[/muted]")
        print("")  # Add a newline for separation

    newly_staged_paths = []  # Store paths that are successfully staged
    # If there are unstaged files, prompt user to select which to stage
    if unstaged_files:
        print_formatted_text("[info]The following files have unstaged changes:[/info]")

        # Prompt user to select files to stage
        selected_items = prompt_checkbox(
            "Select files to stage (optional):", unstaged_files, default=unstaged_files
        )

        # selected_items will be a list of the selected files' paths
        files_to_stage = selected_items if selected_items else []

        if files_to_stage:
            # Find full file info from the paths
            files_to_stage_info = [
                item for item in unstaged_files if item["path"] in files_to_stage
            ]
            # Stage the selected files
            success = stage_selected_files(files_to_stage_info)
            if success:
                newly_staged_paths = files_to_stage
            else:
                print_formatted_text(
                    "[warning]Warning: Some files could not be staged[/warning]"
                )
        # If no files selected or staging failed, proceed based on initially staged files

    # Determine if we have anything staged TO commit/amend
    # Check if there were initially staged files OR if we just staged some files
    has_anything_staged_now = bool(staged_files) or bool(newly_staged_paths)

    if not has_anything_staged_now:
        print_formatted_text("[warning]No changes staged. Exiting.[/warning]")
        # This covers the case where there were only unstaged changes,
        # and the user chose not to stage any, or staging failed.
        sys.exit(0)

    # Determine if we should create a new commit or amend
    # Create new commit if:
    # 1. commit_flag is True (user explicitly asked for new commit via -c)
    # 2. no_amend is True (user explicitly asked not to amend via --no-amend)
    # 3. branch has no commits yet
    parent_branch = get_parent_branch(current_branch)
    current_branch_has_commits = branch_has_commits(current_branch, parent_branch)
    force_new_commit_flag = commit_flag
    prevent_amend_flag = no_amend

    # Default behavior: amend if possible (branch exists and has commits)
    should_amend = current_branch_has_commits
    reason_for_new_commit = ""

    # Override default based on flags or if branch has no commits
    if force_new_commit_flag:
        should_amend = False
        reason_for_new_commit = "the --commit flag was specified"
    elif prevent_amend_flag:
        should_amend = False
        reason_for_new_commit = "the --no-amend flag was specified"
    elif not current_branch_has_commits:
        should_amend = False  # Can't amend if no commits exist
        reason_for_new_commit = "this branch has no commits yet"

    # Execute the action
    if should_amend:
        amend_existing_commit(message)
    else:
        # If we are creating a new commit, provide a reason unless it's the first commit.
        if reason_for_new_commit:
            print_formatted_text(
                f"[info]Creating a new commit instead of amending because {reason_for_new_commit}[/info]"
            )
        create_new_commit(message)

    # Inform user about how to update the PR
    print_formatted_text(
        "[info]Changes have been committed. To update the remote branch and PR, run:[/info]"
    )
    print_formatted_text(f"[info]  pq submit {current_branch}[/info]")
