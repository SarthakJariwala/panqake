# Changelog

## [v0.10.0] - 2025-05-05

### Changed

- Run rebase using `--autostash` option to allow running on dirty worktree.

## [v0.9.1] - 2025-05-02

### Changed

- Minor formatting changes to outputs of certain commands

## [v0.9.0] - 2025-04-30

### Added

- `pq submit` will now prompt the user if they also want to create a PR. This simplifies the workflow by not requiring the user to explicitly call `pq pr` after submitting changes.

### Removed

- Removed old prompt utils that were no longer being used

## [v0.8.0] - 2025-04-29

### Added

- Added create_branch utility function
- Added branch hierarchy visualization for checkout command

### Changed

- Refactored code to use the common checkout_branch utility
- Enhanced branch hierarchy display before showing switching options in switch command
- Improved update command to continue instead of aborting on conflicts

## [v0.7.0] - 2025-04-28

### Added

- Added a new `submit` command to replace the `update-pr` command
- Added documentation for arguments in commands
- Added aliases for list (`ls`) and switch (`co`) commands
- Added `rich` library for improved terminal output and formatting

### Changed

- Changed from argparse to `click` for CLI parsing
- Improved UI for showing PR information using `rich` Panel
- Enhanced console output using `rich` library

### Fixed

- Fixed formatting issues for printing information
- Fixed `delete` command to work without confirmation when upstream branch is deleted and confirmed by user

## [v0.6.0] - 2025-04-28

### Added

- Added a new `sync` command to fetch latest changes from the remote main branch, update local child branches, and optionally delete merged branches.
- Added utilities for common branch related git operations

### Changed

- Refactored `merge` and `update` to use common extracted branch utility functions

## [v0.5.0] - 2025-04-24

### Added

- Added Git command pass-through functionality - any unrecognized commands are passed to vanilla Git
- Improved CLI experience by allowing standard Git commands to work seamlessly within Panqake

## [v0.4.0] - 2025-04-23

### Added

- Added file selection UI for staging files in the modify command
- Added `--no-amend` flag to force creating new commits instead of amending
- Added smart handling for new branches vs. branches with commits in modify command
- Added improved rename/copy file handling during staging

### Changed

- Enhanced modify command to show unstaged changes and prompt for selection
- Modified branch detection to better handle parent branch identification
- Improved user experience with clear feedback during file staging

## [v0.3.1] - 2025-04-23

### Fixed

- Fixed error messages appearing when checking if a branch exists during branch creation

## [v0.3.0] - 2025-04-23

### Added

- Added track command to add existing Git branches to the stack

## [v0.2.0] - 2025-04-22

### Added

- Added merge command to streamline merging branches
- Added modify and update-pr commands
- Added select prompt functionality
- Improved branch selection workflows

### Changed

- Consolidated common code into git and github utilities
- Now using a common run_gh_command utility
- Update command now pushes to remote branches, automatically updating associated PRs
- Better formatting while printing information
- Updated README with more complete information

### Fixed

- Fixed import issue in git.py
- Fixed publishing workflow
- Ensured stacks.json accuracy after merge and branch deletion
- Verify branch is pushed to remote before creating PR

### Removed

- Removed shell scripts in favor of Python implementations
- Removed test_pr
- Removed claude.md

## [v0.1.0] - Initial Release

### Added

- Initial project structure and core functionality
- Implementation of basic commands (new, list, delete, update)
- Added switch command to move between branches
- Added PR creation capability
- Integration with GitHub CLI
- Integrated prompt_toolkit for interactive prompts
- Added pytest configuration and initial tests
- Added "pq" as an alias for "panqake"

### Changed

- Moved from using prompt_toolkit directly to questionary for improved prompts
- Simplified PR module structure
- Simplified delete module

### Fixed

- Fixed nested branch display
- Improved color styling for better readability
- Added type hints and related fixes
- Fixed prompt_confirm function
