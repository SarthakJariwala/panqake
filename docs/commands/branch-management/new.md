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
| `--worktree-script` | Executable to create the worktree instead of Git (implies `--tree`) |

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

### Using a worktree creation script

Interactive worktree creation also asks for an optional script. Leave it blank to
use Git, or supply an executable path. To supply all inputs without prompts:

```bash
pq new feature-auth main --path ../feature-auth --worktree-script ./worktree.sh --json
```

Panqake runs the script from your current directory with three positional arguments:
the new branch name, the absolute worktree path, and the base branch. Relative
script paths resolve from your current directory. The script replaces the entire
creation step and must create a Git worktree on the requested branch at that path.
For example, `worktree.sh` can create the worktree and copy an untracked local file:

```sh
#!/bin/sh
set -eu
git worktree add -b "$1" "$2" "$3"
cp .env "$2/.env"
```

Make the script executable with `chmod +x worktree.sh`. Only run scripts you trust.
The script runs without terminal input. Its output is discarded,
so script output does not expose local secrets or corrupt JSON. Have the
script write its own log if needed for debugging.

Panqake records the stack relationship only after the script succeeds and the
requested worktree is registered with Git. On failure, it leaves any partial files
or branches in place for you to inspect. It does not fall back to Git creation.

With `--json`, omitting `--worktree-script` uses Git without prompting. Outside JSON
mode, use `--worktree-script ''` to skip the script prompt and use Git.
