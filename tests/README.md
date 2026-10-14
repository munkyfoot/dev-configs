# Tests

Behavioral tests for the shell configuration, written with Python's standard-library `unittest`. No packages need to be installed.

## Running

From the repository root:

```bash
python3 -m unittest discover -s tests -v
```

`tests/` is not a package, so select modules or tests through discovery rather than dotted module names:

```bash
python3 -m unittest discover -s tests -p 'test_configs.py' -v         # shared logic, helpers, banner, img2ascii
python3 -m unittest discover -s tests -p 'test_prompt_refresh.py' -v  # interactive Zsh prompt refresh
python3 -m unittest discover -s tests -k focus -v                     # tests whose names match "focus"
```

## Dependencies and skips

| Needed | Used for | If missing |
| --- | --- | --- |
| Python 3.8+ | Running the suite | – |
| Git 2.28+ | Repository fixtures use [`git init -b`](https://git-scm.com/docs/git-init/2.28.0.html); prompt tests also use `git switch` | Tests that create repositories fail |
| Bash, Zsh | Running each shell's checks | Checks for the missing shell are skipped |
| ImageMagick 7 (`magick`) | Real image conversion tests | Those tests are skipped; other `img2ascii` tests use stubs |
| A POSIX pseudo-terminal (macOS or Linux) | `test_prompt_refresh.py` | – |

Install at least one of Bash or Zsh; use both to cover both sets of wrappers. Native Windows is not supported by this test harness.

## Isolation

- Shells start without your startup files (`bash --noprofile --norc`, `zsh -f`), with `HOME` set to a fresh temporary directory and system/global Git configuration disabled.
- Each test creates its repositories, images and stub commands (for example a logging `git` wrapper on `PATH`) inside that temporary directory, which is removed afterwards.
- Interactive prompt tests run `zsh -f -i` in pseudo-terminals they own and shut down only those sessions.

## What the focus tests cover

`test_prompt_refresh.py` writes the focus sequences (`ESC[I`, `ESC[O`) directly into a pseudo-terminal and checks the shell's response: when reporting is turned on and off, the redrawn prompt, preserved command line, and how often Git runs. It does not exercise a real terminal emulator, so whether a particular app or tmux actually delivers focus events has to be checked by hand.

## Manual smoke check

Use a disposable Git repository with one committed file and no pending changes. Load the Zsh prompt in both terminals (and enable `set -g focus-events on` if using tmux):

1. Open two panes or windows in the same Git working tree and leave one idle at its prompt, optionally with some text typed.
2. In the other, run `git switch -c smoke-test`. Within about a second the idle prompt should show `smoke-test` without pressing Enter, with the typed text intact.
3. Edit a tracked file from the active pane, then focus the idle pane. Its prompt should gain `*`; after `git add` and refocusing, `+`.
4. Restore the scratch file to its committed contents in both the index and working tree, then focus the idle pane again. Both markers should disappear. Discard the scratch repository when finished.
