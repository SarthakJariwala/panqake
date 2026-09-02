---
name: verify-panqake
description: >-
  Drive the Panqake git-stacking CLI (pq / panqake) on an isolated git fixture
  with --json. Use when verifying Panqake user-facing commands, proving a CLI
  change, or running a feature from .agents/skills/verify-panqake/features/.
---

# Verify Panqake

Panqake is a git-stacking CLI. Users run `pq` or `panqake`. Interactive prompts fire when required arguments are missing. Verification always uses `--json` so those prompts become `NonInteractiveError` instead of a hang.

The primary surface is the CLI. The docs site under `docs/` is not this skill's target. Local stack commands use a fixture with no remote. GitHub commands (`pr`, `submit`, `merge`, `sync`) use `launch --github` against `SarthakJariwala/panqake-verify-repo` and `GITHUB_PAT`.

Read `features/README.md` before driving. Then use the matching feature file.

## Launch

Panqake is a short-lived CLI. There is no server. Launch means install deps once, then create one isolated fixture per run.

From the Panqake repo root:

```bash
./.agents/skills/verify-panqake/bin/verify-panqake launch
```

GitHub recipes instead run:

```bash
./.agents/skills/verify-panqake/bin/verify-panqake launch --github
```

Ready when stdout is a JSON object with `run_id`, `home`, `repo`, `evidence`, and `pq`. The fixture is a git repo on `main` with seeded branches `feature-auth` and `feature-ui`. HEAD is `feature-ui`. `HOME` for every later command is `home`, not the user's home.

`--github` also sets `github` true, `github_repo`, `origin_url`, and `branch_prefix`. It points `origin` at `https://github.com/SarthakJariwala/panqake-verify-repo.git` (override with `PANQAKE_VERIFY_GITHUB_REPO`), maps `GITHUB_PAT` to `GH_TOKEN` for `gh` and git, and isolates `GH_CONFIG_DIR` under the session home. If the verify repo is empty it pushes `main` once. It does not push `feature-auth` or `feature-ui`.

`--github` requires `gh` on PATH and `GITHUB_PAT` (or `GH_TOKEN` / `GITHUB_TOKEN`) with **Contents: write** and **Pull requests: write** on the verify repo. A metadata-only token can `gh repo view` and still fail `launch --github`. Panqake itself never reads `GITHUB_PAT`; it shells out to `gh`. This helper is what exports `GH_TOKEN`.

Do not use `uv run --directory <this-repo>`. That changes cwd into the product checkout and will create real branches. The helper runs `.venv/bin/pq` with cwd set to the fixture.

If `.venv/bin/pq` is missing, the helper runs `uv sync --locked --all-extras --dev --python 3.12` in the project root first.

Teardown is `cleanup`. It deletes the session directory and leaves evidence. For a `--github` session it also closes this run's PRs and deletes remote branches whose names start with `branch_prefix`. It never deletes `main`.

## Doctor

Run this first, after any failed drive, and on every fresh session:

```bash
./.agents/skills/verify-panqake/bin/verify-panqake doctor
```

Require `"ok": true`. Doctor checks that the pq binary exists, the git toplevel is the fixture, `HOME` isolation points at the session home, `~/.panqake/stacks.json` is not the user's file, the stack key is the fixture basename, and `pq list --json` returns `"ok": true`.

On a `--github` session it also checks that `gh` is on PATH, a token is present, `origin` is the verify repo, `gh repo view` succeeds with that token, and gh config is under the session home.

Refuse to drive when doctor fails. Do not drive the Panqake checkout. Do not drive a repo whose basename is `workspace`. Do not drive without this helper setting `HOME`. Do not drive GitHub recipes without `--github`.

If `launch --github` or GitHub doctor fails because `GITHUB_PAT` is unset, the token lacks Contents: write / Pull requests: write, `gh` is missing, or the verify repo is unreachable, the GitHub feature is `verified-unreachable`. Record the attempted command and that prerequisite. Do not mark it verified from a local-only fixture.

## Drive

Use the helper. It cds into the fixture, sets `HOME`, strips `GIT_DIR` and related git overrides, and appends `--json` when missing. On every drive it also isolates gh config and, when `GITHUB_PAT` is set, exports it as `GH_TOKEN`.

```bash
./.agents/skills/verify-panqake/bin/verify-panqake drive --feature list-stack -- list
./.agents/skills/verify-panqake/bin/verify-panqake drive -- new auth-backend main
./.agents/skills/verify-panqake/bin/verify-panqake git -- branch --show-current
./.agents/skills/verify-panqake/bin/verify-panqake gh -- pr list --json number,url,headRefName
./.agents/skills/verify-panqake/bin/verify-panqake stacks
```

