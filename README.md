# Panqake - Git Branch Stacking Utility

Panqake is a CLI implementing the git-stacking workflow. It helps manage stacked branches, making it easier to work with multiple dependent pull requests.

## Installation

1. ```bash
   uv tool install panqake
   ```

2. Dependencies:
   - gh: GitHub CLI (optional, only needed for PR creation)

## Usage

### Create a new branch in the stack

```bash
panqake new feature-login
```

This creates a new branch based on your current branch and tracks the relationship.

### View the branch stack

```bash
panqake list
```

Displays a tree view of your current branch stack.

### Update branches after changes

```bash
panqake update
```

After making changes to a branch, this command rebases all child branches to incorporate your changes.

### Delete a branch and relink the stack

```bash
panqake delete feature-old
```

Deletes a branch and relinks its children to its parent, maintaining the stack structure.

### Create PRs for the branch stack

```bash
panqake pr
```

Creates pull requests for each branch in the stack, starting from the bottom.

### Modify/amend commits

```bash
# Amend the current commit with changes
panqake modify

# Amend with a new commit message
panqake modify -m "New commit message"

# Create a new commit instead of amending
panqake modify --commit -m "New feature commit"
```

This command lets you modify your current commit by amending it or create a new commit.

### Update remote branch and PR

```bash
panqake update-pr
```

After modifying commits, this command updates the remote branch and any associated PR. It handles force pushing with safeguards when necessary.

## Workflow Example

1. Start a new feature stack from main:

   ```bash
   git checkout main
   panqake new feature-base
   ```

2. Make your initial changes and commit.

3. Create a dependent branch for additional work:

   ```bash
   panqake new feature-ui
   ```

4. Make changes and commit in the feature-ui branch.

5. If you need to update the feature-base branch:

   ```bash
   git checkout feature-base
   # Make changes and commit
   panqake update
   ```

6. If you need to modify a commit:

   ```bash
   # Make changes to files
   panqake modify -m "Updated implementation"
   panqake update-pr  # To update the remote branch and PR
   ```

7. Create PRs for your stack:
   ```bash
   panqake pr
   ```

## License

MIT

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## Changelog

### v0.1.1 (Unreleased)

- Added `modify` command for amending commits or creating new ones
- Added `update-pr` command for updating remote branches and PRs
- Improved force pushing with --force-with-lease for safety
- Switched CLI interface from prompt_toolkit to questionary for improved user experience
- Enhanced command-line prompts with better styling and autocomplete
- Fixed styling issues in branch listing display
- Improved output formatting for colored text
- Added custom color scheme that works well on both light and dark terminals
- Added documentation for the style system

### v0.1.0

- Initial release with core functionality
- Branch stacking management
- PR creation support
