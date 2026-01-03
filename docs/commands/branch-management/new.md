# `new`

The `new` command creates a new branch based on your current or another branch, tracks the parent-child relationship, and automatically checks out the new branch. This is the foundation of building a stack, allowing you to create branches that build on each other.

## Usage

```bash
pq new [BRANCH_NAME] [BASE_BRANCH] [OPTIONS]
```

## Arguments

| Argument | Description |
|----------|-------------|
| `BRANCH_NAME` | Name of the new branch (optional) |
| `BASE_BRANCH` | Parent branch (optional) |

## Options

| Option | Description |
|--------|-------------|
| `--tree` | Create branch in a new git worktree |
| `--path`, `-p` | Custom path for the worktree (implies `--tree`) |

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

### Creating a Branch in a Worktree

Create a branch in a separate worktree directory. You'll be prompted for branch name, base branch, and worktree path (defaults to sibling of current repo):

```bash
pq new --tree
```

### Specifying Custom Worktree Path

Specify the path upfront and fill in branch details interactively:

```bash
pq new --path ~/projects/
# Creates worktree at ~/projects/<branch-name>
```

Paths ending with `/` or pointing to existing directories automatically append the branch name:

```bash
pq new --path ../
# Creates worktree at ../<branch-name>
```
