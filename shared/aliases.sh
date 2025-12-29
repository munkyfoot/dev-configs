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
  _venv_activate() {
    source "$1/bin/activate"
    printf '%s✓ Virtual environment activated: %s%s%s\n' \
      "$_dc_color_cyan" "$_dc_color_magenta" "$(basename "$VIRTUAL_ENV")" "$_dc_color_reset"
  }

  _venv_create() {
    printf '%s▷ Creating new virtual environment...%s\n' "$_dc_color_yellow" "$_dc_color_reset"
    python3 -m venv .venv
    printf '%s✓ New virtual environment created successfully!%s\n' "$_dc_color_green" "$_dc_color_reset"
    _venv_activate .venv
  }

  if [ -d ".venv" ]; then
    _venv_activate .venv
  elif [ -d "venv" ]; then
    _venv_activate venv
  elif [[ "$1" == "-f" ]]; then
    _venv_create
  else
    printf '%s✗ No venv directory found.%s\n' "$_dc_color_red" "$_dc_color_reset"
    printf '%sCreate a new virtual environment? (y/N)%s\n' "$_dc_color_yellow" "$_dc_color_reset"
    read -r response
    case "$response" in
      [yY][eE][sS]|[yY])
        _venv_create
        ;;
      *)
        printf '%s✗ Operation aborted.%s\n' "$_dc_color_red" "$_dc_color_reset"
        return 1
        ;;
    esac
  fi
}

# mcd DIR
# Make directory if needed and cd into it.
mcd() {
  if [ -d "$1" ]; then
    cd "$1"
  else
    mkdir -p "$1"
    cd "$1"
  fi
}

# mcode DIR
# Ensure directory exists and open it in VS Code.
mcode() {
  if [ -d "$1" ]; then
    code "$1"
  else
    mkdir -p "$1"
    code "$1"
  fi
}

# help message
help() {
  printf '%sAvailable helper functions:%s\n' "$_dc_color_cyan" "$_dc_color_reset"
  printf '%svenv [-f]%s - Activate local Python virtualenv; with -f, create if missing.\n' \
    "$_dc_color_yellow" "$_dc_color_reset"
  printf '%smcd DIR%s - Create DIR (if needed) and cd into it.\n' "$_dc_color_yellow" "$_dc_color_reset"
  printf '%smcode DIR%s - Create DIR (if needed) and open it in VS Code.\n' \
    "$_dc_color_yellow" "$_dc_color_reset"
}
