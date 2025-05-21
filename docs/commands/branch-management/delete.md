# `delete`

The `delete` command removes a branch from your Git repository while maintaining stack relationships by reconnecting any child branches to the parent branch. It helps you clean up your stack while preserving dependencies.

::: tip
If you simply want to remove a branch from tracking without deleting it, use `pq untrack` instead
:::


## Usage

```bash
pq delete BRANCH_NAME
```

## Arguments

| Argument | Description |
|----------|-------------|
| `BRANCH_NAME` | Name of the branch to delete (required) |

## Examples

### Deleting a Specified Branch

```bash
pq delete feature-auth
```

::: warning
Panqake includes safeguards to prevent deletion of `main` and `master` branches.
:::
