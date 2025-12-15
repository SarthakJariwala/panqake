# Changelog

## [Unreleased]

## v0.23.1 - 2025-11-14

### Fixed

- Fixed branch tracking bug where branches created from subfolders weren't recognized when running `pq ls` from the top-level folder
  - `get_repo_id()` now normalizes git directory paths to absolute paths to ensure consistent repository identification across different working directories
  - Added automatic migration to recover branches previously stored under incorrect repo IDs (e.g., ".", "..", "../..")

## v0.23.0 - 2025-11-06

### Fixed

- Fixed `pq merge` to check PR actions status before updating child PR base references - prevents unnecessary updates when user decides not to proceed with merge

## v0.22.0 - 2025-09-22

### Added

- Added comprehensive git worktree support for all branch operations
  - `pq sync` now automatically handles branches managed by git worktrees
  - Branch operations (rebase, push, etc.) run in the appropriate working directory for both worktree and normal branches
  - Eliminates "already used by worktree" errors during sync operations
  - Seamless integration - no user intervention required for worktree branches

## v0.21.2 - 2025-09-08

### Fixed

- Fixed error when staging deleted files in `pq modify` command - now uses `git add -u` to stage tracked deletions reliably

## v0.21.1 - 2025-08-19

### Fixed

- Fixed error when staging deleted files in `pq modify` command - now uses `git rm --cached` for deleted files instead of `git add -A`

## v0.20.0 - 2025-07-02

### Changed

- Updated branch merge info display to show parent and child branches in a single line format (e.g., "Preparing to merge PR: main ← feature-branch")

## v0.19.3 - 2025-06-18

### Fixed

- Fixed error when staging deleted files in `pq modify` command - now uses `git add -A` to properly handle file deletions

## v0.19.2 - 2025-06-14

### Added

- Enhanced keyboard interrupt handling in all prompt functions with proper cleanup and exit

## v0.19.1 - 2025-06-10

### Fixed

- Fixed inconsistent conflict handling behavior between operations - merge command now aborts rebase on conflicts (same as sync and update) instead of leaving conflicts for manual resolution

## v0.19.0 - 2025-06-10

### Added

- Draft PR support for all PR creation commands

  - Added `--draft` flag to `pq pr` command to create all PRs as drafts
  - Interactive prompt for draft status when creating individual PRs
  - Support for draft PRs in both `pq pr` and `pq submit` workflows

- Improved type hints across the codebase

- Centralized selection utilities and refactored all commands to use new selection utilities

- Status feedback for all long-running operations
  - Real-time progress spinners for Git operations
  - Clear feedback during branch operations and GitHub API calls

### Changed

- Consolidated branch validation logic into single function

## v0.18.0 - 2025-05-29

### Changed

- Reduced terminal verbosity by replacing intermediate status messages with Rich Status spinners
  - Commands like `pq sync`, `pq update`, and `pq merge` now show clean progressive status updates
  - Only final status messages remain after command completion
  - Implemented nested status context handling to prevent spinner conflicts
  - Added status spinners to GitHub operations (PR creation, reviewer fetching, status checks, etc.)

## v0.17.0 - 2025-05-28

### Added

- Added search functionality to selection prompts for easier navigation through long lists. Users can type to filter options in real-time with clear "(type to search)" hints.
  - Reviewer selection
  - Branch selection
  - Branch tracking
  - File selection

### Changed

- Migrated CLI from Click to Typer
- Improved boolean flag naming for better clarity and consistency:
  - Changed `--no-push` to `--push/--no-push` (default: push) for update and sync commands
  - Changed `--no-delete-branch` to `--delete-branch/--no-delete-branch` (default: delete) for merge command
  - Changed `--no-update-children` to `--update-children/--no-update-children` (default: update) for merge command
  - Changed `--no-amend` to `--amend/--no-amend` (default: amend) for modify command

### Fixed

- Fixed type errors in utility functions for better type safety
- Enhanced type hints across utils module with semantic type aliases for improved type safety and code readability.

## v0.16.0 - 2025-05-23

### Added

- Enhanced `pq merge` command to show specific failed check names and status instead of generic warning
  - Now displays which checks failed (e.g., "Tests (FAILURE)", "CI (PENDING)")
  - Users no longer need to check GitHub to see which checks haven't passed

## v0.15.0 - 2025-05-23

### Added

- Added reviewer selection functionality for PR creation in `pq submit` and `pq pr` commands
  - Automatically fetch repository collaborators and owner as potential reviewers
  - Interactive checkbox interface for selecting multiple reviewers
  - Option to skip reviewer selection entirely
  - Selected reviewers are automatically assigned when creating PRs

## v0.14.0 - 2025-05-22

### Added

- Added multiline support for PR descriptions

### Fixed

- Fixed `update_branches_with_conflict_handling` to properly handle cases when no child branches exist

## v0.13.1 - 2025-05-21

### Fixed

- Fixed checking PR checks status by using `conclusion` field instead of `state` field

## v0.13.0 - 2025-05-21

### Added

