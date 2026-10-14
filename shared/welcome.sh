# Shared welcome banner logic for zsh and bash.
# Expects DC_SHARED_DIR to be set by the caller. Image art is used only when
# shared/img2ascii.sh has been sourced first.

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
  return 1
}

_dc_find_custom_ascii() {
  local welcome_images_dir="$1"
  local part="$2"
  local ext
  local ascii_extensions=("txt" "ascii" "asc" "art")

  for ext in "${ascii_extensions[@]}"; do
    if [[ -f "${welcome_images_dir}/${part}.${ext}" ]]; then
      printf '%s' "${welcome_images_dir}/${part}.${ext}"
      return 0
    fi
  done

  for ext in "${ascii_extensions[@]}"; do
    if [[ -f "${welcome_images_dir}/custom.${ext}" ]]; then
      printf '%s' "${welcome_images_dir}/custom.${ext}"
      return 0
    fi
  done
  return 1
}

# Prints cached art from $2 if it is a regular, non-empty file not older than image $3.
# Symlinks are ignored so the cache cannot be redirected elsewhere.
_dc_welcome_read_cache() {
  local cache_dir="$1" cache_file="$2" image="$3"
  [[ ! -L "$cache_dir" && ! -L "$cache_file" && -f "$cache_file" && -s "$cache_file" ]] || return 1
  [[ "$image" -nt "$cache_file" ]] && return 1
  printf '%s\n' "$(<"$cache_file")"
}

# Writes $3 to cache file $2 via a private temp file and atomic rename.
# Refuses symlinks and fails quietly when the directory is not writable.
_dc_welcome_write_cache() {
  local cache_dir="$1" cache_file="$2" content="$3"
  [[ -L "$cache_dir" || -L "$cache_file" || -d "$cache_file" ]] && return 1
  (
    umask 077
    [[ -d "$cache_dir" ]] || mkdir -p -- "$cache_dir" || exit 1
    [[ -L "$cache_dir" ]] && exit 1
    tmp_file="$(mktemp -- "${cache_dir}/.cache.XXXXXX")" || exit 1
    if printf '%s\n' "$content" > "$tmp_file" && mv -f -- "$tmp_file" "$cache_file"; then
      exit 0
    fi
    rm -f -- "$tmp_file"
    exit 1
  ) 2>/dev/null
}

dc_welcome_banner() {
  local script_dir="$1"
  local user_name="${WELCOME_USER_NAME:-${USER}}"
  local welcome_images_dir="${WELCOME_IMAGES_DIR:-${script_dir}/welcome-images}"

  # Time-of-day greeting (10# keeps "08"/"09" from being read as octal)
  local h day weekday month part="evening"
  read -r h day weekday month <<< "$(date '+%H %d %A %B')"
  h=$((10#$h))
  (( h >= 5 && h < 12 )) && part="morning"
  (( h >= 12 && h < 17 )) && part="afternoon"

  # Facts
  local suffix today
  day=$((10#$day))
  suffix=$(_dc_ordinal_suffix "$day")
  today="$weekday, $month $day$suffix"

  local nodev="N/A" pyv="N/A"
  command -v node >/dev/null 2>&1 && nodev=$(node -v)
  if command -v python3 >/dev/null 2>&1; then
    pyv=$(python3 -V 2>&1)
    pyv="v${pyv#Python }"
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

  # Try to use custom ASCII art or convert custom image, fall back to preset ASCII art
  local custom_ascii custom_image
  custom_ascii=$(_dc_find_custom_ascii "$welcome_images_dir" "$part")
  custom_image=$(_dc_find_custom_image "$welcome_images_dir" "$part")

  if [[ -n "$custom_ascii" ]]; then
    cat -- "$custom_ascii"
  elif [[ -n "$custom_image" ]] && command -v img2ascii >/dev/null 2>&1; then
    local cache_dir="${welcome_images_dir}/.ascii-cache"
    local cache_file ascii_art="" width

    # Same bounded width img2ascii uses; the key keeps the extension so
    # custom.png and custom.jpg do not share a cache entry.
    width=$(_dc_img2ascii_default_width)
    cache_file="${cache_dir}/${custom_image##*/}_w${width}.txt"

    ascii_art=$(_dc_welcome_read_cache "$cache_dir" "$cache_file" "$custom_image")
    if [[ -z "$ascii_art" ]]; then
      ascii_art=$(img2ascii "$custom_image" "$width" 2>/dev/null) || ascii_art=""
      # Caching is best effort; the art is still shown if the write fails.
      [[ -n "$ascii_art" ]] && _dc_welcome_write_cache "$cache_dir" "$cache_file" "$ascii_art"
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
