# `down`

The `down` command moves you from your current branch to one of its child branches in the stack.

If there's only one child branch, `down` command switches to it directly. But, if there are multiple child branches, it presents an interactive selection menu.

::: tip
`down` is often used in conjunction with `up` for quick navigation within the stack.
:::

## Usage

```bash
pq down
```

## Examples

### With a Single Child Branch

If your current branch has only one child:

```bash
main
└── feature-backend
      └── * feature-auth (current)
            └── feature-auth-ui
```

```bash
$ pq down
Switched to branch 'feature-auth-ui'

main
└── feature-backend
      └── feature-auth
            └── * feature-auth-ui (current)
```

### With Multiple Child Branches

If your current branch has multiple children:

```bash
$ pq down
? Select a child branch to switch to: (Use arrow keys)
 ❯ feature-auth-ui
   feature-auth-tests
```
