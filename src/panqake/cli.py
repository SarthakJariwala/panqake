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
from panqake.commands.update import update_branches
from panqake.commands.update_pr import update_pull_request
from panqake.utils.config import init_panqake
from panqake.utils.git import is_git_repo


def setup_argument_parsers():
    """Set up argument parsers for the CLI."""
    parser = argparse.ArgumentParser(
        description="Panqake - Git Branch Stacking Utility"
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

    return parser


def execute_command(args):
    """Execute the appropriate command based on args."""
    if args.command == "new":
        create_new_branch(args.branch_name, args.base_branch)
    elif args.command == "list":
        list_branches(args.branch_name)
    elif args.command == "update":
        update_branches(args.branch_name, skip_push=args.no_push)
    elif args.command == "delete":
        delete_branch(args.branch_name)
    elif args.command == "pr":
        create_pull_requests(args.branch_name)
    elif args.command == "switch":
        switch_branch(args.branch_name)
    elif args.command == "modify":
        modify_commit(args.commit, args.message)
    elif args.command == "update-pr":
        update_pull_request(args.branch_name)
    elif args.command == "merge":
        merge_branch(
            args.branch_name, not args.no_delete_branch, not args.no_update_children
        )


def main():
    """Main entry point for the panqake CLI."""
    parser = setup_argument_parsers()
    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return

    # Initialize panqake directory and files
    init_panqake()

    # Check if we're in a git repository
    if not is_git_repo():
        print("Error: Not in a git repository")
        sys.exit(1)

    # Execute the appropriate command
    execute_command(args)


if __name__ == "__main__":
    main()
