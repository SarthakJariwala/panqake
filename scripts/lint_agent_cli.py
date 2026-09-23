"""Lint interactive prompts against their non-interactive CLI contracts."""

from __future__ import annotations

import ast
import sys
from collections import Counter
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path

from typer.main import get_command

from panqake.cli import app


ROOT = Path(__file__).resolve().parents[1]
CLI_PATH = ROOT / "src" / "panqake" / "cli.py"
COMMANDS_DIR = ROOT / "src" / "panqake" / "commands"


@dataclass(frozen=True, order=True)
class PromptSite:
    """Stable identity for one prompt call within a command function."""

    path: str
    function: str
    method: str
    occurrence: int


@dataclass(frozen=True)
class CliContract:
    """CLI inputs that replace a prompt for one or more commands."""

    commands: tuple[str, ...]
    inputs: tuple[str, ...]


CONTRACTS: dict[PromptSite, CliContract] = {
    PromptSite("delete.py", "delete_branch_core", "prompt_select_branch", 1): (
        CliContract(("delete",), ("BRANCH_NAME",))
    ),
    PromptSite("delete.py", "delete_branch_core", "prompt_confirm", 1): (
        CliContract(("delete",), ("--yes",))
    ),
    PromptSite("down.py", "down_core", "prompt_select_branch", 1): CliContract(
        ("down",), ("CHILD",)
    ),
    PromptSite("merge.py", "merge_branch_core", "prompt_confirm", 1): CliContract(
        ("merge",), ("--allow-failed-checks",)
    ),
    PromptSite("merge.py", "merge_branch.core", "prompt_confirm", 1): CliContract(
        ("merge",), ("--yes",)
    ),
    PromptSite("merge.py", "get_merge_method", "select_from_options", 1): (
        CliContract(("merge",), ("--method",))
    ),
    PromptSite("modify.py", "modify_commit_core", "prompt_select_files", 1): (
        CliContract(("modify",), ("--file", "--all", "--staged-only"))
    ),
    PromptSite("modify.py", "modify_commit_core", "prompt_input", 1): CliContract(
        ("modify",), ("--message",)
    ),
    PromptSite("move.py", "move_branch_core", "prompt_select_branch", 1): (
        CliContract(("move", "reparent"), ("--to",))
    ),
    PromptSite("new.py", "create_new_branch_core", "prompt_input", 1): (
        CliContract(("new",), ("BRANCH_NAME",))
    ),
    PromptSite("new.py", "create_new_branch_core", "prompt_input", 2): (
        CliContract(("new",), ("BASE_BRANCH",))
    ),
    PromptSite("new.py", "create_new_branch_core", "prompt_path", 1): CliContract(
        ("new",), ("--path",)
    ),
    PromptSite("pr.py", "create_pr_for_branch_core", "prompt_confirm", 1): (
        CliContract(("pr", "submit"), ("--push", "--no-push"))
    ),
    PromptSite("pr.py", "create_pr_for_branch_core", "prompt_confirm", 2): (
        CliContract(("pr", "submit"), ("--push", "--no-push"))
    ),
    PromptSite("pr.py", "create_pr_for_branch_core", "prompt_input", 1): (
        CliContract(("pr", "submit"), ("--title", "--defaults"))
    ),
    PromptSite(
        "pr.py", "create_pr_for_branch_core", "prompt_input_multiline", 1
    ): CliContract(("pr", "submit"), ("--body", "--body-file", "--defaults")),
    PromptSite(
        "pr.py", "create_pr_for_branch_core", "prompt_pr_attachments", 1
    ): CliContract(("pr", "submit"), ("--attach", "--defaults")),
    PromptSite("pr.py", "create_pr_for_branch_core", "prompt_confirm", 3): (
        CliContract(("pr", "submit"), ("--draft", "--no-draft"))
    ),
    PromptSite(
        "pr.py", "create_pr_for_branch_core", "prompt_select_reviewers", 1
    ): CliContract(
        ("pr", "submit"),
        ("--reviewer", "--no-reviewers", "--defaults"),
    ),
    PromptSite("pr.py", "create_pr_for_branch_core", "prompt_confirm", 4): (
        CliContract(("pr", "submit"), ("--yes",))
    ),
    PromptSite("rename.py", "rename_core", "prompt_input", 1): CliContract(
        ("rename",), ("NEW_NAME",)
    ),
    PromptSite("submit.py", "submit_branch_core", "prompt_confirm", 1): (
        CliContract(("submit",), ("--create-pr", "--no-create-pr"))
    ),
    PromptSite("switch.py", "switch_branch_core", "prompt_select_branch", 1): (
        CliContract(("switch", "co"), ("BRANCH_NAME",))
    ),
    PromptSite("sync.py", "handle_merged_branches_core", "prompt_confirm", 1): (
        CliContract(("sync",), ("--delete-merged", "--keep-merged"))
    ),
    PromptSite("track.py", "track_branch_core", "prompt_select_branch", 1): (
        CliContract(("track",), ("--parent",))
    ),
    PromptSite("update.py", "update_core", "prompt_confirm", 1): (
        CliContract(("update",), ("--yes",))
    ),
}


