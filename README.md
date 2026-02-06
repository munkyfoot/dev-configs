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

Uses helper functions for Git and venv detection, hooks into Zsh's `precmd` for dynamic updates.

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

#### Option 1: Copy & paste into your `.zshrc`

Open `~/.zshrc` and paste file contents in this order:

1. `zsh/.zsh-aliases` - Helper functions and aliases
2. `zsh/.zsh-welcome` - Welcome message
3. `zsh/.zsh-prompt` - Custom prompt configuration

#### Option 2: Source files directly

Add these lines to your `~/.zshrc`:

```bash
# Source custom configurations
source ~/path/to/dev-configs/zsh/.zsh-aliases
source ~/path/to/dev-configs/zsh/.zsh-welcome
source ~/path/to/dev-configs/zsh/.zsh-prompt
```

Replace `~/path/to/dev-configs/` with the actual path to your config files.

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

Uses shared helper functions for Git and venv detection.

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

Replace `~/path/to/dev-configs/` with the actual path to your config files.

## Shared

Common logic for prompts, welcome banners, and helpers lives in `shared/` and is sourced by both shells.

## Requirements

- Zsh shell (for zsh configs)
- Bash shell (for bash configs)
- Git (for prompt features)
- Python (for venv detection)

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
