# Create a branch

Create branch makes a new git branch, records its parent in the Panqake stack, and checks the branch out.

## Sub-features

- `new-from-main` creates a sibling of `feature-auth` off `main`.
- `new-nested` creates a child of an existing stacked branch.
- `new-duplicate` refuses a name that already exists.
- `new-missing-base` refuses `--json` when `BASE_BRANCH` is omitted.

## How to get to it (user POV)

- Run `pq new <branch> <parent>`.
- Run `pq new` and answer the name and parent prompts. Verification does not use this path.

## Driving it with verify-panqake

Preconditions:

- `verify-panqake doctor` reports `"ok": true`.
- The session is at baseline, or a fresh `launch` was just run.
- No branch named `auth-backend` or `auth-frontend` exists. Confirm with `verify-panqake git -- branch --list`.

- **Create from main.** Switch to `main`, then create. Run `verify-panqake drive --feature create-branch -- switch main` then `verify-panqake drive --feature create-branch -- new auth-backend main`. Exit code `0`. `envelope.command` is `new`. `result.branch_name` is `auth-backend`. `result.base_branch` is `main`. `result.worktree_path` is `null`. `verify-panqake git -- branch --show-current` prints `auth-backend`.
- **Nested child.** Create a dependent branch. Run `verify-panqake drive --feature create-branch -- new auth-frontend auth-backend`. Exit code `0`. `result.base_branch` is `auth-backend`. `verify-panqake drive --feature create-branch -- list` shows `auth-backend` under `main` and `auth-frontend` under `auth-backend`.
- **Duplicate name.** Create the same name again. Run `verify-panqake drive --feature create-branch -- new auth-backend main`. Exit code is not `0`. `envelope.ok` is `false`. `error.type` is `BranchExistsError`.
- **Missing base.** Omit the parent under `--json`. Run `verify-panqake drive --feature create-branch -- new missing-base-only`. Exit code `2`. `error.type` is `NonInteractiveError`.
- **Proof.** `verify-panqake stacks` contains `auth-backend` with `"parent": "main"` and `auth-frontend` with `"parent": "auth-backend"`. `verify-panqake git -- branch --list` includes both names.

## Gotchas

- `pq new <branch> --json` without a parent still prompts for the base even when HEAD would be a sensible default. Always pass both arguments.
- `--json` create is a real `git checkout -b`. Confirm with `git`, not only the envelope.
- `pq new --tree` is not in this map. Do not treat a non-tree create as coverage of worktrees.
- Creating `feature-auth` or `feature-ui` on a seeded session hits `BranchExistsError`. Use the names in this recipe.
