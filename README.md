# Dev Configs

Personal shell configuration for Zsh and Bash:

- **Prompt** – time, `user@host` over SSH, directory, Git branch with change markers, and the active Python virtualenv.
- **Welcome banner** – time-of-day greeting with ASCII art (built-in, your own text art, or converted images) and Node/Python versions.
- **Helpers** – `venv`, `mcd`, `mcode` and `dc_help`.
- **Image to ASCII** – `img2ascii`, used by the banner and usable on its own.
- **Terminal profile** (optional) – a macOS Terminal color profile in [`themes/Custom.terminal`](themes/Custom.terminal).

Each shell has small wrapper files (`zsh/.zsh-*`, `bash/.bash-*`) that load the shared logic in [`shared/`](shared/). Source only the pieces you want.

## Contents

- [Setup](#setup)
- [Prompt](#prompt)
- [Welcome banner](#welcome-banner)
- [Helpers](#helpers)
- [Image to ASCII](#image-to-ascii)
- [Configuration](#configuration)
- [Requirements](#requirements)
- [Troubleshooting](#troubleshooting)
- [Development](#development)

## Setup

Clone the repository and source the files **from the checkout**. The wrappers find `shared/` relative to their own location, so copying or pasting a single file into a startup file will not work. Replace `$HOME/path/to/configs` below with your checkout path, and keep the quotes if it contains spaces.

### Zsh

Add the components you want to `~/.zshrc`:

```zsh
source "$HOME/path/to/configs/zsh/.zsh-aliases"   # helpers
source "$HOME/path/to/configs/zsh/.zsh-welcome"   # welcome banner
source "$HOME/path/to/configs/zsh/.zsh-prompt"    # prompt
source "$HOME/path/to/configs/zsh/.zsh-img2ascii" # optional: img2ascii command
```

### Bash

Add the components you want to `~/.bashrc`:

```bash
source "$HOME/path/to/configs/bash/.bash-aliases"
source "$HOME/path/to/configs/bash/.bash-welcome"
source "$HOME/path/to/configs/bash/.bash-prompt"
source "$HOME/path/to/configs/bash/.bash-img2ascii" # optional
```

Bash login shells (commonly used for new macOS Terminal windows) read the first available file among `~/.bash_profile`, `~/.bash_login` and `~/.profile`, rather than `~/.bashrc`. If your existing login profile does not already load `~/.bashrc`, add this line to that file. If you have no login profile, create `~/.bash_profile` with it:

```bash
[ -f "$HOME/.bashrc" ] && . "$HOME/.bashrc"
```

### Terminal profile (optional)

Import [`themes/Custom.terminal`](themes/Custom.terminal) from macOS Terminal's Settings → Profiles using the Action menu → Import ([Apple's instructions](https://support.apple.com/guide/terminal/import-and-export-terminal-profiles-trml4299c696/mac)). It only changes appearance (colors, font, cursor, window size); the shell files do not depend on it.

## Prompt

```text
14:05:09 [user@host] configs main+* (.venv) ❯
```

| Part | Shown when |
| --- | --- |
| `user@host` | Connected over SSH |
| `main` | Inside a Git repository: the branch, else an exact tag, else a short commit hash |
| `+` | Staged changes exist |
| `*` | Unstaged changes or untracked files exist (ignored files do not count) |
| `(.venv)` | A Python virtualenv is active |

### When the prompt refreshes

| Trigger | Zsh | Bash | What is checked |
| --- | --- | --- | --- |
| A new prompt is drawn (after each command or Enter) | ✓ | ✓ | Everything, including `+`/`*` |
| Idle at the prompt, every second | ✓ | – | Nothing: the existing prompt is redrawn so the clock ticks |
| Idle at the prompt and the branch changes (e.g. `git checkout` in another pane of the same working tree) | ✓ within about 1 second | – | Branch; then a full refresh |
| The terminal window or pane regains focus | ✓ if the terminal supports focus reporting | – | Everything, including `+`/`*` |

The repository is never scanned continuously. The clock redraw only re-displays the prompt already built (Git branch, markers and venv as of the last refresh); it runs no Git or other external commands and works outside repositories and regardless of the Git settings. Zsh's idle branch check only re-reads the working tree's small `HEAD` file about once a second using shell builtins; a change triggers a full Git status refresh. File edits, staging and commits made elsewhere that leave that file unchanged update `+`/`*` at the next prompt or on focus-in. The command line and cursor position are preserved when the prompt redraws.

The clock, idle branch check and focus refresh are active only while editing at the main prompt, not while a command runs or at continuation (`PS2`) and `vared` prompts. None of them uses `TMOUT` or `TRAPALRM`, and existing ZLE widgets and hooks are kept.

### Performance and safety

- Git status runs with `--no-optional-locks`, without ahead/behind counts or rename detection, so the prompt does not take index locks. Untracked files always set `*`, even if `status.showUntrackedFiles=no` is configured.
- In very large repositories, set `DC_PROMPT_GIT=0` to remove the Git segment and all Git work from the prompt.
- Branch, tag, directory and virtualenv names are displayed as plain text and never run as prompt code, whether or not Bash `promptvars` or Zsh `PROMPT_SUBST` is enabled. Control characters are removed from Git and virtualenv labels (and from the Bash directory label); Zsh's native directory display already escapes them.
- In Bash, the prompt builder runs first in `PROMPT_COMMAND` (string or array) and passes the previous command's exit status on to your other hooks.

## Welcome banner

Printed once per interactive shell; sourcing the file again does not reprint it. The greeting and art change with the time of day: morning 05:00–11:59, afternoon 12:00–16:59, evening otherwise.

### Custom art

Put files in a `welcome-images` directory next to the shell's welcome file (`zsh/welcome-images/` or `bash/welcome-images/`, ignored by Git), or point `WELCOME_IMAGES_DIR` at another directory. The first match wins:

1. Text art for the time of day: `morning`, `afternoon` or `evening` with extension `.txt`, `.ascii`, `.asc` or `.art`
2. Text art for all times: `custom` with one of those extensions
3. An image for the time of day: same names with `.png`, `.jpg`, `.jpeg`, `.gif`, `.bmp` or `.webp`
4. An image for all times: `custom` with one of those extensions
5. Built-in art

Images are converted with [`img2ascii`](#image-to-ascii) at the terminal width (up to 500 columns) and need ImageMagick; if conversion fails, the built-in art is shown. Converted art is cached in `.ascii-cache/` inside the images directory, per image file and width, and regenerated when the image is newer. If the cache cannot be written (or is a symlink), the art is still shown without caching. Delete `.ascii-cache/` to force regeneration.

## Helpers

| Command | Description |
| --- | --- |
| `venv` | Activate `./.venv` or `./venv`. If neither exists, offer to create `./.venv` (only when input is a terminal; otherwise it prints a hint and exits). |
| `venv -f` | Activate, creating `./.venv` with `python3 -m venv` if missing. |
| `mcd DIR` | Create `DIR` if needed and `cd` into it. |
| `mcode DIR` | Create `DIR` if needed and open it in VS Code (requires the `code` command). |
| `dc_help` | List these helpers. |

`venv` runs the environment's `bin/activate` script in your shell, so only use it in directories you trust. It returns the activation script's exit status if activation fails. `mcd` and `mcode` take exactly one directory; names with spaces or a leading `-` work, and `CDPATH` is not searched.

## Image to ASCII

Requires [ImageMagick](https://imagemagick.org) (`magick`, or `convert` from ImageMagick 6), e.g. `brew install imagemagick`.

After sourcing `zsh/.zsh-img2ascii` or `bash/.bash-img2ascii` (the welcome file also loads it in interactive shells unless the banner is disabled):

```bash
img2ascii "path/to/image.png"     # use the terminal width
img2ascii "path/to/image.png" 80  # choose a width
```

Without sourcing, run a wrapper with its shell (the files are not executable):

```bash
bash bash/.bash-img2ascii path/to/image.png 80
zsh zsh/.zsh-img2ascii path/to/image.png 80
```

- `width` is an integer from 1 to 500; the default is the terminal width, capped at 500.
- Output is at most 500 rows; very tall images are scaled down proportionally, so they come out narrower than `width`.
- Transparency is flattened onto black; animated images use their first frame.
- Invalid arguments or conversion failures print a message and return non-zero.
- These ImageMagick limits apply unless you set the variables yourself: `MAGICK_WIDTH_LIMIT=16384`, `MAGICK_HEIGHT_LIMIT=16384`, `MAGICK_TIME_LIMIT=60` (seconds), `MAGICK_MEMORY_LIMIT=64MiB`, `MAGICK_MAP_LIMIT=128MiB`, `MAGICK_DISK_LIMIT=256MiB`. They bound the work done on oversized images but are not a sandbox; only convert images you trust.

## Configuration

Set these before the relevant `source` lines in your startup file. Plain shell variables are enough; `export` is not required.

| Variable | Default | Effect | When it is read |
| --- | --- | --- | --- |
| `WELCOME_DISABLE` | unset | Any non-empty value skips the banner. | When the welcome file is sourced |
| `WELCOME_USER_NAME` | `$USER` | Name used in the greeting. | When the welcome file is sourced |
| `WELCOME_IMAGES_DIR` | `welcome-images/` next to the shell's welcome file | Directory for custom art and images. | When the welcome file is sourced |
| `DC_PROMPT_GIT` | on | `0` removes the Git segment and disables the idle branch check and focus refresh (the clock keeps ticking). Use in very large repositories. | Every prompt |
| `DC_PROMPT_CLOCK_REFRESH` | on | `0` stops Zsh's once-a-second clock redraw; the time then updates only when the prompt is refreshed. | Every prompt |
| `DC_PROMPT_AUTO_REFRESH` | on | `0` disables Zsh's idle branch check (the clock keeps ticking). | Every prompt |
| `DC_PROMPT_FOCUS_REFRESH` | on | `0` disables Zsh's focus-in refresh (independent of `DC_PROMPT_AUTO_REFRESH`). | Every prompt |

`DC_SHARED_DIR` overrides where the wrappers look for `shared/`; it is normally derived automatically and does not need to be set.

## Requirements

- Zsh and/or Bash. Shared code is written to avoid Bash 4-only features, since macOS ships Bash 3.2. Zsh's ticking clock and idle branch check use ZLE hooks and the `zsh/zselect` and `zsh/system` modules; if they cannot be loaded, the prompt still refreshes at each new prompt.
- Git 2.18 or newer for the Git segment ([`git status` options used](https://git-scm.com/docs/git-status/2.18.0)). Without Git the segment is omitted.
- Optional: Python 3 (`venv -f`, banner version, tests), Node.js (banner version), ImageMagick (image art and `img2ascii`), VS Code's `code` command (`mcode`).

## Troubleshooting

**Errors about missing `shared/...` files.** Source the wrappers from an intact checkout; don't copy them elsewhere. If you set `DC_SHARED_DIR`, make sure it points to the checkout's `shared/` directory.

**`+`/`*` do not update when switching back to the terminal.**

- The terminal must support focus reporting ([xterm mode 1004](https://invisible-island.net/xterm/ctlseqs/ctlseqs.html); [Ghostty, for example, implements it](https://github.com/ghostty-org/ghostty/blob/main/src/terminal/focus.zig)). If it doesn't, press Enter for a fresh prompt.
- In tmux, enable focus events with `set -g focus-events on` (see the [tmux wiki](https://github.com/tmux/tmux/wiki/Getting-Started)).
- Your own key bindings for the focus sequences take precedence. The prompt binds `^[[I` and `^[[O` only in the `emacs`, `viins` and `vicmd` keymaps, and only where they are unbound, and it turns focus reporting on only when the active keymap uses its widgets for both. To enable it in a custom keymap, bind `^[[I` to `_dc_prompt_focus_in` and `^[[O` to `_dc_prompt_focus_out` there.
- Check that `DC_PROMPT_GIT` and `DC_PROMPT_FOCUS_REFRESH` are not `0`.

**`^[[I` or `^[[O` appears in other programs.** A shell that was killed abruptly may have left focus reporting on. Run `printf '\e[?1004l'` or open a new terminal.

**The branch doesn't update in another pane.** Idle refresh only follows the same working tree; separate Git worktrees have independent branches by design. It also doesn't run while a command is executing, and it is Zsh-only (Bash updates at the next prompt).

**The prompt still behaves like the old timer version.** After updating from the original version that used `TRAPALRM`/`TMOUT`, open a new shell; re-sourcing does not remove timers already loaded in an existing session.

**The clock doesn't tick.** It only ticks in Zsh while idle at the main prompt (not during commands, continuation or `vared` prompts). Check that `DC_PROMPT_CLOCK_REFRESH` is not `0`. Bash shows the time the prompt was drawn.

**The prompt is slow in a huge repository.** Set `DC_PROMPT_GIT=0`.

## Development

- Tests: see [`tests/README.md`](tests/README.md). Run all of them from the repository root with `python3 -m unittest discover -s tests -v`.
- Engineering guidelines for contributors and coding agents: [`prompts/AGENTS.md`](prompts/AGENTS.md).
