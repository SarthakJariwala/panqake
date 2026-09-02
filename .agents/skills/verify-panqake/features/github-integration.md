# GitHub integration

GitHub integration pushes stacked branches to `origin`, opens or updates pull requests through `gh`, merges an open PR, and syncs local branches with remote `main`.

## Sub-features

- `merge-missing-pr` refuses merge when the branch has no open PR.
- `pr-skip-unpushed` skips PR creation when the head is not on the remote and `--push` is omitted.
- `submit-push-only` pushes the branch and does not create a PR without `--create-pr`.
- `submit-create-pr` pushes and creates one draft PR for the current branch.
- `pr-create-child` creates a draft PR for the stacked child when the parent already has an open PR.
- `pr-already-exists` reports `already_exists` when the target already has an open PR.
- `pr-attach-image` attaches a local image on create and rewrites it into the PR body.
- `merge-squash` squash-merges a non-draft parent PR and retargets the child.
- `sync-keep-merged` pulls remote `main` without deleting merged locals or pushing.

## How to get to it (user POV)

- Run `pq pr [BRANCH]` to create missing PRs from the oldest stack branch without a PR up to the target.
- Run `pq submit [BRANCH]` to push the current branch and optionally create one PR.
- Run `pq merge [BRANCH]` to merge that branch's open PR and restack children.
- Run `pq sync [MAIN]` to pull `main` and rebase stacked children.

## Driving it with verify-panqake

Preconditions:

- `GITHUB_PAT` is set (or `GH_TOKEN` / `GITHUB_TOKEN`) with Contents: write and Pull requests: write on `SarthakJariwala/panqake-verify-repo`. `gh` is on PATH.
- `verify-panqake launch --github` succeeded. Launch JSON has `"github": true` and a `branch_prefix`.
- `verify-panqake doctor` reports `"ok": true`.
- `verify-panqake github-prepare` succeeded. Read `auth_branch` as `AUTH` and `ui_branch` as `UI` from that JSON. Substitute those names into every command below.
- Do not push seeded `feature-auth` or `feature-ui`. Those names are not unique on the shared repo.

- **Missing PR.** Merge before any PR exists. Run `verify-panqake drive --feature github-integration -- merge AUTH --method squash --allow-failed-checks --yes`. Exit code is not `0`. `envelope.ok` is `false`. `error.type` is `PRMergeError`.
- **Skip unpushed.** Create PRs without pushing. Run `verify-panqake drive --feature github-integration -- pr AUTH --draft --defaults --yes --no-reviewers`. Exit code `0`. `envelope.command` is `pr`. The AUTH result has `status` `skipped` and `skip_reason` `not_pushed`.
- **Submit without PR.** Push AUTH only. Run `verify-panqake drive --feature github-integration -- submit AUTH --no-create-pr`. Exit code `0`. `envelope.command` is `submit`. `result.branch_name` is AUTH. `result.pr_existed` is `false`. `result.pr_created` is `false`. `result.pr_url` is `null`. `verify-panqake git -- ls-remote --heads origin AUTH` prints a ref for AUTH. `verify-panqake gh -- pr view AUTH --json url,state` fails because there is no PR.
- **Missing attachment.** Run `verify-panqake drive --feature github-integration -- pr AUTH --attach ./missing-shot.png --draft --defaults --yes --no-reviewers`. Exit code `2`. Output mentions that the attachment is not a file.
- **Submit create.** Write the screenshot. Run `verify-panqake png shot.png`. Then create AUTH's PR with that file. Run `verify-panqake drive --feature github-integration -- submit AUTH --create-pr --attach ./shot.png --push --draft --defaults --yes --no-reviewers`. Exit code `0`. `result.pr_created` is `true`. `result.pr_url` contains `/pull/`. `verify-panqake gh -- pr view AUTH --json body,isDraft,baseRefName,headRefName,state,url` shows `state` `OPEN`, `isDraft` `true`, `baseRefName` `main`, `headRefName` AUTH. `body` contains a GitHub upload URL, not only `./shot.png`.
- **Create child PR.** Open the rest of the stack. Run `verify-panqake drive --feature github-integration -- pr UI --push --draft --defaults --yes --no-reviewers`. Exit code `0`. `result.starting_branch` is UI. The only result is UI with `status` `created` and a `pr_url`. AUTH is not in `results` because it already has an open PR. `verify-panqake gh -- pr view UI --json baseRefName,headRefName,isDraft,state` shows `baseRefName` AUTH, `headRefName` UI, `state` `OPEN`, `isDraft` `true`.
- **Already exists.** Run `verify-panqake drive --feature github-integration -- pr UI --draft --defaults --yes --no-reviewers`. Exit code `0`. The UI result `status` is `already_exists`.
- **Mark ready.** GitHub refuses to merge drafts. Run `verify-panqake gh -- pr ready AUTH`. Then `verify-panqake gh -- pr view AUTH --json isDraft,state` shows `isDraft` `false` and `state` `OPEN`.
- **Merge parent.** Land AUTH. Run `verify-panqake drive --feature github-integration -- merge AUTH --method squash --allow-failed-checks --yes`. Exit code `0`. `envelope.command` is `merge`. `result.merge_method` is `squash`. `result.remote_branch_deleted` is `true`. `result.local_branch_deleted` is `true`. `verify-panqake gh -- pr view AUTH --json state` shows `MERGED`. `verify-panqake gh -- pr view UI --json baseRefName,state` shows `state` `OPEN` and `baseRefName` `main`.
- **Sync.** Pull the merged `main`. Run `verify-panqake drive --feature github-integration -- sync main --keep-merged --no-push`. Exit code `0`. `envelope.command` is `sync`. `result.skip_push` is `true`. `result.main_branch` is `main`.
- **Proof.** Keep the submit/pr/merge envelopes with the matching `verify-panqake gh -- pr view` JSON. An envelope without the GitHub view is not enough. After `cleanup`, `github-cleanup.json` exists under the evidence directory and `origin/main` still exists.

