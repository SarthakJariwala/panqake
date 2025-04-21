# Bash commands

- ruff check --fix --select I: lint python code
- ruff format: format python code
- uv add <package_name>: install a new python package
- uv run pytest: run pytest tests

# Workflow

- Write tests first, verify that they fail, implement code, and verify that they pass
- Don't use mocks unless necessary - justify why you need them
- Don't repeat yourself (DRY)
- Use python type hints to improve code readability and maintainability
- When in doubt, ask for help/confirmation
