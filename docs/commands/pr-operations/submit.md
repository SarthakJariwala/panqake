# `submit`

The `submit` command updates your pull request with the latest changes from your branch and optionally creates a new PR if one doesn't exist. It streamlines the process of sharing your changes with your team for review.

## Usage

```bash
pq submit [BRANCH_NAME] [OPTIONS]
```

## Arguments

| Argument | Description |
|----------|-------------|
| `BRANCH_NAME` | Optional branch to update PR for |

## Options

| Option | Description |
|--------|-------------|
| `--create-pr / --no-create-pr` | Create or skip a missing PR without prompting |
| `--push / --no-push` | Push or skip an unpushed PR base branch without prompting |
| `--draft / --no-draft` | Create a missing PR as draft or ready for review |
| `--title TEXT` | Set the title of a missing PR |
| `--body TEXT` | Set the body of a missing PR |
| `--body-file PATH` | Read the body from a file; use `-` for stdin |
| `--reviewer USERNAME` | Add a reviewer; repeat for multiple reviewers |
| `--no-reviewers` | Create without reviewers or a reviewer prompt |
| `--attach PATH[#ALT]` | Attach an image or video when creating a missing PR; repeat for multiple files |
| `--defaults` | Use a generated title and no reviewers without metadata prompts. An empty body is filled with attachment markdown when `--attach` is given |
| `--yes, -y` | Skip the final PR creation confirmation |
| `--json` | Output machine-readable JSON and disable remaining prompts |

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

For a fully non-interactive submission that creates a missing PR:

```bash
pq submit feature-auth \
  --create-pr \
  --push \
  --no-draft \
  --defaults \
  --yes \
  --json
```

To attach a screenshot when that missing PR is created:

```bash
pq submit feature-auth \
  --create-pr \
  --attach './login.png#The login error state' \
  --push \
  --defaults \
  --yes \
  --json
```

`--defaults` would otherwise send an empty description. With `--attach`,
Panqake writes `![alt](path)` for each file so GitHub CLI can rewrite those
references to upload URLs. An explicit `--body` is left unchanged.

`--attach` is ignored when the branch already has an open PR, the same as
`--title` and `--body`. GitHub CLI 2.99.0 or newer is required.

::: info
Use `submit` as your primary command for sharing changes for review.
:::

::: tip
After making revisions based on PR feedback, use `submit` again to update the PR.
:::
