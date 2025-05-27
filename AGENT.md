# Panqake Agent Guidelines

## Build/Test Commands

- Run project locally with changes: `uv run pq`
- Run all tests: `uv run pytest`
- Run a single test: `uv run pytest tests/panqake/test_main.py::test_main_execution`
- Run tests with verbosity: `uv run pytest -v`

## Code Style Guidelines

- Uses [Ruff](https://docs.astral.sh/ruff/) for both linting and formatting
- Run linter: `ruff check --fix`
- Run formatter: `ruff format`
- Python 3.12+ required
- Always use modern Python type hints for type safety. Check type errors using `uvx pyrefly check`
- Uses pre-commit hooks for code quality (trailing whitespace, line endings, YAML/TOML validation)

## Naming & Import Conventions

- Follow Python PEP 8 naming conventions
- Import order: standard library → external packages → project modules
- Group imports with blank lines between sections
- Use relative imports within modules

## Error Handling

- Handle Git errors with appropriate user feedback
- Use `run_git_command` utility for Git operations
- Print formatted error messages using rich
