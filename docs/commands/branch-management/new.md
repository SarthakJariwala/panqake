# `new`

The `new` command creates a new branch based on your current or another branch, tracks the parent-child relationship, and automatically checks out the new branch

`new` command is the foundation of building a stack, allowing you to create branches that build on each other.

## Usage

```bash
pq new
```

## Arguments

| Argument | Description |
|----------|-------------|
| `branch-name` | The name for the new branch (optional) |
| `parent-branch` | The name for the parent branch (optional) |

## Examples

### Creating Your First Branch

```bash
pq new

Enter your branch name: feature-backend
Enter base branch: main

Created new branch 'feature-backend' based on 'main'
Switched to branch 'feature-backend'
```

### Building on an Existing Branch

When already on a feature branch:

```bash
pq new feature-auth

Created new branch 'feature-auth' based on 'feature-backend'
Switched to branch 'feature-auth'
```
