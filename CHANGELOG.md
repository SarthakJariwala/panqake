# Changelog

All notable changes to the Panqake project will be documented in this file.

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
