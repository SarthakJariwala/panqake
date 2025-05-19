# `list`

The `list` command displays all branches in your stack with their hierarchical relationships, giving you a visual overview of your branch structure.

**Aliases**: `ls`

## Usage

```bash
pq list
pq ls
```

::: tip
Use this command frequently to visualize your current stack structure
:::

## Examples

### Basic Usage

```bash
$ pq list
main
  └── feature-backend
        ├── * feature-frontend (current)
        └── feature-tests
```

In this example:
- `main` is the root branch
- `feature-backend` is a branch off of `main`
- `feature-frontend` and `feature-tests` are both branches off of `feature-backend`
- You are currently on the `feature-frontend` branch

### Complex Stack Example

```bash
$ pq list
main
  ├── docs-update
  └── auth-feature
         ├── * login-ui (current)
         │       └── login-tests
         └── signup-ui
                └── signup-tests
```

This shows a more complex branch structure with multiple levels and parallel branches.
