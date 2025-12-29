# Shared prompt helpers for zsh and bash.

# Prints (venvname) when a Python virtualenv is active.
prompt_venv() {
  [[ -n "$VIRTUAL_ENV" ]] && printf '(%s)' "$(basename "$VIRTUAL_ENV")"
}

# Prints the current git branch or tag; appends "+" for staged and "*" for unstaged/untracked changes.
prompt_git() {
  command -v git >/dev/null 2>&1 || return
  git rev-parse --is-inside-work-tree >/dev/null 2>&1 || return

  local b staged="" dirty=""
  b=$(git symbolic-ref --quiet --short HEAD 2>/dev/null \
      || git describe --tags --exact-match 2>/dev/null \
      || git rev-parse --short HEAD 2>/dev/null) || return

  git diff --quiet --ignore-submodules --cached || staged="+"
  git diff --quiet --ignore-submodules || dirty="*"

  if [[ -z "$dirty" ]]; then
    if git ls-files --others --exclude-standard --directory --no-empty-directory 2>/dev/null | read -r _; then
      dirty="*"
    fi
  fi

  printf '%s' "$b$staged$dirty"
}
