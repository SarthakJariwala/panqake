# Modify a commit

Modify stages files on the current branch and either creates a commit or amends the current one.

## Sub-features

- `modify-all-commit` stages every unstaged file and creates a new commit.
- `modify-file` stages one path.
- `modify-empty` errors when the worktree is clean.
- `modify-missing-message` refuses `--json` without `--message` when a message prompt would fire.

## How to get to it (user POV)

- Run `pq modify` and pick files in the prompt. Verification does not use this path.
- Run `pq modify --all --message "<msg>"`.
- Run `pq modify --file <path> --message "<msg>"`.
- Run `pq modify --commit` or `--no-amend` to force a new commit instead of an amend.

## Driving it with verify-panqake

Preconditions:

- `verify-panqake doctor` reports `"ok": true`.
- HEAD is `feature-ui`.
- Launch a fresh session if `feature-ui` already has commits beyond `initial`.

- **Empty worktree.** Run `verify-panqake drive --feature modify-commit -- modify --all --message "noop" --commit`. Exit code `1`. `error.type` is `NoChangesError`.
- **Create a commit.** Append a line. Run `verify-panqake append README.md "Add auth note"`. Then run `verify-panqake drive --feature modify-commit -- modify --all --message "Add auth note" --commit`. Exit code `0`. `envelope.command` is `modify`. `result.branch_name` is `feature-ui`. `result.amended` is `false`. `result.files_staged` contains `README.md`. `result.message` is `Add auth note`.
- **Git log proof.** Run `verify-panqake git -- log -1 --pretty=%s`. The subject is `Add auth note`. Run `verify-panqake git -- branch --show-current` and require `feature-ui`.
- **Missing message.** Append another line. Run `verify-panqake append README.md "Needs a message"`. Then run `verify-panqake drive --feature modify-commit -- modify --all --commit`. Exit code `2`. `error.type` is `NonInteractiveError`. `--all` stages before the message prompt, so README.md is left staged.
- **File flag.** Append another line. Run `verify-panqake append README.md "Tweak readme"`. Then run `verify-panqake drive --feature modify-commit -- modify --file README.md --message "Tweak readme" --commit`. Exit code `0`. `result.files_staged` is `["README.md"]`. The previous staged line is included in this commit.
- **List files.** Run `verify-panqake drive --feature modify-commit -- list --files`. `feature-ui.files_changed` includes `README.md` in git's `--name-status` form, such as `M\tREADME.md`.
- **Proof.** Keep the modify envelope and the `git log -1` output together. An envelope without the log is not enough.

## Gotchas

- `--json` modify still writes a git commit. There is no dry-run.
- `--all`, `--file`, and `--staged-only` cannot be combined. Typer exits before a JSON envelope if they are.
- On a branch whose only commit is the branch point, Panqake creates a new commit rather than amending. This recipe still passes `--commit` so later commits keep a new log subject instead of amending.
- `--json` modify without `--message` raises `NonInteractiveError` when a new commit needs a message. `--all` stages first, so that error leaves files staged. Amend can succeed without `--message`.
- Edit files inside the fixture `repo` path. Editing the Panqake checkout does not feed this command.
