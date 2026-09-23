"""Parse and validate local PR attachments at input boundaries."""

import re
import shlex
from pathlib import Path

from panqake.ports.results import MAX_PR_ATTACHMENTS, PRAttachment


def parse_interactive_attachment(raw: str) -> str:
    """Accept one local Markdown reference or a terminal-dropped file path."""
    text = raw.strip()
    markdown = re.fullmatch(r"!?\[([^\]]*)\]\((.+)\)", text)
    if markdown:
        alt, path = markdown.groups()
        return PRAttachment(
            path=path.strip().removeprefix("<").removesuffix(">"), alt_text=alt or None
        ).to_gh_value()
    # Preserve plain paths containing spaces; terminals may quote or escape them.
    if not Path(text.partition("#")[0]).expanduser().is_file():
        words = shlex.split(text)
        if len(words) != 1:
            raise ValueError("Enter one file at a time; quote paths containing spaces")
        text = words[0]
    return text


def resolve_pr_attachments(raw: list[str]) -> list[PRAttachment]:
    if len(raw) > MAX_PR_ATTACHMENTS:
        raise ValueError(f"cannot attach more than {MAX_PR_ATTACHMENTS} files")
    attachments: list[PRAttachment] = []
    seen: set[Path] = set()
    for item in raw:
        attachment = PRAttachment.parse(item)
        lookup = Path(attachment.path).expanduser()
        if not lookup.is_file():
            raise ValueError(f"attachment '{attachment.path}' is not a file")
        resolved = lookup.resolve()
        if resolved in seen:
            raise ValueError(f"cannot attach the same file twice: '{attachment.path}'")
        seen.add(resolved)
        gh_path = str(lookup) if attachment.path.startswith("~") else attachment.path
        attachments.append(PRAttachment(path=gh_path, alt_text=attachment.alt_text))
    return attachments