class PromptVisitor(ast.NodeVisitor):
    """Collect UI-port, helper, and direct interactive calls."""

    def __init__(self, path: str) -> None:
        self.path = path
        self.functions: list[str] = []
        self.interactive_helpers: set[str] = set()
        self.occurrences: Counter[tuple[str, str]] = Counter()
        self.sites: list[PromptSite] = []

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        module = node.module or ""
        if module.endswith("utils.selection"):
            prefix = "select_"
        elif module.endswith("utils.questionary_prompt"):
            prefix = "prompt_"
        else:
            self.generic_visit(node)
            return

        for name in node.names:
            if name.name.startswith(prefix):
                self.interactive_helpers.add(name.asname or name.name)
        self.generic_visit(node)

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        self.functions.append(node.name)
        self.generic_visit(node)
        self.functions.pop()

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        self.functions.append(node.name)
        self.generic_visit(node)
        self.functions.pop()

    def visit_Call(self, node: ast.Call) -> None:
        function = node.func
        method: str | None = None
        if isinstance(function, ast.Attribute) and function.attr.startswith("prompt_"):
            method = function.attr
        elif isinstance(function, ast.Name) and (
            function.id in self.interactive_helpers or function.id == "input"
        ):
            method = function.id
        elif (
            isinstance(function, ast.Attribute)
            and function.attr in {"confirm", "prompt"}
            and isinstance(function.value, ast.Name)
            and function.value.id in {"click", "typer"}
        ):
            method = f"{function.value.id}.{function.attr}"
        elif isinstance(function, ast.Attribute) and function.attr == "ask":
            method = "ask"

        if method is not None:
            enclosing_function = ".".join(self.functions) or "<module>"
            key = (enclosing_function, method)
            self.occurrences[key] += 1
            self.sites.append(
                PromptSite(
                    self.path,
                    enclosing_function,
                    method,
                    self.occurrences[key],
                )
            )
        self.generic_visit(node)


def prompt_source_paths() -> list[Path]:
    """Return every first-party source that may define CLI interaction."""
    return [CLI_PATH, *sorted(COMMANDS_DIR.glob("*.py"))]


def find_prompt_sites(paths: Iterable[Path] | None = None) -> set[PromptSite]:
    """Return every interactive prompt in CLI and command modules."""
    sites: set[PromptSite] = set()
    for path in paths if paths is not None else prompt_source_paths():
        tree = ast.parse(path.read_text(), filename=str(path))
        visitor = PromptVisitor(path.name)
        visitor.visit(tree)
        sites.update(visitor.sites)
    return sites


def command_inputs(command: str) -> set[str]:
    """Return the arguments and options exposed by a Typer command."""
    root_command = get_command(app)
    click_command = root_command.commands[command]
    inputs: set[str] = set()
    for parameter in click_command.params:
        inputs.update(parameter.opts)
        inputs.update(parameter.secondary_opts)
        if not parameter.name.startswith("-"):
            inputs.add(parameter.human_readable_name)
    return inputs


def main() -> int:
    """Check prompt inventory and actual Typer input contracts."""
    failures: list[str] = []
    actual_sites = find_prompt_sites()
    contracted_sites = set(CONTRACTS)

    for site in sorted(actual_sites - contracted_sites):
        failures.append(
            "unregistered interactive prompt: "
            f"{site.path}:{site.function} {site.method} #{site.occurrence}"
        )

    for site in sorted(contracted_sites - actual_sites):
        failures.append(
            "stale interactive prompt contract: "
            f"{site.path}:{site.function} {site.method} #{site.occurrence}"
        )

    inputs_by_command: dict[str, set[str]] = {}
    for site in sorted(actual_sites & contracted_sites):
        contract = CONTRACTS[site]
        for command in contract.commands:
            cli_inputs = inputs_by_command.setdefault(command, command_inputs(command))
            for cli_input in contract.inputs:
                if cli_input not in cli_inputs:
                    failures.append(
                        f"pq {command}: {site.method} in "
                        f"{site.path}:{site.function} has no {cli_input} input"
                    )

    if failures:
        print("Agent CLI contract lint failed:", file=sys.stderr)
        for failure in failures:
            print(f"- {failure}", file=sys.stderr)
        return 1

    print(f"Agent CLI contract lint passed ({len(actual_sites)} prompts checked)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
