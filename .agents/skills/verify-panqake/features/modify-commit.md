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
- **Create a commit.** Append a line to `README.md` in the fixture repo path from `launch` JSON (`repo`). Then run `verify-panqake drive --feature modify-commit -- modify --all --message "Add auth note" --commit`. Exit code `0`. `envelope.command` is `modify`. `result.branch_name` is `feature-ui`. `result.amended` is `false`. `result.files_staged` contains `README.md`. `result.message` is `Add auth note`.
- **Git log proof.** Run `verify-panqake git -- log -1 --pretty=%s`. The subject is `Add auth note`. Run `verify-panqake git -- branch --show-current` and require `feature-ui`.
- **File flag.** Append another line to `README.md`. Run `verify-panqake drive --feature modify-commit -- modify --file README.md --message "Tweak readme" --commit`. Exit code `0`. `result.files_staged` is `["README.md"]`.
- **List files.** Run `verify-panqake drive --feature modify-commit -- list --files`. `feature-ui.files_changed` includes `README.md` in git's `--name-status` form, such as `M\tREADME.md`.
- **Proof.** Keep the modify envelope and the `git log -1` output together. An envelope without the log is not enough.

## Gotchas

- `--json` modify still writes a git commit. There is no dry-run.
- `--all`, `--file`, and `--staged-only` cannot be combined. Typer exits before a JSON envelope if they are.
- On a branch whose only commit is the branch point, omit `--commit` and Panqake may amend. This recipe always passes `--commit` so the log subject is a new commit.
- Edit files inside the fixture `repo` path. Editing the Panqake checkout does not feed this command.
