# Panqake verification map

This directory is the maintained source for verifying the user-facing behavior of Panqake. Read the index before driving, then use the matching feature file as the recipe.

## Baseline preconditions

- Run `./.agents/skills/verify-panqake/bin/verify-panqake launch` from the Panqake repo root.
- Run `./.agents/skills/verify-panqake/bin/verify-panqake doctor` and require `"ok": true`.
- The fixture is on branch `feature-ui` in stack `main`, `feature-auth`, then `feature-ui`.
- `README.md` in the fixture contains `seed`.
- Never drive `pq` outside this helper. Never drive the Panqake product checkout.

## Driving conventions

- Start every recipe from the baseline state unless its preconditions say otherwise.
- Mutating recipes (`create-branch`, `modify-commit`, `restack`) should `launch` a fresh run if the session was already mutated.
- Treat every command as literal. Keep quoted names and flags unchanged.
- Run Panqake through `verify-panqake drive --feature <id> -- <command>`.
- Run git through `verify-panqake git -- <command>`.
- Cleanup removes the session and keeps `/tmp/panqake-verify-evidence/<run_id>/`.

## Proof and skip reporting

- Capture the command and the resulting JSON envelope, not only the final git branch.
- CLI proof includes the helper command, stdout envelope, stderr, and exit code.
- Mutation proof includes a second view via `verify-panqake git` and `verify-panqake stacks`.
- Record the feature ID (`--feature`) with every artifact.
- Report an unreachable path with the attempted command and the unmet precondition.
- Do not report a skipped entry point as verified through a different path.

## Feature entry contract

Each feature file starts with an H1 title and one paragraph describing the user-visible behavior. It then uses exactly four H2 sections in this order.

1. `Sub-features` lists short IDs with one line for each behavior.
2. `How to get to it (user POV)` lists every user entry point.
3. `Driving it with verify-panqake` starts with `Preconditions:` and uses labeled bullets that pair each user action with an exact command and observable result.
4. `Gotchas` lists traps that can waste or invalidate a verification run.

Keep implementation details out of the map. Name only user paths, stable handles, required state, commands, and observable proof.

## Features

- [List the stack](./list-stack.md) covers `pq list` / `pq ls`, `--files`, and the JSON tree.
- [Create a branch](./create-branch.md) covers `pq new` with an explicit parent, nested children, and duplicate-name errors.
- [Navigate the stack](./navigate-stack.md) covers `switch` / `co`, `up`, and `down`.
- [Modify a commit](./modify-commit.md) covers staging via `--all` / `--file`, `--commit`, empty-change errors, and git log proof.
- [Restack locally](./restack.md) covers `update --no-push`, `rename`, `delete --yes`, `track` / `untrack`, and `move --to`.

## Not in this map yet

`pr`, `submit`, `merge`, and `sync` talk to GitHub through `gh` and need a remote. `pq new --tree` creates a git worktree. Do not mark those verified from this map.
