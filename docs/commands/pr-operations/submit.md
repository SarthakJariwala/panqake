# `submit`

The `submit` command updates your pull request with the latest changes from your branch and optionally creates a new PR if one doesn't exist. It streamlines the process of sharing your changes with your team for review.

## Usage

```bash
pq submit [BRANCH_NAME]
```

## Arguments

| Argument | Description |
|----------|-------------|
| `BRANCH_NAME` | Optional branch to update PR for |

## Examples

### Basic Usage

```bash
pq submit
```

### For a Specific Branch

```bash
pq submit feature-auth
```

::: info
Use `submit` as your primary command for sharing changes for review.
:::

::: tip
After making revisions based on PR feedback, use `submit` again to update the PR.
:::
