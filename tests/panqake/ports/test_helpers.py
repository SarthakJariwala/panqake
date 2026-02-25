"""Tests for ports/helpers.py — JSON error envelope and run_command."""

import json
import warnings

import pytest

from panqake.ports.exceptions import PanqakeError
from panqake.ports.helpers import _emit_json_error, _to_jsonable, run_command
from panqake.testing.fakes import FakeUI


def test_emit_json_error_format(capsys):
    """_emit_json_error prints a well-formed JSON error envelope."""
    error = PanqakeError("something went wrong", exit_code=2)
    _emit_json_error("test-cmd", error)

    captured = capsys.readouterr()
    payload = json.loads(captured.out)

    assert payload["ok"] is False
    assert payload["command"] == "test-cmd"
    assert payload["error"]["type"] == "PanqakeError"
    assert payload["error"]["message"] == "something went wrong"
    assert payload["error"]["exit_code"] == 2


def test_to_jsonable_str_fallback_emits_warning():
    """_to_jsonable should warn when falling back to str()."""
    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")
        result = _to_jsonable(42)

    assert result == "42"
    assert len(w) == 1
    assert "_to_jsonable fell back to str()" in str(w[0].message)


def test_run_command_json_emits_error_on_panqake_error(capsys):
    """run_command with json_output=True emits a JSON error envelope and exits."""
    ui = FakeUI(strict=False)

    def failing_core():
        raise PanqakeError("bad input", exit_code=3)

    with pytest.raises(SystemExit) as exc_info:
        run_command(ui, failing_core, json_output=True, command="my-cmd")

    assert exc_info.value.code == 3

    captured = capsys.readouterr()
    payload = json.loads(captured.out)

    assert payload["ok"] is False
    assert payload["command"] == "my-cmd"
    assert payload["error"]["type"] == "PanqakeError"
    assert payload["error"]["message"] == "bad input"
    assert payload["error"]["exit_code"] == 3
