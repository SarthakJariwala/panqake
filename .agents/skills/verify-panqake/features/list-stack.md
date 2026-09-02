# List the stack

List shows the tracked branch tree for the current stack, names the current branch, and can include per-branch files changed against the parent.

## Sub-features

- `list-default` prints the stack that contains the current branch.
- `list-ls` is the `ls` alias for the same tree.
- `list-files` adds `files_changed` for each child relative to its parent.
- `list-target` lists from a named branch without switching.

## How to get to it (user POV)

- Run `pq list`.
- Run `pq ls`.
- Run `pq list --files` or `pq ls -f`.
- Run `pq list <branch>` to start from a named branch.

## Driving it with verify-panqake

Preconditions:

- `verify-panqake doctor` reports `"ok": true`.
- The seeded stack is `main`, then `feature-auth`, then `feature-ui`.
- HEAD is `feature-ui`.

- **Default list.** Show the current stack. Run `verify-panqake drive --feature list-stack -- list`. Exit code `0`. `envelope.ok` is `true`. `envelope.command` is `list`. `result.current_branch` and `result.target_branch` are `feature-ui`. `result.root_branch` is `main`. `result.tree.name` is `main`. `result.tree.children[0].name` is `feature-auth`. That child's only child is `feature-ui`.
- **Alias.** List through `ls`. Run `verify-panqake drive --feature list-stack -- ls`. Exit code `0`. `envelope.command` is `list`. The tree matches the default list.
- **Files.** Include file breakdowns. Run `verify-panqake drive --feature list-stack -- list --files`. Exit code `0`. `feature-auth.files_changed` is `[]` at seed. `main.files_changed` is `null` because it has no parent in the stack.
- **Named target.** List from `main` without switching. Run `verify-panqake drive --feature list-stack -- list main`. Exit code `0`. `result.target_branch` is `main`. `result.current_branch` is still `feature-ui`. Confirm HEAD with `verify-panqake git -- branch --show-current`. The output is `feature-ui`.
- **Proof.** Keep `latest.json` plus the named-target drive record. Both envelopes identify Panqake command `list` and the seeded names `main`, `feature-auth`, and `feature-ui`.

## Gotchas

- `pq list` with no tracked children still succeeds. A fresh git repo that was not launched through this helper shows `tree.children` as `[]` and is not the seeded baseline.
- `--json` list is not a dry-run of anything else. It does not create branches.
- `uv run --directory` of the Panqake repo lists that repo's stack, not the fixture. Doctor must stay green before you trust a list.
- `ls` is an alias. Assert `envelope.command == "list"`, not `"ls"`.
