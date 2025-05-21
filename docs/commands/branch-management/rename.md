# `rename`

The `rename` command allows you to rename a branch while preserving its stack relationships. It ensures that parent-child relationships are maintained when renaming branches.

## Usage

```bash
pq rename [OLD_NAME] [NEW_NAME]
```

## Arguments

| Argument | Description |
|----------|-------------|
| `OLD_NAME` | Current name of the branch to rename (default: current branch) |
| `NEW_NAME` | New name for the branch (if not provided, will prompt) |

## Examples

### Renaming the Current Branch

```bash
pq rename auth-feature
```

### Renaming a Specific Branch

```bash
pq rename feature-backend backend-feature
```

::: info
If the branch has an open PR, you may need to recreate it with `pq pr` after renaming
:::
