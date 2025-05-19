# Advanced Workflows

## Working on Multiple Features Simultaneously

Stacked diffs excel when you need to work on multiple interdependent features at the same time:

```bash
# Start from main
git checkout main

# Create the first feature branch
pq new auth-backend

# Make changes to implement backend authentication
pq modify -m "Implement JWT authentication backend"

# Submit your changes for review
pq submit

#### Work on the next dependent feature

# Create a branch for the frontend authentication
pq new auth-frontend
# Make changes for the login UI
pq modify -m "Add login form and authentication UI"
# Submit your changes for review
pq submit

#### Work on another independent feature

# Create another independent feature branch from main
pq switch main
pq new api-refactor
# Make changes to refactor API
pq modify -m "Refactor API endpoints for better organization"
# Submit your changes
pq submit

# Now you have two separate feature stacks
pq list
# main
#   ├── auth-backend
#   │      └── auth-frontend
#   └── api-refactor
```

This allows you to work on multiple feature paths simultaneously without them interfering with each other.

## Handling Review Feedback

When you receive feedback on a PR that requires changes:

```bash
# Switch to the branch that needs changes
pq co auth-backend
# `pq co` is shorthand for `pq switch`

# Make the requested changes
# Edit files...

# Stage and commit the changes and update the PR
pq modify
pq submit

# Update any child branches with these changes
pq update

# This will ensure that auth-frontend gets the reviewer requested improvements too
```

## Mid-Stack Changes

Sometimes you need to make changes to a branch in the middle of your stack:

```bash
# Starting with a stack like:
# main
#   └── feature-base
#           └── feature-middleware
#                   └── feature-ui (current)

# Go to the middle branch
pq up
# OR
pq switch feature-middleware

# Make necessary changes
# Edit files...

# Commit the changes
pq modify --commit -m "Add request validation middleware"

# Update child branches with your changes
pq update

# Now feature-ui includes your middleware changes
```

## Collaborative Stack Work

When multiple developers are working on the same stack:

```bash
# First, sync with the latest changes
pq sync

# Create your branch based on a colleague's branch
pq switch teammate-feature
pq new my-feature
# Make changes
pq modify -m "Add my feature building on teammate's work"

# Submit changes and create PR
pq submit

# When teammate's PR gets merged:
pq merge teammate-feature
# Your branch will now be based directly on main
# and your PR will update automatically
```

## Refactoring Workflow Example

For a major refactoring that touches many parts of the codebase:

```bash
# Create a base refactoring branch
git checkout main
pq new refactor-base
# Make foundational changes
pq modify -m "Refactor core data structures"
pq submit

# Create branches for each affected subsystem
pq new refactor-api
# Make API-specific changes
pq modify -m "Update API to use new data structures"
pq submit

# Create a branch for updating tests
pq switch refactor-base
pq new refactor-tests
# Update tests
pq modify -m "Update tests for new data structures"
pq submit

# Create branch for documentation updates
pq switch refactor-base
pq new refactor-docs
# Update docs
pq modify -m "Update documentation for new data structures"
pq submit

# Now you have a cleaner breakdown of your refactoring
pq list
# main
#   └── refactor-base
#           ├── refactor-api
#           ├── refactor-tests
#           └── refactor-docs
```

This approach makes the refactoring more manageable for both you and your reviewers.

## Integrating with CI/CD Workflows

When you need to ensure CI passes before merging:

```bash
# Create and develop your branches as usual
pq new feature
# Make changes
pq modify -m "Implement new feature"

# Submit for CI testing
pq submit

# If CI fails, make fixes
# Edit files...
pq modify --commit -m "Fix failing tests"

# Resubmit
pq submit

# Once CI passes and review is approved
pq merge feature
```

## Handling Hotfixes

When you need to create a hotfix while in the middle of feature work:

```bash
# Switch to main
pq switch main

# Create hotfix branch
pq new hotfix-critical-bug
# Fix the bug
pq modify -m "Fix critical production bug"

# Create PR and merge after review
pq submit
pq merge hotfix-critical-bug

# Return to your feature work and sync with the hotfix
pq switch feature-in-progress
pq sync
```

These advanced workflows demonstrate the flexibility of `panqake` in handling complex development scenarios. By breaking work into smaller, focused branches, you can simplify review, reduce merge conflicts, and increase development velocity.
