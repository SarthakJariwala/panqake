"""Clean exit utilities for panqake."""

import sys


def clean_exit(code: int = 130) -> None:
    """Clean exit with optional message.

    Args:
        code: Exit code (default 130 for SIGINT/Ctrl+C)
    """
    # Import here to avoid circular import with questionary_prompt
    from panqake.utils.questionary_prompt import console

    console.print("\n[muted]Interrupted by user[/muted]")
    sys.exit(code)
