#!/usr/bin/env python3
"""
Panqake - Git Branch Stacking Utility
A Python implementation of git-stacking workflow management
"""

import argparse
import sys

from panqake.commands.delete import delete_branch
from panqake.commands.list import list_branches
from panqake.commands.new import create_new_branch
from panqake.commands.pr import create_pull_requests
from panqake.commands.switch import switch_branch
from panqake.commands.update import update_branches
from panqake.utils.config import init_panqake
from panqake.utils.git import is_git_repo


def main():
    """Main entry point for the panqake CLI."""
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
        "update", help="Update branches after changes"
    )
    update_parser.add_argument(
        "branch_name",
        nargs="?",
        help="Optional branch to start from (defaults to current branch)",
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
    if args.command == "new":
        create_new_branch(args.branch_name, args.base_branch)
    elif args.command == "list":
        list_branches(args.branch_name)
    elif args.command == "update":
        update_branches(args.branch_name)
    elif args.command == "delete":
        delete_branch(args.branch_name)
    elif args.command == "pr":
        create_pull_requests(args.branch_name)
    elif args.command == "switch":
        switch_branch(args.branch_name)


if __name__ == "__main__":
    main()
