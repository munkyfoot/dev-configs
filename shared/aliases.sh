# Shared helper functions for zsh and bash.
# Expects DC_SHARED_DIR to be set by the caller.

# shellcheck disable=SC1090
source "${DC_SHARED_DIR}/colors.sh"

# venv [-f]
# Activates a local Python virtual environment from ./(.)venv. If not present:
# - with -f, it will create a new venv and activate it.
# - without -f, it interactively prompts to create one.
# Prints colored status lines.
venv() {
  local target_dir="" response
  local create_requested=0

  if [[ -d ".venv" ]]; then
    target_dir=".venv"
  elif [[ -d "venv" ]]; then
    target_dir="venv"
  elif [[ "${1:-}" == "-f" ]]; then
    create_requested=1
  else
    printf '%s✗ No venv directory found.%s\n' "$_dc_color_red" "$_dc_color_reset"
    printf '%sCreate a new virtual environment? (y/N)%s\n' "$_dc_color_yellow" "$_dc_color_reset"
    read -r response
    case "$response" in
      [yY][eE][sS]|[yY]) create_requested=1 ;;
      *)
        printf '%s✗ Operation aborted.%s\n' "$_dc_color_red" "$_dc_color_reset"
        return 1
        ;;
    esac
  fi

  if (( create_requested )); then
    if ! command -v python3 >/dev/null 2>&1; then
      printf '%s✗ python3 is required to create a virtual environment.%s\n' \
        "$_dc_color_red" "$_dc_color_reset"
      return 1
    fi
    printf '%s▷ Creating new virtual environment...%s\n' "$_dc_color_yellow" "$_dc_color_reset"
    if ! python3 -m venv .venv; then
      printf '%s✗ Failed to create virtual environment.%s\n' "$_dc_color_red" "$_dc_color_reset"
      return 1
    fi
    printf '%s✓ New virtual environment created successfully!%s\n' "$_dc_color_green" "$_dc_color_reset"
    target_dir=".venv"
  fi

  if [[ ! -f "${target_dir}/bin/activate" ]]; then
    printf '%s✗ Virtual environment activation script not found: %s/bin/activate%s\n' \
      "$_dc_color_red" "$target_dir" "$_dc_color_reset"
    return 1
  fi

  # shellcheck disable=SC1090
  source "${target_dir}/bin/activate"
  printf '%s✓ Virtual environment activated: %s%s%s\n' \
    "$_dc_color_cyan" "$_dc_color_magenta" "$(basename "$VIRTUAL_ENV")" "$_dc_color_reset"
}

# mcd DIR
# Make directory if needed and cd into it.
mcd() {
  if [[ -z "${1:-}" ]]; then
    printf 'Usage: mcd DIR\n' >&2
    return 2
  fi
  mkdir -p "$1" && cd "$1"
}

# mcode DIR
# Ensure directory exists and open it in VS Code.
mcode() {
  if [[ -z "${1:-}" ]]; then
    printf 'Usage: mcode DIR\n' >&2
    return 2
  fi
  mkdir -p "$1" || return
  code "$1"
}

# helper message
dc_help() {
  printf '%sAvailable helper functions:%s\n' "$_dc_color_cyan" "$_dc_color_reset"
  printf '%svenv [-f]%s - Activate local Python virtualenv; with -f, create if missing.\n' \
    "$_dc_color_yellow" "$_dc_color_reset"
  printf '%smcd DIR%s - Create DIR (if needed) and cd into it.\n' "$_dc_color_yellow" "$_dc_color_reset"
  printf '%smcode DIR%s - Create DIR (if needed) and open it in VS Code.\n' \
    "$_dc_color_yellow" "$_dc_color_reset"
  printf '%sdc_help%s - Show this helper message.\n' "$_dc_color_yellow" "$_dc_color_reset"
}
