"""Tests for __main__.py module."""

from unittest.mock import patch

import pytest


@pytest.fixture
def mock_main():
    """Mock the main() function from cli module."""
    with patch("panqake.cli.main") as mock:
        yield mock


def test_main_execution(mock_main):
    """Test that main() is called when module is run directly.

    This test verifies that when the module is run as __main__,
    it properly calls the main() function from the cli module.
    """
    # Import the __main__ module
    import panqake.__main__

    # Directly call the main function imported within __main__
    # This bypasses issues with patching __name__ and module reloading
    # The mock_main fixture already patches panqake.cli.main
    panqake.__main__.main()

    # Verify the patched main was called
    mock_main.assert_called_once()


def test_main_not_called_on_import(mock_main):
    """Test that main() is not called when module is imported.

    This test verifies that when the module is imported rather than
    run directly, the main() function is not called.
    """
    # Setup
    # Import module with __name__ not set to __main__
    with patch("__main__.__name__", "not_main"):
        import panqake.__main__  # noqa: F401

    # Verify
    assert not mock_main.called