`--feature` records the feature id in the evidence file. Treat every argv after `--` as literal pq flags.

`--json` without a required argument exits `2` with `NonInteractiveError`. That is expected. Do not fall back to interactive `pq`.

Pass both `BRANCH_NAME` and `BASE_BRANCH` to `new`. `pq new feature-auth --json` still prompts for the base and will fail in this mode.

Destructive local commands need their skip flags. Examples: `delete --yes`, `update --no-push --yes`.

GitHub commands need their skip flags too. Examples: `pr --push --draft --defaults --yes`, `submit --create-pr --push --draft --defaults --yes`, `merge --method squash --allow-failed-checks --yes`, `sync --keep-merged --no-push`.

Inspect git side effects with `verify-panqake git`, not with `git` in the product repo. Inspect GitHub side effects with `verify-panqake gh`, not with the user's `gh` (that one is a different account).

## Evidence

Proof lives in `/tmp/panqake-verify-evidence/<run_id>/`. Each drive writes `NNN-<command>.json` and updates `latest.json`. Cleanup must not delete that directory.

A proof includes all of these:

- The exact helper command, including `--feature`
- The JSON envelope (`ok`, `command`, `result` or `error`)
- The process exit code
- A second view of the side effect (`verify-panqake git`, `verify-panqake stacks`, and for GitHub recipes `verify-panqake gh`)

Do not treat pytest, Typer `CliRunner`, or fakes in `src/panqake/testing/` as proof. Those are unit tests. Drive the real `pq` binary against a real git repo. GitHub recipes must hit the real verify repo.

`--json` is not a dry-run. `new`, `modify`, `delete`, `rename`, `move`, and `update` change git refs and `stacks.json`. `pr`, `submit`, `merge`, and `sync` change remotes and pull requests. Confirm with `git`, `stacks`, and `gh`.

Copy proof you want to keep into `/opt/cursor/artifacts/` before the machine goes away. The `/tmp` evidence directory is the skill's named store.

## Cleanup

```bash
./.agents/skills/verify-panqake/bin/verify-panqake cleanup
```

This removes `/tmp/panqake-verify/<run_id>/` only. It unsets `current` when it points at that run. For `--github` sessions it closes open PRs and deletes remote branches whose names start with this run's `branch_prefix`, then writes `github-cleanup.json` into the evidence directory. It does not kill processes by name. It does not delete `/tmp/panqake-verify-evidence/<run_id>/`. It does not delete `origin/main`.

Failed launches can leave a partial session directory. `launch` with the same `PANQAKE_VERIFY_RUN` deletes an incomplete dir and recreates it. A complete `session.json` is reused. A local session cannot be reused as `--github`; cleanup first.

After cleanup, confirm evidence still exists:

```bash
test -d /tmp/panqake-verify-evidence/<run_id>
ls /tmp/panqake-verify-evidence/<run_id>
```

## Helpers

The only helper is `.agents/skills/verify-panqake/bin/verify-panqake`. It is executable. Run it from the Panqake repo so it can find `pyproject.toml`.

```text
verify-panqake launch [--github]
verify-panqake doctor [--run RUN_ID]
verify-panqake drive [--run RUN_ID] [--feature FEATURE_ID] -- <pq args>
verify-panqake git [--run RUN_ID] -- <git args>
verify-panqake gh [--run RUN_ID] -- <gh args>
verify-panqake append [--run RUN_ID] PATH TEXT
verify-panqake github-prepare [--run RUN_ID]
verify-panqake stacks [--run RUN_ID]
verify-panqake cleanup [--run RUN_ID]
```

`--run` defaults to `PANQAKE_VERIFY_RUN` or `/tmp/panqake-verify/current`. Concurrent runs must pass distinct `--run` values or set `PANQAKE_VERIFY_RUN`. Two runs may proceed side by side. Each owns its HOME and its repo basename (`pqv-<run_id>`). Panqake keys `stacks.json` by that basename, so a shared HOME would collide. This helper never shares HOME.

`github-prepare` creates `{branch_prefix}-auth` on `main` and `{branch_prefix}-ui` on that auth branch, each with a commit. Use those names as `AUTH` and `UI` in the GitHub feature file. Unique prefixes keep concurrent runs from colliding on the shared verify repo.

Keep the map honest with `/maintain-verification-skill`. The skill directory is `.agents/skills/verify-panqake/`, not `.cursor/skills/`.
