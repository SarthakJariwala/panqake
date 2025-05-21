# `sync`

The `sync` command fetches the latest changes from your remote main branch, updates your local branch stack, and optionally cleans up merged branches. It keeps your branch stack up to date with remote changes in collaborative environments.

## Usage

```bash
pq sync [MAIN_BRANCH]
```

## Arguments

| Argument | Description |
|----------|-------------|
| `MAIN_BRANCH` | Base branch to sync with (default: main) |

## Examples

### Basic Sync Operation

```bash
pq sync
```

### Sync with a Different Base Branch

```bash
pq sync develop
```

::: tip
- Run `sync` regularly to keep your branch stack up to date with the remote main branch
- When working in a team, sync frequently to minimize potential merge conflicts
- The command uses git's `--autostash` option, so uncommitted changes will be automatically stashed and reapplied
:::
