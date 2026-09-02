---
name: verify-panqake
description: >-
  Drive the Panqake git-stacking CLI (pq / panqake) on an isolated git fixture
  with --json. Use when verifying Panqake user-facing commands, proving a CLI
  change, or running a feature from .agents/skills/verify-panqake/features/.
---

# Verify Panqake

Panqake is a git-stacking CLI. Users run `pq` or `panqake`. Interactive prompts fire when required arguments are missing. Verification always uses `--json` so those prompts become `NonInteractiveError` instead of a hang.

The primary surface is the CLI. The docs site under `docs/` is not this skill's target. GitHub commands (`pr`, `submit`, `merge`, `sync`) need `gh` and a remote. They are not in the feature map yet.

Read `features/README.md` before driving. Then use the matching feature file.

## Launch

Panqake is a short-lived CLI. There is no server. Launch means install deps once, then create one isolated fixture per run.

From the Panqake repo root:

```bash
./.agents/skills/verify-panqake/bin/verify-panqake launch
```

Ready when stdout is a JSON object with `run_id`, `home`, `repo`, `evidence`, and `pq`. The fixture is a git repo on `main` with seeded branches `feature-auth` and `feature-ui`. HEAD is `feature-ui`. `HOME` for every later command is `home`, not the user's home.

Do not use `uv run --directory <this-repo>`. That changes cwd into the product checkout and will create real branches. The helper runs `.venv/bin/pq` with cwd set to the fixture.

If `.venv/bin/pq` is missing, the helper runs `uv sync --locked --all-extras --dev --python 3.12` in the project root first.

Teardown is `cleanup`. It deletes the session directory and leaves evidence.

## Doctor

Run this first, after any failed drive, and on every fresh session:

```bash
./.agents/skills/verify-panqake/bin/verify-panqake doctor
```

Require `"ok": true`. Doctor checks that the pq binary exists, the git toplevel is the fixture, `HOME` isolation points at the session home, `~/.panqake/stacks.json` is not the user's file, the stack key is the fixture basename, and `pq list --json` returns `"ok": true`.

Refuse to drive when doctor fails. Do not drive the Panqake checkout. Do not drive a repo whose basename is `workspace`. Do not drive without this helper setting `HOME`.

## Drive

Use the helper. It cds into the fixture, sets `HOME`, strips `GIT_DIR` and related git overrides, and appends `--json` when missing.

```bash
./.agents/skills/verify-panqake/bin/verify-panqake drive --feature list-stack -- list
./.agents/skills/verify-panqake/bin/verify-panqake drive -- new auth-backend main
./.agents/skills/verify-panqake/bin/verify-panqake git -- branch --show-current
./.agents/skills/verify-panqake/bin/verify-panqake stacks
```

`--feature` records the feature id in the evidence file. Treat every argv after `--` as literal pq flags.

`--json` without a required argument exits `2` with `NonInteractiveError`. That is expected. Do not fall back to interactive `pq`.

Pass both `BRANCH_NAME` and `BASE_BRANCH` to `new`. `pq new feature-auth --json` still prompts for the base and will fail in this mode.

Destructive local commands need their skip flags. Examples: `delete --yes`, `update --no-push --yes`.

Inspect git side effects with `verify-panqake git`, not with `git` in the product repo.

## Evidence

Proof lives in `/tmp/panqake-verify-evidence/<run_id>/`. Each drive writes `NNN-<command>.json` and updates `latest.json`. Cleanup must not delete that directory.

A proof includes all of these:

- The exact helper command, including `--feature`
- The JSON envelope (`ok`, `command`, `result` or `error`)
- The process exit code
- A second view of the side effect (`verify-panqake git` and/or `verify-panqake stacks`)

Do not treat pytest, Typer `CliRunner`, or fakes in `src/panqake/testing/` as proof. Those are unit tests. Drive the real `pq` binary against a real git repo.

`--json` is not a dry-run. `new`, `modify`, `delete`, `rename`, `move`, and `update` change git refs and `stacks.json`. Confirm with `git` and `stacks`.

Copy proof you want to keep into `/opt/cursor/artifacts/` before the machine goes away. The `/tmp` evidence directory is the skill's named store.

## Cleanup

```bash
./.agents/skills/verify-panqake/bin/verify-panqake cleanup
```

This removes `/tmp/panqake-verify/<run_id>/` only. It unsets `current` when it points at that run. It does not kill processes by name. It does not delete `/tmp/panqake-verify-evidence/<run_id>/`.

Failed launches can leave a partial session directory. `launch` with the same `PANQAKE_VERIFY_RUN` deletes an incomplete dir and recreates it. A complete `session.json` is reused.

After cleanup, confirm evidence still exists:

```bash
test -d /tmp/panqake-verify-evidence/<run_id>
ls /tmp/panqake-verify-evidence/<run_id>
```

## Helpers

The only helper is `.agents/skills/verify-panqake/bin/verify-panqake`. It is executable. Run it from the Panqake repo so it can find `pyproject.toml`.

```text
verify-panqake launch
verify-panqake doctor [--run RUN_ID]
verify-panqake drive [--run RUN_ID] [--feature FEATURE_ID] -- <pq args>
verify-panqake git [--run RUN_ID] -- <git args>
verify-panqake stacks [--run RUN_ID]
verify-panqake cleanup [--run RUN_ID]
```

`--run` defaults to `PANQAKE_VERIFY_RUN` or `/tmp/panqake-verify/current`. Concurrent runs must pass distinct `--run` values or set `PANQAKE_VERIFY_RUN`. Two runs may proceed side by side. Each owns its HOME and its repo basename (`pqv-<run_id>`). Panqake keys `stacks.json` by that basename, so a shared HOME would collide. This helper never shares HOME.

Keep the map honest with `/maintain-verification-skill`. The skill directory is `.agents/skills/verify-panqake/`, not `.cursor/skills/`.
