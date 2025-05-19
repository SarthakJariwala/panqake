# Installation and Setup

## Installation

`panqake` can be easily installed using [uv](https://github.com/astral-sh/uv) package manager:

```bash
uv tool install panqake
```

::: details Other installation methods

Using `pipx`
```bash
pipx install panqake
```

Using `pip`
```bash
python -m pip install panqake
```
:::

## Optional Dependencies (Recommended)

While `panqake` works with Git out of the box, to unlock the full potential of `panqake`, you should [install the GitHub CLI](https://github.com/cli/cli#installation).

::: tip
GitHub CLI is required for pull request creation and management features.
:::

```bash
# macOS
brew install gh

# Windows
winget install --id GitHub.cli

# Linux
# https://github.com/cli/cli#installation
```


## Command Aliases

Panqake provides both `panqake` and `pq` commands. They are functionally identical, with `pq` serving as a convenient shorthand:

```bash
# These commands are equivalent
panqake list
pq list
```

::: info
Throughout this documentation, we'll use the `pq` command as a shorthand for `panqake`. Feel free to use either command interchangeably.
:::

## Next Steps

Now that you've installed Panqake, you're ready to start using it:

- Continue to the [Quick Start Guide](/quickstart) to learn basic usage
- Explore the [Commands Reference](/commands) for detailed information about each command
