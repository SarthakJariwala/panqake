# `pr`

The `pr` command creates or updates pull requests for branches in your stack. It automatically sets the correct base branch and generates appropriate PR titles and descriptions.

## Usage

```bash
pq pr [BRANCH_NAME]
```

## Arguments

| Argument | Description |
|----------|-------------|
| `BRANCH_NAME` | Optional branch to start from |

## Examples

### Creating a PR for the Current Branch

```bash
pq pr
```

### Creating a PR for a Specific Branch

```bash
pq pr feature-auth-ui
```

::: info
This command uses GitHub CLI (`gh`) under the hood, so you must have it installed and authenticated.
:::
