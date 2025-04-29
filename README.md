# Panqake: Stack Git Branches Without the Headache

Panqake is a CLI tool that makes managing dependent pull requests significantly easier by automating the entire git-stacking workflow. Stop dealing with painful rebases and focus on your code instead.

## What Problems Panqake Solves

- **Reviews no longer block progress** on dependent work
- **Simplify complex workflows** with a single command for common operations
- **Eliminate manual rebasing** when working with dependent branches
- **Automate PR management** for each branch in your stack

## Quick Installation

```bash
uv tool install panqake
```

**Optional dependency:**
- gh: GitHub CLI (needed only for PR creation/management)

## Most-Used Commands

| Command | Purpose | What It Does |
|---------|---------|-------------|
| `pq new feature-name` | Create branches | Creates a new branch based on your current branch |
| `pq modify` | Commit changes | Interactively select files to stage and commit/amend |
| `pq update` | Propagate changes | Rebases all child branches and updates their PRs |
| `pq submit` | Submit changes | Updates the PR with current branch changes |
| `pq sync` | Sync branches | Fetches latest changes from the remote main branch, updates local child branches, and optionally deletes merged branches |
| `pq merge` | Complete workflow | Merges PR and updates all dependent branches |
| `pq list` or `pq ls` | View branch structure | Lists all branches in the stack with their relationships |
| `pq switch` or `pq co` | Navigate branches | Switches to another branch in the stack |

## Real-World Workflow Example

Here's how to build a stack of dependent features:

```bash
# Start from main
git checkout main

# Create your base feature branch
pq new auth-backend
# Make changes, commit them
pq modify -m "Implement JWT authentication"

# Create a dependent branch for frontend work
pq new auth-frontend
# Make changes, commit them
git add .
pq modify -m "Add login form UI"

# Oops! Need to fix something in the backend branch
pq switch auth-backend
# Make your backend fixes

# Commit the fixes and automatically update child branches
pq modify -m "Fix token validation"

# Sync with remote main and update stack
pq sync

# Update any remaining child branches if needed
pq update

# Create PRs for your entire stack with a single command
pq pr

# When the first PR is approved, merge it and update the stack
pq merge auth-backend
```

## Advanced Features

### Sync with Remote Main Branch

Keep your branch stack up to date with remote changes:

```bash
# Sync with remote main and update stack
pq sync
```

### Track Existing Git Branches

Add branches created outside panqake to your stack:

```bash
pq track feature-branch

# You can use the list alias to see your branch structure
pq ls

# Use the switch alias to move between branches
pq co auth-frontend
```

### Flexible Commit Creation

```bash
# Amend existing Commit
pq modify

# Force creating a new commit instead of amending
pq modify --no-amend

# Or explicitly
pq modify --commit -m "New feature implementation"
```

### Delete a Branch While Preserving the Stack

```bash
pq delete feature-old
```

## Why Choose Panqake

- **Designed for real workflows**: Stack PRs without effort
- **Reduces context switching** by making branch navigation seamless
- **Single command operations**: Complex git operations condensed to simple commands
- **GitHub integration**: Seamlessly works with GitHub PRs

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

MIT
