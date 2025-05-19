# `up`

The `up` command moves you from your current branch to its parent branch in the stack. It identifies the current branch's parent from the stack metadata.

`up` is particularly useful when you need to quickly navigate to the parent branch without having to manually switch branches using the `switch` command.

::: tip
`up` is often used in conjunction with `down` for quick navigation within the stack.
:::

## Usage

```bash
pq up
```

## Examples

### Basic Usage

If you're on a child branch (`feature-auth-ui`) that has a parent:

```bash
main
└── feature-backend
      └── feature-auth
            └── * feature-auth-ui (current)
```

```bash
$ pq up
Switched to branch 'feature-auth'

main
└── feature-backend
      └── * feature-auth (current)
            └── feature-auth-ui
```
