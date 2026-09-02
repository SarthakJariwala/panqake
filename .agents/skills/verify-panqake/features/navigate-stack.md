# Navigate the stack

Navigate moves HEAD to a parent, a child, or a named branch in the stack without rewriting commits.

## Sub-features

- `switch-named` checks out a named branch.
- `switch-alias` does the same through `co`.
- `switch-missing-arg` refuses `--json` without a branch name.
- `up` checks out the parent.
- `down-single` checks out the only child.
- `down-named` selects one child when several exist.

## How to get to it (user POV)

- Run `pq switch <branch>` or `pq co <branch>`.
- Run `pq switch` and pick from a menu. Verification does not use this path.
- Run `pq up`.
- Run `pq down`.
- Run `pq down <child>` when the current branch has more than one child.

## Driving it with verify-panqake

Preconditions:

- `verify-panqake doctor` reports `"ok": true`.
- The seeded stack is `main`, then `feature-auth`, then `feature-ui`.
- HEAD is `feature-ui`.

- **Switch named.** Move to `main`. Run `verify-panqake drive --feature navigate-stack -- switch main`. Exit code `0`. `envelope.command` is `switch`. `result.target_branch` is `main`. `result.previous_branch` is `feature-ui`. `result.switched` is `true`. `verify-panqake git -- branch --show-current` prints `main`.
- **Alias.** Move to `feature-auth` through `co`. Run `verify-panqake drive --feature navigate-stack -- co feature-auth`. Exit code `0`. `result.target_branch` is `feature-auth`. Git current branch is `feature-auth`.
- **Up.** Move to the parent. Run `verify-panqake drive --feature navigate-stack -- up`. Exit code `0`. `envelope.command` is `up`. `result.target_branch` is `main`. Git current branch is `main`.
- **Down single.** `main` has one seeded child. Run `verify-panqake drive --feature navigate-stack -- down`. Exit code `0`. `envelope.command` is `down`. `result.target_branch` is `feature-auth`.
- **Down named.** From `main` after a second child exists, pass the child. If you are still on the seeded session, first `switch main`, then run `verify-panqake drive --feature navigate-stack -- down feature-auth`. Exit code `0`. `result.target_branch` is `feature-auth`.
- **Missing switch argument.** Run `verify-panqake drive --feature navigate-stack -- switch`. Exit code `2`. `error.type` is `NonInteractiveError`.
- **Proof.** A successful switch, up, or down is proven by the envelope and by `verify-panqake git -- branch --show-current` matching `result.target_branch`.

## Gotchas

- `pq down --json` with several children and no `CHILD` argument raises `NonInteractiveError`. Pass the child name.
- `pq up` on `main` raises `BranchNotFoundError` because the root has no parent.
- Switch to the current branch returns `switched: false` and exit `0`. That is not a failed navigation.
- These commands change HEAD. They do not change `stacks.json`. If you need the seeded HEAD again, `switch feature-ui`.
