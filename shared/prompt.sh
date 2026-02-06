# Shared prompt helpers for zsh and bash.

# Prints (venvname) when a Python virtualenv is active.
prompt_venv() {
  [[ -n "$VIRTUAL_ENV" ]] && printf '(%s)' "$(basename "$VIRTUAL_ENV")"
}

# Prints the current git branch or tag; appends "+" for staged and "*" for unstaged/untracked changes.
prompt_git() {
  command -v git >/dev/null 2>&1 || return
  local status_out branch oid staged="" dirty="" line tmp xy x y
  status_out="$(git status --porcelain=2 --branch --ignore-submodules=dirty 2>/dev/null)" || return

  while IFS= read -r line; do
    case "$line" in
      '# branch.head '*)
        branch="${line#\# branch.head }"
        ;;
      '# branch.oid '*)
        oid="${line#\# branch.oid }"
        ;;
      '1 '*|'2 '*|'u '*)
        tmp="${line#? }"
        xy="${tmp%% *}"
        x="${xy%?}"
        y="${xy#?}"
        [[ "$x" != "." ]] && staged="+"
        [[ "$y" != "." ]] && dirty="*"
        ;;
      '? '*)
        dirty="*"
        ;;
    esac
  done <<< "$status_out"

  if [[ -z "$branch" || "$branch" == "(detached)" ]]; then
    branch="$(git describe --tags --exact-match 2>/dev/null)"
  fi
  if [[ -z "$branch" || "$branch" == "(detached)" ]]; then
    [[ -n "$oid" && "$oid" != "(initial)" ]] || return
    branch="${oid:0:7}"
  fi

  printf '%s' "${branch}${staged}${dirty}"
}
