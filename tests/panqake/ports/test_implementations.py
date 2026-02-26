"""Tests for concrete port implementations."""

import pytest

from panqake.ports import JsonUI, PRJsonUI, RealUI
from panqake.ports.exceptions import NonInteractiveError
from panqake.ports.protocols import UIPort


def test_json_ui_prompt_confirm_raises_non_interactive_error():
    ui = JsonUI()

    with pytest.raises(NonInteractiveError, match="confirmation"):
        ui.prompt_confirm("Proceed?", default=True)


class TestRuntimeCheckable:
    """Verify that implementations satisfy the runtime_checkable protocols."""

    def test_real_ui_is_ui_port(self):
        assert isinstance(RealUI(), UIPort)

    def test_json_ui_is_ui_port(self):
        assert isinstance(JsonUI(), UIPort)

    def test_pr_json_ui_is_ui_port(self):
        assert isinstance(PRJsonUI(), UIPort)


class TestPRJsonUI:
    """Tests for PRJsonUI behavior."""

    def test_prompt_input_returns_default(self):
        ui = PRJsonUI()
        assert ui.prompt_input("Title:", default="my-title") == "my-title"

    def test_prompt_input_multiline_returns_default(self):
        ui = PRJsonUI()
        assert ui.prompt_input_multiline("Body:", default="body") == "body"

    def test_prompt_confirm_approves_create_pr(self):
        ui = PRJsonUI()
        assert ui.prompt_confirm("Create this pull request?") is True

    def test_prompt_confirm_rejects_other_prompts(self):
        ui = PRJsonUI()
        assert ui.prompt_confirm("Push to remote?") is False

    def test_prompt_select_reviewers_returns_empty(self):
        ui = PRJsonUI()
        assert ui.prompt_select_reviewers(["alice", "bob"]) == []

    def test_print_methods_are_noops(self):
        ui = PRJsonUI()
        ui.print_success("ok")
        ui.print_error("err")
        ui.print_info("info")
        ui.print_muted("muted")
