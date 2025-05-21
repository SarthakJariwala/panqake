# `untrack`

The `untrack` command removes a branch from your Panqake stack without deleting the Git branch itself. It's useful when you want to stop tracking a branch but keep it in your Git repository.

## Usage

```bash
pq untrack [BRANCH_NAME]
```

## Arguments

| Argument | Description |
|----------|-------------|
| `BRANCH_NAME` | Optional name of branch to untrack |

## Examples

### Untracking a Specified Branch

```bash
pq untrack feature-auth
```

### Interactive Branch Selection

```bash
pq untrack
```



::: info
The branch remains in your Git repository and can be tracked again later if needed. If you want to completely remove a branch, use `pq delete` instead.
:::