- Display clickable PR URLs after creating or updating pull requests in `pq submit` and `pq pr` commands
- Check if PR required status checks have passed before merging, with option to proceed anyway
- Automatically detect when force-push is needed:
  - Detect amended commits for automatic force-push with lease during `pq submit`
  - Detect non-fast-forward updates that would otherwise fail during `pq submit`
  - Eliminate need for user confirmation, making it safer and more convenient
- Improved push behavior in `update` and `sync` commands:
  - Automatically push successfully updated branches to remote by default
  - Added `--no-push` option to skip pushing to remote
  - Skip pushing branches that don't exist on remote yet
  - Only push branches that were successfully updated
  - Skip pushing branches that are already in sync with remote

### Changed

- Refactored `update` and `sync` commands to leverage the `Stacks` class and utilities:
  - Replaced recursive implementation with a non-recursive approach
  - Added consistent error handling with (success, error_message) return pattern
  - Leveraged existing branch utilities to reduce code duplication
- Enhanced conflict handling in `update` and `sync` commands:
  - Continue updating other branches when one branch has conflicts
  - Skip branches whose parents had conflicts
  - Provide a report of branches with conflicts at the end
  - Return specific error messages for conflicted branches
- Improved Git error handling with explicit parameter to control stderr return behavior

### Fixed

- Fixed force-push detection to properly capture Git error messages

## v0.12.0 - 2025-05-13

### Added

- Added `up` command to navigate to parent branch in the stack
- Added `down` command to navigate to child branches with smart selection for multiple children
- Added `pre-commit` integration for automatic code formatting and linting
- Added `tests.yml` workflow integration for automated testing

### Changed

- Improved CLI interface with logical command grouping:
  - Navigation Commands (up, down, switch, list, etc.)
  - Branch Management (new, delete, rename, etc.)
  - Update & Sync (update, modify, sync)
  - Pull Request Operations (pr, submit, merge)
- Enhanced help menu formatting and readability with rich-click styling

## v0.11.0 - 2025-05-13

### Added

- Added `untrack` command to remove branches from the panqake stack without deleting the git branch
- Added `rename` command to rename branches while preserving their stack relationships
- Added a new `Stacks` data structure class for more robust branch relationship management
- Added new branch relationship utilities:
  - Branch lineage tracking (all ancestors of a branch)
  - Descendant tracking (all children, grandchildren, etc.)
  - Common ancestor finding between branches
  - Branch tree visualization
  - Branch parent changing with circular reference protection

### Changed

- Improved `remove_from_stack` utility function to return status and properly handle child branches
- Enhanced stack metadata handling when branches are removed, preserving branch hierarchy
- Improved error reporting when branches cannot be found in stack metadata
- Refactored config.py to extract common file operations into helper functions
- Reduced code duplication and improved error handling consistency in configuration utilities
- Unified branch tree visualization in a single implementation in the `Stacks` class
- Enhanced tree visualization with proper tree connectors (└──, ├──, │) and current branch indicator

### Fixed

- Fixed `delete` command to prompt for branch name when none is provided
- Added protection to prevent deletion of main and master branches

## v0.10.0 - 2025-05-05

### Changed

- Run rebase using `--autostash` option to allow running on dirty worktree.

## v0.9.1 - 2025-05-02

### Changed

- Minor formatting changes to outputs of certain commands

## v0.9.0 - 2025-04-30

### Added

- `pq submit` will now prompt the user if they also want to create a PR. This simplifies the workflow by not requiring the user to explicitly call `pq pr` after submitting changes.

### Removed

- Removed old prompt utils that were no longer being used

## v0.8.0 - 2025-04-29

### Added

- Added create_branch utility function
- Added branch hierarchy visualization for checkout command

### Changed

- Refactored code to use the common checkout_branch utility
- Enhanced branch hierarchy display before showing switching options in switch command
- Improved update command to continue instead of aborting on conflicts

## v0.7.0 - 2025-04-28

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

## v0.6.0 - 2025-04-28

### Added

- Added a new `sync` command to fetch latest changes from the remote main branch, update local child branches, and optionally delete merged branches.
- Added utilities for common branch related git operations

### Changed

- Refactored `merge` and `update` to use common extracted branch utility functions

## v0.5.0 - 2025-04-24

### Added

- Added Git command pass-through functionality - any unrecognized commands are passed to vanilla Git
- Improved CLI experience by allowing standard Git commands to work seamlessly within Panqake

## v0.4.0 - 2025-04-23

### Added

- Added file selection UI for staging files in the modify command
- Added `--no-amend` flag to force creating new commits instead of amending
- Added smart handling for new branches vs. branches with commits in modify command
- Added improved rename/copy file handling during staging

### Changed

- Enhanced modify command to show unstaged changes and prompt for selection
- Modified branch detection to better handle parent branch identification
- Improved user experience with clear feedback during file staging

## v0.3.1 - 2025-04-23

### Fixed

- Fixed error messages appearing when checking if a branch exists during branch creation

## v0.3.0 - 2025-04-23

### Added

- Added track command to add existing Git branches to the stack

## v0.2.0 - 2025-04-22

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

## v0.1.0 - Initial Release

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
