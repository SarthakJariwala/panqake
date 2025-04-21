# Git Stacking Discussion

## What is Git Stacking?

Git stacking (or stacked diffs/PRs) is a development workflow where large code changes are broken into multiple smaller, interdependent pull requests (PRs) that can be reviewed and merged incrementally.

Key aspects:
- Instead of creating one large PR, developers create multiple small, sequential PRs
- Each subsequent PR builds upon the previous one
- Developers can continue working while waiting for reviews
- Uses interactive rebasing to manage dependencies between PRs

## Manual Implementation with Git

To implement git-stacking manually with Git:

1. Create a base branch from main
2. Make your first change set, commit
3. Create subsequent branches from each previous stack branch
4. When changes are requested on earlier branches, rebase dependent branches
5. Use interactive rebasing to manage the stack when upstream branches change
6. Track dependencies between branches to maintain proper ordering

## Shell Utilities for Git Stacking

To implement git-stacking as shell utilities:

1. Write scripts for creating new stack branches 
2. Create commands to handle rebasing after changes
3. Build utilities to visualize the stack structure
4. Implement tools to track branch dependencies
5. Create helpers for updating branches when their dependencies change
6. Add commands for submitting PRs in the correct order

These utilities would wrap Git commands in Bash scripts with appropriate error handling and clear user interfaces.

## Benefits

- Enables continuous parallel development
- Reduces PR review bottlenecks
- Makes code reviews more manageable
- Allows engineers to stay "in the flow" without waiting for full feature approval
- Facilitates easier testing and potential reversion of individual changes

## Challenges

- Requires more advanced git skills, particularly interactive rebasing
- Needs specialized tooling for smooth implementation
- More complex workflow compared to traditional branching