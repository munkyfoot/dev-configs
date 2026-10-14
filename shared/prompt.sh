# Shared prompt helpers for zsh and bash.
# Output is plain text with control characters removed; callers must still keep
# it out of prompt source (see .bash-prompt / .zsh-prompt) because branch and
# venv names may contain prompt or expansion syntax.

# Prints (venvname) when a Python virtualenv is active.
prompt_venv() {
  local name="${VIRTUAL_ENV:-}"
  name="${name%/}"
  name="${name##*/}"
  name="${name//[[:cntrl:]]/}"
  [[ -n "$name" ]] || return 1
  printf '(%s)' "$name"
}

# Prints the current git branch or tag; appends "+" for staged and "*" for unstaged/untracked changes.
# Set DC_PROMPT_GIT=0 to skip git entirely (e.g. for very large repositories).
prompt_git() {
  [[ "${DC_PROMPT_GIT:-1}" != 0 ]] || return 1
  command -v git >/dev/null 2>&1 || return
  local status_out branch oid staged="" dirty="" line tmp xy x y
  # --no-optional-locks avoids taking index.lock behind the user's back; ahead/behind
  # counts and rename detection are not displayed, so skip that work. Untracked mode is
  # explicit so a status.showUntrackedFiles=no config cannot hide the "*" marker.
  status_out="$(git --no-optional-locks status --porcelain=2 --branch --no-ahead-behind \
    --no-renames --untracked-files=normal --ignore-submodules=dirty 2>/dev/null)" || return

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
    branch="$(git --no-optional-locks describe --tags --exact-match 2>/dev/null)"
  fi
  if [[ -z "$branch" || "$branch" == "(detached)" ]]; then
    [[ -n "$oid" && "$oid" != "(initial)" ]] || return
    branch="${oid:0:7}"
  fi

  printf '%s' "${branch//[[:cntrl:]]/}${staged}${dirty}"
}
