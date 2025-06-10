# `pr`

The `pr` command creates or updates pull requests for branches in your stack. It automatically sets the correct base branch and generates appropriate PR titles and descriptions.

## Usage

```bash
pq pr [BRANCH_NAME] [OPTIONS]
```

## Arguments

| Argument      | Description                   |
| ------------- | ----------------------------- |
| `BRANCH_NAME` | Optional branch to start from |

## Options

| Option    | Description          |
| --------- | -------------------- |
| `--draft` | Create PRs as drafts |

## Examples

### Creating a PR for the Current Branch

```bash
pq pr
```

### Creating a PR for a Specific Branch

```bash
pq pr feature-auth-ui
```

### Creating Draft PRs

When you want to create PRs as drafts (useful for work-in-progress):

```bash
# Create all PRs in the stack as drafts
pq pr --draft

# Create drafts for a specific branch and its dependencies
pq pr feature-auth-ui --draft
```

### Interactive Draft Selection

When running without the `--draft` flag, you'll be prompted for each PR whether to create it as a draft:

```bash
pq pr
# You'll be asked: "Is this a draft PR? (y/N)"
```

::: info
This command uses GitHub CLI (`gh`) under the hood, so you must have it installed and authenticated.
:::
