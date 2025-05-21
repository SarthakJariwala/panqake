# `new`

The `new` command creates a new branch based on your current or another branch, tracks the parent-child relationship, and automatically checks out the new branch. This is the foundation of building a stack, allowing you to create branches that build on each other.

## Usage

```bash
pq new [BRANCH_NAME] [BASE_BRANCH]
```

## Arguments

| Argument | Description |
|----------|-------------|
| `BRANCH_NAME` | Name of the new branch (optional) |
| `BASE_BRANCH` | Parent branch (optional) |

## Examples

### Interactively Creating a Branch

```bash
pq new
```

### Specifying Branch Name and Parent

```bash
pq new feature-backend main
```

### Building on an Existing Branch

When already on a feature branch:

```bash
pq new feature-auth
```
