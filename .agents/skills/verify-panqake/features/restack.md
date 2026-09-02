# Restack locally

Restack changes parent/child links or replays descendants onto an updated parent without talking to GitHub.

## Sub-features

- `update-no-push` rebases descendants onto the current branch and skips remotes.
- `rename` renames a tracked branch and keeps its children.
- `delete-yes` deletes a branch, removes it from the stack, and relinks children.
- `track-untrack` adds or removes stack metadata for an existing git branch.
- `move-to` rebases a tracked branch onto a new parent.

## How to get to it (user POV)

- Run `pq update` after changing a parent.
- Run `pq rename <old> <new>`.
- Run `pq delete <branch>`.
- Run `pq track <branch> --parent <parent>`.
- Run `pq untrack <branch>`.
- Run `pq move <branch> --to <parent>` (alias `reparent`).

## Driving it with verify-panqake

Preconditions:

- Start from a fresh `launch`. These recipes mutate the stack.
- `verify-panqake doctor` reports `"ok": true`.
- Do not pass push flags that need a remote. Use `--no-push` on `update`.

- **Update without push.** Switch to `main`. Run `verify-panqake drive --feature restack -- switch main` then `verify-panqake drive --feature restack -- update main --no-push --yes`. Exit code `0`. `envelope.command` is `update`. `result.skip_push` is `true`. `result.affected_branches` includes `feature-auth` and `feature-ui`. `result.pushed_branches` is `[]`.
- **Rename.** Run `verify-panqake drive --feature restack -- switch feature-auth` then `verify-panqake drive --feature restack -- rename feature-auth feature-backend`. Exit code `0`. `result.old_name` is `feature-auth`. `result.new_name` is `feature-backend`. `result.was_tracked` is `true`. `verify-panqake drive --feature restack -- list` shows `feature-backend` in place of `feature-auth`, still parenting `feature-ui`.
- **Delete.** Switch to `main`. Run `verify-panqake drive --feature restack -- switch main` then `verify-panqake drive --feature restack -- delete feature-ui --yes`. Exit code `0`. `result.status` is `deleted`. `result.removed_from_stack` is `true`. `verify-panqake git -- branch --list` does not contain `feature-ui`.
- **Track and untrack.** Create a git branch that Panqake does not know. Run `verify-panqake git -- checkout -b leftover main`. Then `verify-panqake drive --feature restack -- track leftover --parent main`. Exit code `0`. `result.branch_name` is `leftover`. `verify-panqake drive --feature restack -- list leftover` shows `leftover` under `main`. Then `verify-panqake drive --feature restack -- untrack leftover`. Exit code `0`. `result.was_tracked` is `true`. `verify-panqake git -- branch --show-current` is still `leftover`. Untrack does not delete the git branch.
- **Move.** Track `leftover` again if needed. Create `sibling` with `verify-panqake drive --feature restack -- new sibling main`. Switch to `leftover`. Run `verify-panqake drive --feature restack -- move leftover --to sibling`. Exit code `0`. `envelope.command` is `move`. `result.new_parent` is `sibling`. `result.no_op` is `false`. `verify-panqake stacks` shows `leftover.parent` as `sibling`.
- **Proof.** Pair each mutating envelope with `verify-panqake drive -- list` or `verify-panqake stacks` and, for delete/untrack, `verify-panqake git -- branch --list`.

## Gotchas

- `update` without `--no-push` tries to push. On this fixture that is the wrong path.
- `--json` does not skip the delete confirmation. Pass `--yes`.
- `move` requires the branch to be tracked. `BranchNotFoundError` with "Run `pq track`" means you untracked it first.
- `untrack` leaves the git branch. `delete` removes it.
- `pr`, `submit`, `merge`, and `sync` are not this feature. A green local restack is not GitHub proof.
