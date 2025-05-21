# `update`

The `update` command rebases all child branches in your stack with changes from their parent branches, ensuring your entire stack stays in sync. It's crucial when changes are made to parent branches that need to propagate down the stack.

## Usage

```bash
pq update [BRANCH_NAME]
```

## Arguments

| Argument | Description |
|----------|-------------|
| `BRANCH_NAME` | Optional branch to start updating from |

## Options

| Option | Description |
|--------|-------------|
| `--no-push` | Don't push changes to remote after updating branches |

## Examples

### Updating from Current Branch

```bash
pq update
```

### Updating from a Specific Branch

```bash
pq update feature-auth
```

::: tip
- Run `update` whenever you make changes to a parent branch that should propagate to its children
- Remote branches and PRs are automatically updated, keeping your GitHub workflow in sync
:::
