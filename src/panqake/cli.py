#!/usr/bin/env python3
"""
Panqake - Git Branch Stacking Utility
A Python implementation of git-stacking workflow management
"""

import argparse
import sys

from panqake.commands.delete import delete_branch
from panqake.commands.list import list_branches
from panqake.commands.merge import merge_branch
from panqake.commands.modify import modify_commit
from panqake.commands.new import create_new_branch
from panqake.commands.pr import create_pull_requests
from panqake.commands.switch import switch_branch
from panqake.commands.sync import sync_with_remote
from panqake.commands.track import track
from panqake.commands.update import update_branches
from panqake.commands.update_pr import update_pull_request
from panqake.utils.config import init_panqake
from panqake.utils.git import is_git_repo, run_git_command
from panqake.utils.questionary_prompt import print_formatted_text


def setup_argument_parsers():
    """Set up argument parsers for the CLI."""
    parser = argparse.ArgumentParser(
        description="Panqake - Git Branch Stacking Utility",
        # Add this to prevent error on unknown args
        allow_abbrev=False,
    )
    subparsers = parser.add_subparsers(dest="command", help="Command to run")

    # new command
    new_parser = subparsers.add_parser("new", help="Create a new branch in the stack")
    new_parser.add_argument(
        "branch_name",
        nargs="?",
        help="Name of the new branch to create",
    )
    new_parser.add_argument(
        "base_branch",
        nargs="?",
        help="Optional base branch (defaults to current branch)",
    )

    # list command
    list_parser = subparsers.add_parser("list", help="List the branch stack")
    list_parser.add_argument(
        "branch_name",
        nargs="?",
        help="Optional branch to start from (defaults to current branch)",
    )

    # update command
    update_parser = subparsers.add_parser(
        "update", help="Update branches after changes and push to remote"
    )
    update_parser.add_argument(
        "branch_name",
        nargs="?",
        help="Optional branch to start from (defaults to current branch)",
    )
    update_parser.add_argument(
        "--no-push",
        action="store_true",
        help="Don't push changes to remote after updating branches",
    )

    # delete command
    delete_parser = subparsers.add_parser(
        "delete", help="Delete a branch and relink the stack"
    )
    delete_parser.add_argument("branch_name", help="Name of the branch to delete")

    # pr command
    pr_parser = subparsers.add_parser("pr", help="Create PRs for the branch stack")
    pr_parser.add_argument(
        "branch_name",
        nargs="?",
        help="Optional branch to start from (defaults to current branch)",
    )

    # switch command
    switch_parser = subparsers.add_parser(
        "switch", help="Interactively switch between branches"
    )
    switch_parser.add_argument(
        "branch_name",
        nargs="?",
        help="Optional branch to switch to (defaults to interactive selection)",
    )

    # track command
    track_parser = subparsers.add_parser(
        "track", help="Track an existing Git branch in the panqake stack"
    )
    track_parser.add_argument(
        "branch_name",
        nargs="?",
        help="Optional branch to track (defaults to current branch)",
    )

    # modify command
    modify_parser = subparsers.add_parser(
        "modify", help="Modify/amend the current commit or create a new one"
    )
    modify_parser.add_argument(
        "-c",
        "--commit",
        action="store_true",
        help="Create a new commit instead of amending",
    )
    modify_parser.add_argument(
        "-m", "--message", help="Commit message for the new or amended commit"
    )
    modify_parser.add_argument(
        "--no-amend",
        action="store_true",
        help="Always create a new commit instead of amending",
    )

    # update-pr command
    update_pr_parser = subparsers.add_parser(
        "update-pr", help="Update remote branch and PR after changes"
    )
    update_pr_parser.add_argument(
        "branch_name",
        nargs="?",
        help="Optional branch to update (defaults to current branch)",
    )

    # merge command
    merge_parser = subparsers.add_parser(
        "merge", help="Merge a PR and manage the branch stack after merge"
    )
    merge_parser.add_argument(
        "branch_name",
        nargs="?",
        help="Optional branch to merge (defaults to current branch)",
    )
    merge_parser.add_argument(
        "--no-delete-branch",
        action="store_true",
        help="Don't delete the local branch after merging",
    )
    merge_parser.add_argument(
        "--no-update-children",
        action="store_true",
        help="Don't update child branches after merging",
    )

    # sync command
    sync_parser = subparsers.add_parser(
        "sync", help="Sync branches with remote repository changes"
    )
    sync_parser.add_argument(
        "main_branch",
        nargs="?",
        default="main",
        help="Trunk/main branch to sync with (defaults to 'main')",
    )

    return parser


def execute_branch_commands(args):
    """Execute branch-related commands."""
    if args.command == "new":
        create_new_branch(args.branch_name, args.base_branch)
    elif args.command == "list":
        list_branches(args.branch_name)
    elif args.command == "delete":
        delete_branch(args.branch_name)
    elif args.command == "switch":
        switch_branch(args.branch_name)
    elif args.command == "track":
        track(args.branch_name)


def execute_update_commands(args):
    """Execute update and synchronization related commands."""
    if args.command == "update":
        update_branches(args.branch_name, skip_push=args.no_push)
    elif args.command == "modify":
        modify_commit(args.commit, args.message, args.no_amend)
    elif args.command == "update-pr":
        update_pull_request(args.branch_name)
    elif args.command == "sync":
        sync_with_remote(args.main_branch)


def execute_pr_commands(args):
    """Execute PR related commands."""
    if args.command == "pr":
        create_pull_requests(args.branch_name)
    elif args.command == "merge":
        merge_branch(
            args.branch_name, not args.no_delete_branch, not args.no_update_children
        )


def execute_command(args):
    """Execute the appropriate command based on args."""
    # Group 1: Branch management commands
    if args.command in ["new", "list", "delete", "switch", "track"]:
        execute_branch_commands(args)
    # Group 2: Update and synchronization commands
    elif args.command in ["update", "modify", "update-pr", "sync"]:
        execute_update_commands(args)
    # Group 3: PR related commands
    elif args.command in ["pr", "merge"]:
        execute_pr_commands(args)


def main():
    """Main entry point for the panqake CLI."""
    # Check if any arguments were provided
    if len(sys.argv) <= 1:
        # No arguments, show help
        parser = setup_argument_parsers()
        parser.print_help()
        return

    # Get the first argument (potential command)
    potential_command = sys.argv[1]

    # Define the list of known commands
    known_commands = [
        "new",
        "list",
        "update",
        "delete",
        "pr",
        "switch",
        "track",
        "modify",
        "update-pr",
        "merge",
        "sync",
    ]

    # Initialize panqake directory and files
    init_panqake()

    # Check if we're in a git repository
    if not is_git_repo():
        print("Error: Not in a git repository")
        sys.exit(1)

    # If the potential command is known, use argparse normally
    if potential_command in known_commands:
        parser = setup_argument_parsers()
        args = parser.parse_args()
        execute_command(args)
    # Otherwise, pass all arguments to git
    else:
        print_formatted_text("<info>Passing command to git...</info>")
        result = run_git_command(sys.argv[1:])
        if result is not None:
            print(result)


if __name__ == "__main__":
    main()
