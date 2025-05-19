# Introduction to Panqake

## What is Git Stacking?

Git stacking or stacked diffs is a development workflow where large code changes are broken into multiple smaller, interdependent pull requests that can be reviewed and merged incrementally.

Instead of creating one large PR, you create multiple small, sequential PRs where each subsequent PR builds upon the previous one.

For example, consider a feature that requires data models, authentication, and UI components. You might start with a backend PR, followed by an authentication PR, and finally an authentication UI PR.

A git stacked workflow for this feature might look like:

```bash
main
└── feature-data-models
        └── feature-auth
                └── feature-auth-ui
```

::: details What's a "diff"?

A "diff" refers to the difference between two versions of code - essentially what changes were made. In Git, this is what you see when you run `git diff`.

*In stacked workflows, each "diff" becomes a separate PR.*

:::

## Why use Git Stacking?

::: warning The Problem: Large Pull Requests

Large pull requests create several problems in the development process:

- **Review bottlenecks**: Large PRs take longer to review. No one wants to review a 1000 line PR
- **Context complexity**: Reviewers struggle to understand extensive changes
- **Stalled development**: Dependent work is blocked while waiting for approval

:::

### Benefits of Stacked Diffs

Stacked diffs offer numerous advantages:

- **Faster reviews**: Smaller, focused PRs are quicker and easier to review
- **Continuous development**: Continue working on dependent changes while waiting for reviews
- **Incremental merging**: Get value to production faster by merging parts as they're approved
- **Clearer context**: Each PR focuses on a single logical change
- **Better quality**: More thorough reviews of smaller, focused changes
- **Reduced merge conflicts**: Frequent integration reduces conflict complexity

## The Challenge with Manual Stacked Workflows

You can do git stacking manually with vanilla git operations, and while beneficial, it has its challenges:

- **Complex rebasing**: When changes are requested on earlier branches, all dependent branches must be rebased
- **Dependency tracking**: Maintaining the correct order of branches and PRs is error-prone
- **PR management**: Updating PR descriptions and references gets tedious
- **Branch synchronization**: Keeping branches updated with remote changes becomes complex
- **Advanced Git knowledge**: Requires expertise in interactive rebasing and branch management

## How Panqake Solves These Challenges

Panqake is a CLI tool that automates the entire git-stacking workflow, making it accessible to developers of all experience levels:

- **Simplified branch creation**: One command to create properly tracked branches with parent-child relationships
- **Automated rebasing**: Update all dependent branches with a single command
- **Branch relationship tracking**: Visualize and manage your branch hierarchy easily
- **PR integration**: Create, update, and merge PRs for your entire stack seamlessly
- **Conflict resolution**: Handle merge conflicts in a structured way
- **Stack visualization**: See your entire branch stack with simple commands

With Panqake, you can focus on writing code instead of managing complex Git operations.

## Next Steps

- [Installation and Setup](/installation): Get started with Panqake
- [Quick Start Guide](/quickstart): Learn the basic workflow
- [Commands Reference](/commands): Explore all available commands
