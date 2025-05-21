# Quick Start Guide

This guide will walk you through a typical workflow using Panqake to manage a stack of branches and pull requests.

::: tip
Most of the commands you see in `panqake` are interactive, i.e. if you don't pass any arguments to the command, it will prompt you interactively.

So, in most cases, you will only have to pass the command `pq [COMMAND]`
:::

## Basic Workflow

Here's a typical workflow for building a stack of dependent features:

### 1. Create your first feature branch

```bash
pq new
```

This will prompt you for the name of you new branch and suggest a parent based on your current branch.

```
Enter new branch name: auth-backend
Enter parent branch: main
```

This creates a new branch called `auth-backend` based on `main`.

### 2. Make changes and commit them

```bash
# Edit files...

# Commit your changes
pq modify -m "Implement JWT authentication"
```

The `modify` command will stage your changes and intelligently create a commit if none exists or amend an existing one.

::: tip
You can force it to create new commit every time by passing `-c` or `--commit` flag: `pq modify -c`
:::

### 3. Push to remote and submit your changes for review

```bash
pq submit
```

The submit command will push the current changes to remote, create a remote branch if required, and prompt you if you want to create a new pull request for the branch.

::: info
Pull request creation feature requires `gh` CLI to be installed. See [installation](/installation) for more info.
:::

### 4. Create a dependent branch for the next feature

You are now waiting for your colleague to review your code.

But, the benefits of git stacking means that you don't have to wait for them to finish reviewing to continue your work. You can just carry forward!

Let's work on feature that is dependent on our previous work.

```bash
pq new auth-frontend
```

::: info
You can also just pass the branch name in arguments.
:::

This creates a new branch `auth-frontend` based on `auth-backend`.

### 5. Make changes on the new branch

```bash
# Edit files...

# Commit your changes
pq modify -m "Add login form UI"
```

Since this is a new branch, `pq modify` will intelligently create a new commit without specifying `-c` flag.

### 6. Submit our new branch for review

```bash
pq submit
```

Like before, it will again ask you if you also want to create a pull request for this new branch.

### 7. Fix something in the parent branch

By the time, we were done submitting our new branch, our reviewer has come back to us with some feedback for the first pull request (`auth-backend`).

```bash
# Switch back to the parent branch
pq switch auth-backend
```

::: tip Tip #1
If you have already forgotten the name of the branch, you can simply type `pq switch` or `pq co` for shorthand and `panqake` will let you interactively select the branch!
:::

::: tip Another tip
You can also use `pq up` and `pq down` to easily move up and down your branch hierarchy. You can learn more about it [below](##Navigating-Your-Stack).
:::

```bash
# Make your changes
# Edit files...

# Stage and commit the fixes
pq modify
```

Note, since we did not specify the `-c` or `--commit` flag, it amends the existing commit.

```bash
# Re-submit the modifications
pq submit
```

### 8. Update your child branches

Now, we need to update all child branches with changes from the current branch (`auth-backend`).

In vanilla git, you would have to remember which branch was branched off of which parent branch. But, since `panqake` knows about the parent-child relationships in your stack, you only need to run one command and it will manage the update for you.

```bash
pq update
```

After updating child branch, we will push the changes to remote.

```bash
# Move to child branch
pq down

# Submit changes to remote
pq submit
```

### 9. When a PR is approved, merge it

Now, your reviewers are happy with the changes you made on `auth-backend` and have approved your pull request.

It's time to merge it!

```bash
# Merge the approved PR and update the stack
pq merge auth-backend
```

This merges the PR for the branch and updates any children.

In this case, it merges the PR for `auth-backend` and updates `auth-frontend` PR to `auth-backend` branch's parent (`main`). It also updates the relationship locally.

## Visualizing Your Stack

To see the current structure of your branch stack:

```bash
pq list
# or the shorthand
pq ls
```

This displays a tree view of all branches in your stack.

Before merge:

```bash
main
└── auth-backend
        └── auth-frontend
```

After merge:

```bash
main
└── auth-frontend
```

## Navigating Your Stack

```bash
# Move up to the parent branch
pq up

# Move down to a child branch
pq down
# If there are multiple children, you'll be prompted to select one

# Switch to any branch in the stack
pq switch branch-name
# or the shorthand
pq co branch-name
```

## Syncing with Remote Changes

You and your colleagues will be continuously updating and merging changes to `main`. To keep your branch stack up to date with remote changes:

```bash
# Sync with remote main and update stack
pq sync
```

## Managing Branch Stack

```bash
# Rename a branch while preserving stack relationships
pq rename old-name new-name

# Add an existing branch to your stack
# (Not currently tracked using panqake)
pq track existing-branch

# Remove a branch from the panqake stack (without deleting the git branch)
pq untrack branch-name

# Delete a branch while updating the stack relationships of children
pq delete branch-name
```

## Next Steps

Now that you understand the basic workflow:

- Explore the [Commands Reference](/commands/index) for detailed information about each command
- Check out the [Advanced Workflows](/advanced-workflows) section for more complex scenarios
