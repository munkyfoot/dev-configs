# Image to ASCII Art Converter (shared for zsh and bash).
# Usage: img2ascii <image_path> [width]
# Width is an integer from 1 to 500 and defaults to the terminal width (capped at 500).
# Output is capped at 500 rows; only the first frame of animated images is used.
# Requires: ImageMagick (magick or convert). Resource limits below bound work on
# oversized images but are not a sandbox for untrusted files.

# Succeeds if $1 is a decimal integer from 1 to 500.
_dc_img2ascii_valid_width() {
  case "${1:-}" in
    [1-9]|[1-9][0-9]|[1-9][0-9][0-9]) (( $1 <= 500 )) ;;
    *) return 1 ;;
  esac
}

# Prints the terminal width (COLUMNS, then tput) capped at 500, or 80 if unknown.
_dc_img2ascii_default_width() {
  local width="${COLUMNS:-}"
  case "$width" in
    ''|0*|*[!0-9]*) width="$(tput cols 2>/dev/null)" ;;
  esac
  case "$width" in
    ''|0*|*[!0-9]*) width=80 ;;
    ????*) width=500 ;;
    *) (( width > 500 )) && width=500 ;;
  esac
  printf '%s' "$width"
}

img2ascii() {
  local image_path="${1:-}"
  local width="${2:-}"

  if [[ -z "$image_path" || $# -gt 2 ]]; then
    printf 'Usage: img2ascii <image_path> [width]\n' >&2
    return 2
  fi
  if (( $# == 2 )) && ! _dc_img2ascii_valid_width "$width"; then
    printf 'img2ascii: width must be an integer from 1 to 500: %s\n' "$width" >&2
    return 2
  fi
  if [[ ! -f "$image_path" ]]; then
    printf 'img2ascii: not a file: %s\n' "$image_path" >&2
    return 1
  fi
  [[ -n "$width" ]] || width="$(_dc_img2ascii_default_width)"

  local -a convert_cmd
  if command -v magick >/dev/null 2>&1; then
    convert_cmd=(magick)
  elif command -v convert >/dev/null 2>&1; then
    convert_cmd=(convert)
  else
    printf 'Error: ImageMagick is required but not installed.\n' >&2
    printf 'Install with: brew install imagemagick\n' >&2
    return 1
  fi

  # An absolute path keeps names like "-x.png" or "png:x" from being read as
  # options or format prefixes; "[0]" selects the first frame.
  case "$image_path" in
    /*) ;;
    *) image_path="${PWD%/}/${image_path}" ;;
  esac

  local chars=' .:-=+*#%@'

  # Subshell keeps pipefail and the resource limits away from the calling shell.
  (
    set -o pipefail
    export MAGICK_WIDTH_LIMIT="${MAGICK_WIDTH_LIMIT:-16384}"
    export MAGICK_HEIGHT_LIMIT="${MAGICK_HEIGHT_LIMIT:-16384}"
    export MAGICK_TIME_LIMIT="${MAGICK_TIME_LIMIT:-60}"
    export MAGICK_MEMORY_LIMIT="${MAGICK_MEMORY_LIMIT:-64MiB}"
    export MAGICK_MAP_LIMIT="${MAGICK_MAP_LIMIT:-128MiB}"
    export MAGICK_DISK_LIMIT="${MAGICK_DISK_LIMIT:-256MiB}"

    # Flatten alpha and force 8-bit sRGB so every pixel line carries #RRGGBB.
    # Fit within width x 1000 (aspect preserved, so tall images never produce a
    # huge intermediate), then halve rows for terminal cells: at most 500 rows.
    "${convert_cmd[@]}" "${image_path}[0]" \
      -background black -alpha remove -alpha off -colorspace sRGB \
      -resize "${width}x1000" -scale '100%x50%' \
      -type TrueColor -depth 8 \
      txt:- 2>/dev/null | awk -v chars="$chars" '
        BEGIN { esc = sprintf("%c", 27); current_row = -1; line = ""; chars_len = length(chars) }
        function hex2dec(h,   hi, lo) {
          hi = index("0123456789ABCDEF", substr(h, 1, 1)) - 1
          lo = index("0123456789ABCDEF", substr(h, 2, 1)) - 1
          return hi * 16 + lo
        }
        /^#/ { next }
        {
          coord = $1
          sub(/:$/, "", coord)
          split(coord, xy, ",")
          y = xy[2]

          r = 128; g = 128; b = 128
          if (match($0, /#[0-9A-Fa-f][0-9A-Fa-f][0-9A-Fa-f][0-9A-Fa-f][0-9A-Fa-f][0-9A-Fa-f]/)) {
            hex = toupper(substr($0, RSTART + 1, 6))
            r = hex2dec(substr(hex, 1, 2))
            g = hex2dec(substr(hex, 3, 2))
            b = hex2dec(substr(hex, 5, 2))
          }

          if (y != current_row) {
            if (current_row != -1) {
              print line esc "[0m"
            }
            line = ""
            current_row = y
          }
          gray = int((r * 299 + g * 587 + b * 114) / 1000)
          idx = int((gray * (chars_len - 1)) / 255) + 1
          c = substr(chars, idx, 1)
          line = line esc "[38;2;" r ";" g ";" b "m" c
        }
        END {
          if (line == "") exit 1
          print line esc "[0m"
        }
      '
  ) || {
    printf 'img2ascii: failed to convert image: %s\n' "$image_path" >&2
    return 1
  }
}
