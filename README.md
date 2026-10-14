# Dev Configs

Personal development configurations for various tools and languages.

## Zsh

### Custom Prompt

#### `.zsh-prompt`

A clean, informative prompt showing:

- Current time
- `user@host` when SSH'd into remote machines
- Current directory (abbreviated)
- Git branch/status with `+` for staged and `*` for unstaged/untracked changes
- Active Python virtual environment
- Green caret prompt

Uses helper functions for Git and venv detection, hooks into Zsh's `precmd` for dynamic updates. The full prompt (clock, Git status, venv) is rebuilt each time a new prompt is drawn. While you sit idle at a prompt inside a Git repository, a lightweight check also redraws it within about a second if the branch changes, e.g. after `git checkout` in another pane of the same working tree. In terminals that support focus reporting, the full prompt (including `+`/`*`) is also rebuilt when the terminal regains focus. See [Prompt Performance and Safety](#prompt-performance-and-safety).

### Custom Welcome

#### `.zsh-welcome`

Personalized terminal greeting with:

- Time-of-day adapted greeting
- ASCII art that changes throughout the day
- Optional custom ASCII art (`morning.txt`, `afternoon.txt`, `evening.txt`, or `custom.txt`) in `welcome-images` or `WELCOME_IMAGES_DIR`
- Optional disable switch via `WELCOME_DISABLE=1`
- Today's date with ordinal suffixes
- Environment snapshot (Node.js and Python versions)
- Session-aware display (shows once per session)

### Helpers

#### `.zsh-aliases`

Focused helpers for common tasks:

- `venv`: Activate local `./.venv` or `./venv`; with `-f` flag, create `./.venv` if missing
- `mcd`: Create directory and cd into it
- `mcode`: Ensure directory exists and open it in VS Code
- `dc_help`: Show helper usage

### Installation

Clone this repository and source the files from the checkout. The wrappers locate `shared/` relative to themselves, so keep the checkout intact (copying or pasting a single file into `~/.zshrc` will not work).

Add these lines to your `~/.zshrc`:

```bash
# Source custom configurations
source ~/path/to/dev-configs/zsh/.zsh-aliases
source ~/path/to/dev-configs/zsh/.zsh-welcome
source ~/path/to/dev-configs/zsh/.zsh-prompt
```

Replace `~/path/to/dev-configs/` with the actual path to your checkout.

## Bash

### Custom Prompt

#### `bash/.bash-prompt`

A clean, informative prompt showing:

- Current time
- `user@host` when SSH'd into remote machines
- Current directory (abbreviated)
- Git branch/status with `+` for staged and `*` for unstaged/untracked changes
- Active Python virtual environment
- Green caret prompt

