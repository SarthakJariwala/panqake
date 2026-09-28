# `sync`

The `sync` command fetches the latest changes from your remote main branch, updates your local branch stack, and optionally cleans up merged branches. It keeps your branch stack up to date with remote changes in collaborative environments.

## Usage

```bash
pq sync [MAIN_BRANCH]
```

## Arguments

| Argument | Description |
|----------|-------------|
| `MAIN_BRANCH` | Base branch to sync with (default: local `main`, then `master`) |

When no branch is specified, `sync` uses `main` if it exists locally, otherwise
`master`. If both exist, `main` takes precedence. If neither exists, specify the
base branch explicitly, for example `pq sync develop`. An explicit branch always
overrides automatic selection, so `pq sync master` works even when `main` exists.

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
