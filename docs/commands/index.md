# Commands Reference

Panqake provides a comprehensive set of commands to manage your branch stack and pull requests, organized here by their function.

::: info Command Aliases
Panqake provides both `panqake` and `pq` commands. They are functionally identical, with `pq` serving as a convenient shorthand.
:::

## Command Categories

Panqake commands are organized into four main categories:

### Navigation Commands

Used to navigate and visualize your branch stack:

| Command | Alias | Description |
|---------|-------|-------------|
| [`list`](./navigation/list.md) | `ls` | Displays all branches in the stack with their relationships |
| [`switch`](./navigation/switch.md) | `co` | Switches to another branch in the stack |
| [`up`](./navigation/up.md) | | Moves up from current branch to its parent |
| [`down`](./navigation/down.md) | | Moves down from current branch to a child branch |

### Branch Management Commands

Used to create, delete, and manage branches in your stack:

| Command | Description |
|---------|-------------|
| [`new`](./branch-management/new.md) | Creates a new branch based on your current branch |
| [`delete`](./branch-management/delete.md) | Deletes a branch while updating children stack relationships |
| [`rename`](./branch-management/rename.md) | Renames a branch while preserving its stack relationships |
| [`track`](./branch-management/track.md) | Adds an existing git branch to your stack |
| [`untrack`](./branch-management/untrack.md) | Removes a branch from the stack without deleting the Git branch |

### Update & Sync Commands

Used to update branches and propagate changes through your stack:

| Command | Description |
|---------|-------------|
| [`modify`](./update-sync/modify.md) | Interactively select files to stage and commit/amend |
| [`update`](./update-sync/update.md) | Rebases all child branches and updates their PRs |
| [`sync`](./update-sync/sync.md) | Fetches latest changes from the remote main branch and updates local branches |

### Pull Request Operations

Used to manage GitHub pull requests for your branches:

| Command | Description |
|---------|-------------|
| [`submit`](./pr-operations/submit.md) | Push changes to remote and optionally create/update PR with current branch changes |
| [`pr`](./pr-operations/pr.md) | Creates/updates pull requests for branches in the stack |
| [`merge`](./pr-operations/merge.md) | Merges PR and updates all dependent branches |

## Git Passthrough

Any unrecognized commands are transparently passed to vanilla Git, so you can also use standard Git commands within Panqake.

For example, `status` is not a valid `panqake` command, so it will be passed to Git:

```bash
# Running
pq status

# will pass it to git and run:
# git status
```