Uses shared helper functions for Git and venv detection. The prompt builder runs first in `PROMPT_COMMAND` (scalar or array) and preserves `$?` for any hooks after it. See [Prompt Performance and Safety](#prompt-performance-and-safety).

### Custom Welcome

#### `bash/.bash-welcome`

Personalized terminal greeting with:

- Time-of-day adapted greeting
- ASCII art that changes throughout the day
- Optional custom ASCII art (`morning.txt`, `afternoon.txt`, `evening.txt`, or `custom.txt`) in `welcome-images` or `WELCOME_IMAGES_DIR`
- Optional disable switch via `WELCOME_DISABLE=1`
- Today's date with ordinal suffixes
- Environment snapshot (Node.js and Python versions)
- Session-aware display (shows once per session)

### Helpers

#### `bash/.bash-aliases`

Focused helpers for common tasks:

- `venv`: Activate local `./.venv` or `./venv`; with `-f` flag, create `./.venv` if missing
- `mcd`: Create directory and cd into it
- `mcode`: Ensure directory exists and open it in VS Code
- `dc_help`: Show helper usage

### Installation

Add these lines to your `~/.bashrc`:

```bash
# Source custom configurations
source ~/path/to/dev-configs/bash/.bash-aliases
source ~/path/to/dev-configs/bash/.bash-welcome
source ~/path/to/dev-configs/bash/.bash-prompt
```

Replace `~/path/to/dev-configs/` with the actual path to your checkout. As with Zsh, source the files from an intact checkout rather than copying them.

## Shared

Common logic for prompts, welcome banners, and helpers lives in `shared/` and is sourced by both shells.

### Prompt Performance and Safety

- Git status is read with `git --no-optional-locks status --no-ahead-behind --no-renames --untracked-files=normal`, so the prompt does not take index locks, count ahead/behind commits, or detect renames. Untracked files always set `*`, even if `status.showUntrackedFiles=no` is configured.
- In very large repositories, set `DC_PROMPT_GIT=0` to skip Git status entirely.
- Zsh idle branch refresh: while the line editor waits for input, a small helper sleeps in Zsh's [`zselect` builtin](https://zsh.sourceforge.io/Doc/Release/Zsh-Modules.html#The-zsh_002fzselect-Module) and wakes the prompt about once a second. Each wake-up only reads the repository's `HEAD` file with a shell builtin (no Git or other process is started); the prompt is rebuilt with full Git status only when `HEAD` changed. The helper runs only at the main command prompt and stops when a command runs or the shell exits; continuation prompts and variable editors are left alone. It does not use `TMOUT`/`TRAPALRM` and leaves your own settings and ZLE widgets in place.
  - Only branch/HEAD changes are detected while idle. Edits, staging or commits that do not move `HEAD` update the `+`/`*` markers at the next prompt or when the terminal regains focus (below), not continuously.
  - Separate Git worktrees have independent branches by design; a checkout in one worktree does not change another's prompt.
  - Set `DC_PROMPT_AUTO_REFRESH=0` to disable it (`DC_PROMPT_GIT=0` disables it too). The change takes effect at the next prompt.
  - Bash has no equivalent; its prompt refreshes only when a new prompt is drawn.
- Zsh focus refresh: at the main command prompt, the prompt turns on terminal focus reporting ([xterm mode 1004](https://invisible-island.net/xterm/ctlseqs/ctlseqs.html)) and rebuilds itself, including the `+`/`*` markers, each time the terminal regains focus. The command line and cursor are kept; losing focus does nothing. Reporting is turned off before each command runs and in continuation prompts or variable editors.
  - Your terminal must support focus reporting. [Ghostty implements these events](https://github.com/ghostty-org/ghostty/blob/main/src/terminal/focus.zig). Actual pane/window focus delivery in Ghostty and macOS Terminal has not been verified here; automated tests inject the events into isolated Zsh terminal sessions. In tmux, enable `set -g focus-events on` (see the [tmux wiki](https://github.com/tmux/tmux/wiki/Getting-Started)).
  - The focus sequences (`^[[I`, `^[[O`) are bound only in the `emacs`, `viins` and `vicmd` keymaps, and only where they are not already bound. Your own focus bindings take precedence: if the active keymap does not use this prompt's widgets for both sequences, reporting stays off for that keymap. To opt a custom keymap in, bind `^[[I` to `_dc_prompt_focus_in` and `^[[O` to `_dc_prompt_focus_out` in it.
  - Set `DC_PROMPT_FOCUS_REFRESH=0` to disable it (`DC_PROMPT_GIT=0` disables it too); this is independent of `DC_PROMPT_AUTO_REFRESH`. Bash is unchanged.
- After updating from the original timer-based Zsh prompt (`TRAPALRM`/`TMOUT`), open a new shell. Sourcing the new file in an existing shell does not remove timer hooks already loaded by the old version.
- Branch, tag, directory and virtualenv names are shown as plain text and never evaluated as prompt code, whether or not Bash `promptvars` or Zsh `PROMPT_SUBST` is enabled.
- Control characters are removed from Git and virtualenv labels in both shells, and from the Bash directory label (computed in place of `\W`). Zsh uses its native `%1~`, which already escapes control characters and prompt sequences in directory names.

### Helpers Notes

- `venv` sources `./.venv/bin/activate` (or `./venv/bin/activate`) only when you run it, so use it only in directories you trust. Without a venv and without a terminal on stdin it exits with a hint to run `venv -f` instead of waiting for input.
- `mcd DIR` / `mcode DIR` take exactly one directory; names with spaces or a leading `-` work. `mcode` checks for the `code` CLI before creating anything.

### Image to ASCII (`img2ascii`)

Custom welcome images and the standalone converter need [ImageMagick](https://imagemagick.org) (`magick`, or `convert` from ImageMagick 6):

```bash
brew install imagemagick
```

Usage, either by sourcing `zsh/.zsh-img2ascii` / `bash/.bash-img2ascii` and calling the function:

```bash
img2ascii path/to/image.png [width]
```

or by running a wrapper with its shell (the files are not executable):

```bash
bash bash/.bash-img2ascii path/to/image.png 80
zsh zsh/.zsh-img2ascii path/to/image.png 80
```

- `width` must be an integer from 1 to 500; it defaults to the terminal width, capped at 500.
- Output is at most 500 rows; very tall images are shrunk proportionally (and so come out narrower than `width`). Transparency is flattened onto black, and only the first frame of animated images is used.
- Default ImageMagick resource limits are applied unless you set them yourself: `MAGICK_WIDTH_LIMIT=16384`, `MAGICK_HEIGHT_LIMIT=16384`, `MAGICK_TIME_LIMIT=60` (seconds), `MAGICK_MEMORY_LIMIT=64MiB`, `MAGICK_MAP_LIMIT=128MiB`, `MAGICK_DISK_LIMIT=256MiB`. These bound work on oversized images but are not a sandbox: ImageMagick still parses the file, so only convert images you trust.
- Exits non-zero with a message on invalid arguments or conversion failure.

The welcome banner caches converted art in `welcome-images/.ascii-cache/`, keyed by image filename (including extension) and width. Cache entries are regenerated when the image is newer, and caching is skipped (the art is still shown) if the directory is not writable or is a symlink. Each shell's welcome file looks for a `welcome-images` directory next to itself (e.g. `zsh/welcome-images`) unless `WELCOME_IMAGES_DIR` is set.

## Testing

The test suite uses the Python 3.8+ standard library and the installed Bash/Zsh and Git executables. Real image tests also use ImageMagick 7 when available; they are skipped otherwise:

```bash
python3 -m unittest discover -s tests -v
```

## Prompt Guidelines

Agent guidance for this repo lives in `prompts/AGENTS.md`.

It defines general expectations for code quality, workflow, testing, documentation, and safety without prescribing a default application stack.

## Requirements

- Zsh shell (for zsh configs)
- Bash shell (for bash configs)
- [Git 2.18+](https://git-scm.com/docs/git-status/2.18.0) (for prompt features)
- Python 3 (for creating venvs with `venv -f` and running the tests)
- ImageMagick (optional, for image welcome art and `img2ascii`)

## Customization

Each file can be customized to your preferences:

- **`zsh/.zsh-prompt` / `bash/.bash-prompt`**: Modify colors, symbols, and information displayed
- **`zsh/.zsh-welcome` / `bash/.bash-welcome`**: Change ASCII art, greetings, or add more environment info
- **`zsh/.zsh-aliases` / `bash/.bash-aliases`**: Add your own aliases and helper functions

## Troubleshooting

If the prompt doesn't update properly:

1. Ensure you're using the shell that matches the config you sourced (Zsh or Bash)
2. Check that Git is installed and accessible
3. Restart your terminal or run `source ~/.zshrc` / `source ~/.bashrc`
