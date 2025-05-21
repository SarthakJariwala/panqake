# `track`

The `track` command adds an existing Git branch to your Panqake stack, establishing its relationship with other branches. This is useful when working with branches created before adopting Panqake or integrating branches created through other means.

## Usage

```bash
pq track [BRANCH_NAME]
```

## Arguments

| Argument | Description |
|----------|-------------|
| `BRANCH_NAME` | Name of branch to track (optional) |

## Examples

### Tracking a Branch with Current Branch as Parent

```bash
pq track feature-ui
```

### Tracking a Branch with Interactive Prompts

```bash
pq track
```

::: tip
After tracking, use `pq list` to verify the branch structure. A branch can only have one parent in the stack.
:::
