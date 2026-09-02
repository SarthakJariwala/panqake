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

| Option | Description |
| ------ | ----------- |
| `--push / --no-push` | Push or skip unpushed branches without prompting |
| `--draft / --no-draft` | Create PRs as drafts or ready for review without prompting |
| `--title TEXT` | Set the target branch's PR title |
| `--body TEXT` | Set the target branch's PR body |
| `--body-file PATH` | Read the target PR body from a file; use `-` for stdin |
| `--reviewer USERNAME` | Add a reviewer; repeat for multiple reviewers |
| `--no-reviewers` | Create the target PR without reviewers or a reviewer prompt |
| `--attach PATH[#ALT]` | Attach an image or video to the target PR; repeat for multiple files |
| `--defaults` | Use generated titles, empty bodies, and no reviewers without metadata prompts |
| `--yes, -y` | Skip final creation confirmations |
| `--json` | Output machine-readable JSON and disable remaining prompts |

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

When running without `--draft` or `--no-draft`, you'll be prompted for each PR whether to create it as a draft:

```bash
pq pr
# You'll be asked: "Is this a draft PR? (y/N)"
```

### Fully Non-interactive Creation

```bash
pq pr feature-auth-ui \
  --push \
  --no-draft \
  --defaults \
  --yes \
  --json
```

`--defaults` also covers any ancestor PRs Panqake creates while walking the
stack. You can still use `--title`, `--body`/`--body-file`, `--reviewer`, and
`--attach` to override the generated metadata for the target branch.

Pipe a description through stdin with `--body-file -`:

```bash
printf 'Implements the authentication UI.\n' | \
  pq pr feature-auth-ui --body-file - --no-reviewers --yes --json
```

Attach screenshots the same way GitHub CLI does. Repeat `--attach` for more
than one file. Put alt text after `#`:

```bash
pq pr feature-auth-ui \
  --attach './login.png#The login error state' \
  --attach ./after.png \
  --push --defaults --yes --json
```

`--attach` applies only to a new PR for the target branch. Ancestor PRs in the
stack do not receive the files. GitHub CLI 2.99.0 or newer is required.

::: info
This command uses GitHub CLI (`gh`) under the hood, so you must have it installed and authenticated.
:::