## Gotchas

- `GITHUB_PAT` is required for `--github`. Isolated `HOME` hides the user's `gh auth login`. This helper exports `GH_TOKEN` from `GITHUB_PAT`; Panqake does not read `GITHUB_PAT` itself. The token must include Contents: write and Pull requests: write. A metadata-only PAT fails `launch --github` with `GITHUB_PAT cannot write to …`. That is `verified-unreachable`, not a product bug.
- The PAT only has access to `SarthakJariwala/panqake-verify-repo`. Do not point `origin` at any other GitHub repo.
- Under `--json`, `pr` without `--push` does not push. `submit` without `--create-pr` does not create a PR. `merge` without `--allow-failed-checks` raises `NonInteractiveError` when checks are pending or failed. `sync` without `--keep-merged` or `--delete-merged` raises `NonInteractiveError` if merged locals exist.
- Seeded `feature-auth` / `feature-ui` are local-only. Pushing them collides with other runs. Always use `github-prepare` names.
- GitHub will not merge a draft PR. `pq merge` then raises `PRMergeError`. Mark AUTH ready with `verify-panqake gh -- pr ready AUTH` (or create it with `--no-draft`) before merge.
- `pq merge` defaults to deleting the remote and local branch. That is expected after `merge-squash`.
- `pq merge` retargets child PR bases before it calls `gh pr merge`. If merge then fails (still a draft), the child may already show `baseRefName` `main` while AUTH is still `OPEN`.
- `pq pr` walks from the oldest branch without an open PR. If AUTH already has a PR, `pr UI` only processes UI.
- `--attach` needs GitHub CLI 2.99.0 or newer. `launch --github` pins a capable `gh` onto the fixture PATH. `verify-panqake png PATH` writes a 1x1 PNG into the fixture for attach recipes. The file does not need to be committed.
- `--json` is not a dry-run. These commands create real PRs and can merge them. `cleanup` must run so prefix branches do not pile up on the shared repo.
- If `launch --github` cannot see or write to the verify repo, stop and report `verified-unreachable` with the doctor or launch error. Do not fall back to the cloud agent's `gh` login.
