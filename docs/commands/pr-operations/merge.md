# `merge`

The `merge` command merges a pull request for a branch and updates all dependent branches to be based on the new state of the target branch. It ensures that the branch hierarchy remains intact after merges.

`panqake` will prompt you to select one of `squash`, `rebase`, or `merge` strategies. It will also warn you if the required CI checks have not passed.

::: info
This command requires `gh` CLI to be installed and authenticated. See [installation](../installation) for information.
:::

For instance, if your stack looks like the following before merging `feature-backend` into `main`:

```bash
# Before merge:
main
  └── feature-backend
        ├── feature-frontend
        └── feature-tests
```

After merging, `panqake` will update the branch hierarchy as follows:

```bash
# After merge:
main
  ├── feature-frontend
  └── feature-tests
```

## Usage

```bash
pq merge [BRANCH_NAME]
```

## Arguments

| Argument | Description |
|----------|-------------|
| `BRANCH_NAME` | Optional branch to merge |

## Options

| Option | Description |
|--------|-------------|
| `--no-delete-branch` | Don't delete the local branch after merging |
| `--no-update-children` | Don't update child branches after merging |

## Examples

### Merging the Current Branch's PR

```bash
pq merge
```

### Merging a Specific Branch's PR

```bash
pq merge feature-backend
```
