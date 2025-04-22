"""Command for modifying/amending commits in the stack."""

import sys

from panqake.utils.git import get_current_branch, run_git_command
from panqake.utils.questionary_prompt import (
    print_formatted_text,
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


def stage_all_changes():
    """Stage all unstaged changes."""
    print_formatted_text("<info>Staging changes...</info>")
    stage_result = run_git_command(["add", "."])
    if stage_result is None:
        print_formatted_text("<warning>Error: Failed to stage changes</warning>")
        sys.exit(1)


def create_new_commit(message=None):
    """Create a new commit with the staged changes."""
    if not message:
        message = prompt_input("Enter commit message: ")
        if not message:
            print_formatted_text(
                "<warning>Error: Commit message cannot be empty</warning>"
            )
            sys.exit(1)

    print_formatted_text("<info>Creating new commit...</info>")
    commit_result = run_git_command(["commit", "-m", message])
    if commit_result is None:
        print_formatted_text("<warning>Error: Failed to create commit</warning>")
        sys.exit(1)
    print_formatted_text("<success>New commit created successfully</success>")


def amend_existing_commit(message=None):
    """Amend the existing commit with staged changes."""
    commit_cmd = ["commit", "--amend"]
    if message:
        commit_cmd.extend(["-m", message])
        print_formatted_text("<info>Amending commit with new message...</info>")
    else:
        print_formatted_text("<info>Amending commit...</info>")
        # If no message specified, use the existing commit message
        commit_cmd.append("--no-edit")

    commit_result = run_git_command(commit_cmd)
    if commit_result is None:
        print_formatted_text("<warning>Error: Failed to amend commit</warning>")
        sys.exit(1)
    print_formatted_text("<success>Commit amended successfully</success>")


def modify_commit(commit_flag=False, message=None):
    """Modify/amend the current commit or create a new one."""
    current_branch = get_current_branch()
    if not current_branch:
        print_formatted_text("<warning>Error: Failed to get current branch</warning>")
        sys.exit(1)

    print_formatted_text("<info>Modifying branch</info>")
    print_formatted_text(f"<branch>{current_branch}</branch>")
    print("")

    # Check if there are any changes
    if not has_staged_changes() and not has_unstaged_changes():
        print_formatted_text("<warning>Error: No changes to commit</warning>")
        sys.exit(1)

    # Stage all unstaged changes if there are any
    if has_unstaged_changes():
        stage_all_changes()

    # Create a new commit or amend existing one
    if commit_flag:
        create_new_commit(message)
    else:
        amend_existing_commit(message)

    # Inform user about how to update the PR
    print_formatted_text(
        "<info>Changes have been committed. To update the remote branch and PR, run:</info>"
    )
    print_formatted_text(f"<info>  pq update-pr {current_branch}</info>")
