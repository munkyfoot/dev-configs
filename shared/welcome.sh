# Shared welcome banner logic for zsh and bash.
# Expects DC_SHARED_DIR to be set by the caller.

# shellcheck disable=SC1090
source "${DC_SHARED_DIR}/colors.sh"

_dc_ordinal_suffix() {
  local d=$((10#$1))
  local suf="th"
  (( d % 100 >= 11 && d % 100 <= 13 )) || case $(( d % 10 )) in
    1) suf="st" ;;
    2) suf="nd" ;;
    3) suf="rd" ;;
  esac
  printf '%s' "$suf"
}

_dc_welcome_preset_art() {
  case "$1" in
    morning)
      cat <<'ART'
    ( (
     ) )
  ........
  |      |]
  \      /
   `----'
ART
      ;;
    afternoon)
      cat <<'ART'
      .
   \  |  /
 '-.*;;;*.-'
-==;;;;;;;==-
 .-'*;;;*'-.
   /  |  \
      '
ART
      ;;
    evening)
      cat <<'ART'
    ___
  .'o O'-.
 / O o_.-`\
|o_.-`  o  |
\     o_.-/
 `'--.__.'
ART
      ;;
    *)
      cat <<'ART'
 ><(((º>
ART
      ;;
  esac
}

_dc_find_custom_image() {
  local welcome_images_dir="$1"
  local part="$2"
  local ext
  local image_extensions=("png" "jpg" "jpeg" "gif" "bmp" "webp")

  for ext in "${image_extensions[@]}"; do
    if [[ -f "${welcome_images_dir}/${part}.${ext}" ]]; then
      printf '%s' "${welcome_images_dir}/${part}.${ext}"
      return 0
    fi
  done

  for ext in "${image_extensions[@]}"; do
    if [[ -f "${welcome_images_dir}/custom.${ext}" ]]; then
      printf '%s' "${welcome_images_dir}/custom.${ext}"
      return 0
    fi
  done
}

_dc_file_mtime() {
  local path="$1"
  local mtime=""
  mtime=$(stat -f %m "$path" 2>/dev/null)
  if [[ -z "$mtime" ]]; then
    mtime=$(stat -c %Y "$path" 2>/dev/null)
  fi
  printf '%s' "$mtime"
}

_dc_term_width() {
  local width="${COLUMNS:-}"
  if [[ -z "$width" ]]; then
    width="$(tput cols 2>/dev/null)"
  fi
  [[ -n "$width" ]] || width=80
  printf '%s' "$width"
}

dc_welcome_banner() {
  local script_dir="$1"
  local user_name="${WELCOME_USER_NAME:-${USER}}"
  local welcome_images_dir="${WELCOME_IMAGES_DIR:-${script_dir}/welcome-images}"

  # Time-of-day greeting
  local h part="evening"
  h=$(date +%H)
  (( h >= 5 && h < 12 )) && part="morning"
  (( h >= 12 && h < 17 )) && part="afternoon"

  # Facts
  local day suffix today
  day=$((10#$(date +%d)))
  suffix=$(_dc_ordinal_suffix "$day")
  today="$(date '+%A, %B') $day$suffix"

  local nodev="N/A" pyv="N/A"
  command -v node >/dev/null 2>&1 && nodev=$(node -v)
  if command -v python3 >/dev/null 2>&1; then
    pyv=$(python3 -V 2>&1 | sed 's/Python /v/')
  fi

  # ASCII art header (time-of-day)
  local art_color
  case "$part" in
    morning)   art_color="$_dc_color_cyan" ;;
    afternoon) art_color="$_dc_color_yellow" ;;
    evening)   art_color="$_dc_color_blue" ;;
    *)         art_color="$_dc_color_green" ;;
  esac
  printf '%s' "$art_color"

  # Try to find and convert custom image, fall back to preset ASCII art
  local custom_image
  custom_image=$(_dc_find_custom_image "$welcome_images_dir" "$part")

  if [[ -n "$custom_image" ]] && command -v img2ascii >/dev/null 2>&1; then
    local cache_dir="${welcome_images_dir}/.ascii-cache"
    local image_basename cache_file ascii_art need_generate=0
    local term_width

    term_width=$(_dc_term_width)
    image_basename=$(basename "$custom_image")
    image_basename="${image_basename%.*}"
    cache_file="${cache_dir}/${image_basename}_w${term_width}.txt"

    if [[ -f "$cache_file" ]]; then
      local image_mtime cache_mtime
      image_mtime=$(_dc_file_mtime "$custom_image")
      cache_mtime=$(_dc_file_mtime "$cache_file")
      if [[ -n "$image_mtime" && -n "$cache_mtime" && "$image_mtime" -gt "$cache_mtime" ]]; then
        need_generate=1
      else
        ascii_art=$(<"$cache_file")
      fi
    else
      need_generate=1
    fi

    if (( need_generate )); then
      ascii_art=$(img2ascii "$custom_image" "$term_width" 2>/dev/null)
      if [[ -n "$ascii_art" ]]; then
        [[ -d "$cache_dir" ]] || mkdir -p "$cache_dir"
        printf '%s' "$ascii_art" > "$cache_file"
      fi
    fi

    if [[ -n "$ascii_art" ]]; then
      printf '%s\n' "$ascii_art"
    else
      _dc_welcome_preset_art "$part"
    fi
  else
    _dc_welcome_preset_art "$part"
  fi
  printf '%s' "$_dc_color_reset"

  printf '%s%sGood %s, %s.%s It'\''s %s.\n' \
    "$_dc_color_bold" "$art_color" "$part" "$user_name" "$_dc_color_reset" "$today"
  printf '\n'
  printf '%sCurrent Environment%s\n' "$_dc_color_magenta" "$_dc_color_reset"
  printf ' - %sNode%s %s\n' "$_dc_color_green" "$_dc_color_reset" "$nodev"
  printf ' - %sPython%s %s\n' "$_dc_color_green" "$_dc_color_reset" "$pyv"
  printf '\n'
}
