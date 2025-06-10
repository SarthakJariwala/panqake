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

## Creating New PRs

When a branch doesn't have an existing PR, `submit` will prompt you to create one. During the PR creation process, you'll be asked whether to create it as a draft PR, giving you the option to share work-in-progress changes.

::: info
Use `submit` as your primary command for sharing changes for review.
:::

::: tip
After making revisions based on PR feedback, use `submit` again to update the PR.
:::
