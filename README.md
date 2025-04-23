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

**Dependencies:**
- gh: GitHub CLI (only needed for PR creation)

## Core Commands

| Command | What it Does |
|---------|-------------|
| `panqake new feature-name` | Create a new branch in your stack |
| `panqake update` | Update all child branches after parent changes |
| `panqake pr` | Create PRs for your entire branch stack |
| `panqake merge` | Merge a PR and update all dependents automatically |

## Real-World Workflow Example

Here's how to build a stack of dependent features:

```bash
# Start from main
git checkout main

# Create your base feature branch
pq new auth-backend
# Make changes, commit them
git add .
git commit -m "Implement authentication backend"

# Create a dependent branch for frontend work
pq new auth-frontend
# Make changes, commit them
git add .
git commit -m "Add login form UI"

# Need to fix something in the backend?
git checkout auth-backend
# Make your changes, commit them
git add .
git commit -m "Fix auth token validation"

# Update your entire stack with one command
pq update

# Create PRs for your entire stack
pq pr

# After approval, merge with a single command
pq merge
```

## Advanced Features

### Track Existing Git Branches

Add branches created outside panqake to your stack:

```bash
pq track feature-branch
```

### Modify/Amend Commits

Update your current branch's commit and propagate changes:

```bash
# Make file changes
pq modify -m "Better implementation"
```

### Delete a Branch While Maintaining Stack

```bash
pq delete feature-old
```

## Why Choose Panqake

- **Designed for real workflows**: Stack PRs without effort
- **Single command operations**: Complex git operations condensed to simple commands
- **GitHub integration**: Seamlessly works with GitHub PRs

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

MIT
