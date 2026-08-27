# `modify`

The `modify` command helps you stage and commit changes to your current branch, with smart handling for new branches versus branches with existing commits. It streamlines the file staging and commit process.

## Usage

```bash
pq modify [OPTIONS]
```

## Options

| Option | Description |
|--------|-------------|
| `--commit, -c` | Create a new commit instead of amending |
| `--message, -m TEXT` | Commit message for the new or amended commit |
| `--no-amend` | Always create a new commit instead of amending |
| `--file PATH` | Stage an unstaged path; repeat for multiple paths |
| `--all` | Stage all unstaged files without prompting |
| `--staged-only` | Commit only already-staged changes without prompting |
| `--json` | Output machine-readable JSON and disable remaining prompts |

## Examples

### Interactive File Selection

```bash
pq modify
```

### Create a Commit with a Message

```bash
pq modify -m "Implement JWT authentication"
```

### Force Creating a New Commit

```bash
pq modify --no-amend -m "Add password reset functionality"
```

### Non-interactive File Selection

```bash
pq modify \
  --file src/auth.py \
  --file tests/test_auth.py \
  --message "Implement JWT authentication" \
  --json

# Or stage every unstaged file
pq modify --all --message "Implement JWT authentication" --json

# Or leave all unstaged files untouched
pq modify --staged-only --message "Commit staged changes" --json
```

::: tip
After using `modify` to commit changes, use `pq update` to propagate them to child branches.
:::
