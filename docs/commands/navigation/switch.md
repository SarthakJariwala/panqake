# `switch`

The `switch` command allows you to change your active branch to any branch in your stack.

**Aliases**: `co` (short for "checkout")

## Usage

```bash
# Switch to a specific branch
pq switch branch-name
pq co branch-name

# Interactive branch selection
pq switch
pq co
```

## Arguments

| Argument | Description |
|----------|-------------|
| `branch-name` | The name of the branch to switch to (optional) |

## Examples

### Switch to a Specific Branch

```bash
$ pq switch feature-auth
```

### Interactive Branch Selection

If you run `pq switch` without arguments, you'll see an interactive menu:

```bash
$ pq switch
? Select a branch to switch to: (Use arrow keys)
   main
   feature-backend
 ❯ feature-auth
   feature-auth-ui
```
