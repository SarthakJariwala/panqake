"""Interactive attachment input and shared PR creation behavior."""

import shlex

import pytest
from prompt_toolkit.application import create_app_session
from prompt_toolkit.input import create_pipe_input
from prompt_toolkit.output import DummyOutput

from panqake.commands.pr import create_pull_requests_core
from panqake.commands.submit import update_pull_request_core
from panqake.ports import PRJsonUI, RealUI, UserCancelledError
from panqake.ports.results import PRAttachment
from panqake.testing.fakes import FakeConfig, FakeGit, FakeGitHub, FakeUI
from panqake.utils.pr_attachments import (
    parse_interactive_attachment,
    resolve_pr_attachments,
)


@pytest.mark.parametrize("style", ["plain", "quoted", "escaped", "markdown", "link"])
def test_attachment_paths_with_spaces(tmp_path, style):
    path = tmp_path / "screen shot (after).png"
    path.touch()
    inputs = {
        "plain": str(path),
        "quoted": shlex.quote(str(path)),
        "escaped": str(path)
        .replace(" ", r"\ ")
        .replace("(", r"\(")
        .replace(")", r"\)"),
        "markdown": f"![After login](<{path}>)",
        "link": f"[After login]({path})",
    }
    result = resolve_pr_attachments([parse_interactive_attachment(inputs[style])])
    assert result == [
        PRAttachment(
            str(path), "After login" if style in {"markdown", "link"} else None
        )
    ]


def test_prompt_retries_invalid_and_duplicate_files(tmp_path, monkeypatch):
    image = tmp_path / "image.png"
    video = tmp_path / "demo.mp4"
    image.touch()
    video.touch()
    answers = iter(
        ["missing.png", str(image), f"![Duplicate]({image})", f"![Demo]({video})", ""]
    )
    ui = RealUI()
    errors = []
    monkeypatch.setattr(ui, "prompt_input", lambda *args: next(answers))
    monkeypatch.setattr(ui, "print_error", errors.append)
    assert ui.prompt_pr_attachments() == [
        PRAttachment(str(image)),
        PRAttachment(str(video), "Demo"),
    ]
    assert len(errors) == 2
    assert "not a file" in errors[0]
    assert "same file twice" in errors[1]


def test_prompt_cancel_propagates(monkeypatch):
    ui = RealUI()

    def cancel(*args):
        raise UserCancelledError()

    monkeypatch.setattr(ui, "prompt_input", cancel)
    with pytest.raises(UserCancelledError):
        ui.prompt_pr_attachments()


@pytest.mark.parametrize("command", ["pr", "submit"])
@pytest.mark.parametrize("defaults", [False, True])
def test_interactive_attachments_reach_pr_body(command, defaults):
    git = FakeGit(
        current_branch="feature",
        branches=["main", "feature"],
        pushed_branches={"main", "feature"},
        branch_commits={"feature": True},
    )
    github = FakeGitHub()
    config = FakeConfig(stack={"feature": {"parent": "main"}})
    attachments = [PRAttachment("./screenshot.png", "After")]
    ui = FakeUI(attachment_responses=[attachments])
    kwargs = dict(
        git=git,
        github=github,
        config=config,
        ui=ui,
        branch_name="feature",
        title="Feature title",
        body="Description",
        draft=False,
        reviewers=[],
        assume_yes=True,
        use_defaults=defaults,
    )
    if command == "pr":
        create_pull_requests_core(**kwargs)
    else:
        update_pull_request_core(**kwargs, create_pr=True, push=True)
    assert ui.attachment_calls == (0 if defaults else 1)
    assert github.create_pr_calls[0][3] == (
        "Description" if defaults else "Description\n\n![After](./screenshot.png)"
    )
    assert github.create_pr_calls[0][6] == (None if defaults else attachments)


def test_json_attachment_prompt_does_not_read_input():
    assert PRJsonUI().prompt_pr_attachments() == []


def test_real_prompt_accepts_terminal_input(tmp_path, capsys):
    image = tmp_path / "screen shot.png"
    image.touch()
    with create_pipe_input() as terminal:
        with create_app_session(input=terminal, output=DummyOutput()):
            terminal.send_text(f"![Login screen]({image})\n\n")
            assert RealUI().prompt_pr_attachments() == [
                PRAttachment(str(image), "Login screen")
            ]
    output = capsys.readouterr().out
    assert "![Screenshot](./screenshot.png)" in output
    assert "Attachment (Enter to finish)" in output
