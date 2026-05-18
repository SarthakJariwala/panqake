# `move`

The `move` command (alias `reparent`) reparents a branch within the stack. It updates the panqake metadata, optionally updates the open PR's base on GitHub, then rebases the branch and its descendants onto the new parent so the entire subtree comes along.

This is useful when you realize a branch should sit on top of a different prerequisite — for example, sliding a branch from `main` onto a feature that turned out to be a dependency, or moving a subtree to a sibling stack.

## Usage

```bash
pq move [BRANCH_NAME] --to <NEW_PARENT>
```

## Arguments

| Argument | Description |
|----------|-------------|
| `BRANCH_NAME` | Branch to move (default: current branch) |

## Options

| Option | Description |
|--------|-------------|
| `--to` | New parent branch (if not provided, will prompt) |
| `--json` | Output machine-readable JSON |

## Examples

### Move the current branch under a new parent

```bash
pq move --to feature-x
```

### Move a specific branch

```bash
pq move feature-b --to main
```

### Move a subtree

If the branch you move has descendants, they come along automatically — each descendant is rebased onto its (rewritten) parent in turn.

## Behavior

1. Updates the parent reference in the panqake stack.
2. If the branch has an open PR, updates the PR base on GitHub (requires `gh` CLI; warns if unavailable).
3. Runs `git rebase --onto <new-parent> <old-parent> <branch>`, taking only the commits unique to the branch.
4. Recursively rebases each descendant onto its (now-rewritten) parent.
5. Returns you to the branch you started on.

## After Moving

The rebased branches have new commit SHAs, so the remotes are stale. The command prints an explicit `pq submit <branch>` line for each rebased branch — run them to force-push.

## Handling Conflicts

If a rebase conflict occurs, git is left mid-rebase so you can resolve it:

1. Resolve the conflicts in your editor.
2. Run `git rebase --continue`.
3. Run `pq update <moved-branch>` to finish rebasing any remaining descendants of the moved subtree.

The stack metadata is updated before the rebase begins, so the recovery path is clean — you don't need to re-run `pq move`. Note that `pq update` defaults to the current branch, which after a conflict is the conflicted descendant; passing the moved branch as an argument ensures all sibling descendants get rebased, not just the ones below where you ended up.

::: info
Panqake prevents cycles: you cannot move a branch onto one of its own descendants.
:::
