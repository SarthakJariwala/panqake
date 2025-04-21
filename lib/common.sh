#!/bin/bash
# Common functions for panqake git-stacking utilities

PANQAKE_DIR="$HOME/.panqake"
STACK_FILE="$PANQAKE_DIR/stacks.json"

# Initialize panqake directories and files
init_panqake() {
  if [ ! -d "$PANQAKE_DIR" ]; then
      mkdir -p "$PANQAKE_DIR"
  fi

  if [ ! -f "$STACK_FILE" ]; then
    echo "{}" > "$STACK_FILE"
  fi
}

# Check if we're in a git repository
is_git_repo() {
  if ! git rev-parse --is-inside-work-tree > /dev/null 2>&1; then
    echo "Error: Not in a git repository"
    exit 1
  fi
}

# Get the current repository identifier
get_repo_id() {
  git rev-parse --show-toplevel | xargs basename
}

# Get the current branch name
get_current_branch() {
  git symbolic-ref --short HEAD 2>/dev/null
}

# Check if a branch exists
branch_exists() {
  local branch="$1"
  git show-ref --verify --quiet "refs/heads/$branch"
  return $?
}

# Get parent branch of the given branch
get_parent_branch() {
  local branch="$1"
  local repo_id=$(get_repo_id)

  # Use jq to extract parent branch from the stack file
  if [ -f "$STACK_FILE" ]; then
    jq -r ".[\"$repo_id\"][\"$branch\"].parent // \"\"" "$STACK_FILE"
  else
    echo ""
  fi
}

# Get all child branches of the given branch
get_child_branches() {
  local branch="$1"
  local repo_id=$(get_repo_id)

  if [ -f "$STACK_FILE" ]; then
    jq -r ".[\"$repo_id\"] | to_entries[] | select(.value.parent == \"$branch\") | .key" "$STACK_FILE"
  fi
}

# Add a branch to the stack
add_to_stack() {
  local branch="$1"
  local parent="$2"
  local repo_id=$(get_repo_id)

  # Create the repository entry if it doesn't exist
  if ! jq -e ".[\"$repo_id\"]" "$STACK_FILE" > /dev/null 2>&1; then
    jq ". + {\"$repo_id\": {}}" "$STACK_FILE" > "$STACK_FILE.tmp" && mv "$STACK_FILE.tmp" "$STACK_FILE"
  fi

  # Add the branch and its parent
  jq ".[\"$repo_id\"][\"$branch\"] = {\"parent\": \"$parent\"}" "$STACK_FILE" > "$STACK_FILE.tmp" && mv "$STACK_FILE.tmp" "$STACK_FILE"
}

# Remove a branch from the stack
remove_from_stack() {
  local branch="$1"
  local repo_id=$(get_repo_id)

  jq ".[\"$repo_id\"] |= del(.[\"$branch\"])" "$STACK_FILE" > "$STACK_FILE.tmp" && mv "$STACK_FILE.tmp" "$STACK_FILE"
}

# Check if a command exists
command_exists() {
  command -v "$1" >/dev/null 2>&1
}

# Check for required dependencies
check_dependencies() {
  if ! command_exists jq; then
    echo "Error: jq is required but not installed."
    echo "Please install jq with your package manager:"
    echo "  - macOS: brew install jq"
    echo "  - Ubuntu/Debian: sudo apt install jq"
    echo "  - CentOS/RHEL: sudo yum install jq"
    exit 1
  fi
}

# Initialize on script load
check_dependencies
init_panqake
is_git_repo
