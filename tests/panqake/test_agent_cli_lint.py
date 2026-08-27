"""Regression tests for the agent CLI prompt-contract lint."""

import runpy
from pathlib import Path


LINT_SCRIPT = Path(__file__).parents[2] / "scripts" / "lint_agent_cli.py"


def _load_lint():
    return runpy.run_path(str(LINT_SCRIPT))


def test_prompt_inventory_detects_ui_receiver_with_any_name(tmp_path):
    source = tmp_path / "command.py"
    source.write_text(
        "def run(interaction):\n    return interaction.prompt_confirm('Continue?')\n",
        encoding="utf-8",
    )
    lint = _load_lint()

    sites = lint["find_prompt_sites"]([source])

    assert [(site.path, site.function, site.method) for site in sites] == [
        ("command.py", "run", "prompt_confirm")
    ]


def test_prompt_inventory_scans_cli_and_detects_direct_typer_prompt(tmp_path):
    source = tmp_path / "cli.py"
    source.write_text(
        "import typer\n\ndef command():\n    return typer.confirm('Continue?')\n",
        encoding="utf-8",
    )
    lint = _load_lint()

    sites = lint["find_prompt_sites"]([source])
    default_sources = lint["prompt_source_paths"]()

    assert [(site.path, site.function, site.method) for site in sites] == [
        ("cli.py", "command", "typer.confirm")
    ]
    assert lint["CLI_PATH"] in default_sources
