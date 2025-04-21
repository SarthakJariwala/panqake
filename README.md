# Panqake - Git Branch Stacking Utility

Panqake is a set of shell utilities for implementing the git-stacking workflow. It helps manage stacked branches, making it easier to work with multiple dependent pull requests.

## Installation

1. Clone this repository:

   ```bash
   git clone https://github.com/yourusername/panqake.git
   ```

2. Add the panqake directory to your PATH or create symlinks to the panqake script in a directory that's already in your PATH.

3. Dependencies:
   - jq: For JSON processing
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

6. Create PRs for your stack:
   ```bash
   panqake pr
   ```

## License

MIT

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## Changelog

### v0.1.1 (Unreleased)

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
