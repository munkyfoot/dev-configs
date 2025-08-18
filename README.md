# Dev Configs

Personal development configurations for various tools and languages.

## Zsh

### Custom Prompt

#### `.zsh-prompt`

A clean, informative prompt showing:

- Current time
- `user@host` when SSH'd into remote machines
- Current directory (abbreviated)
- Git branch/status with `*` for dirty repos
- Active Python virtual environment
- Green caret prompt

Uses helper functions for Git and venv detection, hooks into Zsh's `precmd` for dynamic updates.

### Custom Welcome

#### `.zsh-welcome`

Personalized terminal greeting with:

- Time-of-day adapted greeting
- ASCII art that changes throughout the day
- Today's date with ordinal suffixes
- Environment snapshot (Node.js and Python versions)
- Session-aware display (shows once per session)

### Helpers

#### `.zsh-aliases`

Focused helpers for common tasks:

- `venv`: Activate local `./venv`; with `-f` flag, create if missing
- `mcd`: Create directory and cd into it
- `mcursor`: Ensure directory exists and open in Cursor

### Installation

#### Option 1: Copy & paste into your `.zshrc`

Open `~/.zshrc` and paste file contents in this order:

1. `.zsh-aliases` - Helper functions and aliases
2. `.zsh-welcome` - Welcome message
3. `.zsh-prompt` - Custom prompt configuration

#### Option 2: Source files directly

Add these lines to your `~/.zshrc`:

```bash
# Source custom configurations
source ~/path/to/dev-configs/.zsh-aliases
source ~/path/to/dev-configs/.zsh-welcome
source ~/path/to/dev-configs/.zsh-prompt
```

Replace `~/path/to/dev-configs/` with the actual path to your config files.

### Requirements

- Zsh shell
- Git (for prompt features)
- Python (for venv detection)

### Customization

Each file can be customized to your preferences:

- **`.zsh-prompt`**: Modify colors, symbols, and information displayed
- **`.zsh-welcome`**: Change ASCII art, greetings, or add more environment info
- **`.zsh-aliases`**: Add your own aliases and helper functions

### Troubleshooting

If the prompt doesn't update properly:

1. Ensure you're using Zsh (not Bash)
2. Check that Git is installed and accessible
3. Restart your terminal or run `source ~/.zshrc`
