# Image to ASCII Art Converter (shared for zsh and bash).
# Usage: img2ascii <image_path> [width]
# Requires: ImageMagick (magick/convert)

img2ascii() {
  local image_path="$1"
  local width="$2"

  [[ -f "$image_path" ]] || return 1

  if [[ -z "$width" ]]; then
    width="${COLUMNS:-}"
    if [[ -z "$width" ]]; then
      width="$(tput cols 2>/dev/null)"
    fi
    [[ -n "$width" ]] || width=80
  fi

  if ! command -v magick >/dev/null 2>&1 && ! command -v convert >/dev/null 2>&1; then
    printf 'Error: ImageMagick is required but not installed.\n' >&2
    printf 'Install with: brew install imagemagick\n' >&2
    return 1
  fi

  local chars=' .:-=+*#%@'
  local chars_len=${#chars}
  local img_info img_width img_height height

  if command -v magick >/dev/null 2>&1; then
    img_info=$(magick identify -format "%w %h" "$image_path" 2>/dev/null)
  else
    img_info=$(identify -format "%w %h" "$image_path" 2>/dev/null)
  fi

  [[ -n "$img_info" ]] || return 1
  img_width=${img_info%% *}
  img_height=${img_info##* }

  height=$(( (width * img_height) / (img_width * 2) ))
  (( height < 1 )) && height=1

  if command -v magick >/dev/null 2>&1; then
    magick "$image_path" \
      -resize "${width}x${height}!" \
      -depth 8 \
      txt:- 2>/dev/null | tail -n +2 | awk -v chars="$chars" -v chars_len="$chars_len" '
        BEGIN { esc = sprintf("%c", 27); current_row = -1; line = "" }
        function hex2dec(h,   i, c, n, v) {
          n = 0
          for (i = 1; i <= length(h); i++) {
            c = substr(h, i, 1)
            if (c ~ /[0-9]/) v = c + 0
            else if (c ~ /[A-F]/) v = 10 + index("ABCDEF", c) - 1
            else v = 10 + index("abcdef", c) - 1
            n = (n * 16) + v
          }
          return n
        }
        {
          coord = $1
          sub(/:$/, "", coord)
          split(coord, xy, ",")
          y = xy[2]

          r = 128; g = 128; b = 128
          if (match($0, /\([0-9]+,[0-9]+,[0-9]+\)/)) {
            rgb = substr($0, RSTART + 1, RLENGTH - 2)
            split(rgb, parts, ",")
            r = parts[1]; g = parts[2]; b = parts[3]
          } else if (match($0, /#[0-9A-Fa-f]{6}/)) {
            hex = substr($0, RSTART + 1, 6)
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
          if (line != "") print line esc "[0m"
        }
      '
  else
    convert "$image_path" \
      -resize "${width}x${height}!" \
      -depth 8 \
      txt:- 2>/dev/null | tail -n +2 | awk -v chars="$chars" -v chars_len="$chars_len" '
        BEGIN { esc = sprintf("%c", 27); current_row = -1; line = "" }
        function hex2dec(h,   i, c, n, v) {
          n = 0
          for (i = 1; i <= length(h); i++) {
            c = substr(h, i, 1)
            if (c ~ /[0-9]/) v = c + 0
            else if (c ~ /[A-F]/) v = 10 + index("ABCDEF", c) - 1
            else v = 10 + index("abcdef", c) - 1
            n = (n * 16) + v
          }
          return n
        }
        {
          coord = $1
          sub(/:$/, "", coord)
          split(coord, xy, ",")
          y = xy[2]

          r = 128; g = 128; b = 128
          if (match($0, /\([0-9]+,[0-9]+,[0-9]+\)/)) {
            rgb = substr($0, RSTART + 1, RLENGTH - 2)
            split(rgb, parts, ",")
            r = parts[1]; g = parts[2]; b = parts[3]
          } else if (match($0, /#[0-9A-Fa-f]{6}/)) {
            hex = substr($0, RSTART + 1, 6)
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
          if (line != "") print line esc "[0m"
        }
      '
  fi
}
