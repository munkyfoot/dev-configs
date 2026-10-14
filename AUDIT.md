# Shell configuration audit

Audit date: 2026-10-14. Scope: all 17 originally tracked files, including shared shell functions, Bash/Zsh entry points, installation instructions, agent guidance, and the Terminal profile. The initial working tree was clean. Installed dotfiles and global configuration are outside the change scope.

## Findings

All 13 finding groups below have been addressed in the working tree. Codex established the findings and tests; Claude Opus 5.5 implemented the fixes and one correction round; Codex reviewed and independently verified the results.

Priorities reflect impact in this personal shell-configuration repository. P1 denotes code execution; P2 denotes material performance, safety, or correctness problems; P3 denotes maintenance and usability problems. A locally supplied argument is a different trust boundary from a Git branch received from another repository.

| Priority | Area | Confirmed original behavior | Remediation applied |
| --- | --- | --- | --- |
| P1 | [Prompt rendering](shared/prompt.sh) | Git branch and virtual-environment names were inserted into executable prompt text. A name containing `$(>PROMPT_EXECUTED)` created a marker file in Bash and in Zsh with `PROMPT_SUBST`. Backtick payloads were also reproduced. | Keep label data separate from prompt code; strip control characters and escape Zsh prompt sequences. |
| P1 | [Image width arithmetic](shared/img2ascii.sh) | Bash evaluated an unchecked width as arithmetic. Supplying `a[$(>WIDTH_EXECUTED)]` created a marker file. | Validate and bound decimal input before arithmetic or converter invocation. |
| P2 | [Idle prompt work](zsh/.zsh-prompt) | Zsh ran Git status every second, including when no command was entered; it also replaced `TRAPALRM` and `TMOUT`. After initialization, an isolated interactive session made three Git calls in 3.2 seconds idle. | Refresh full status at normal prompts and on terminal focus; use cheap HEAD-only checks for idle branch updates and preserve user timer settings. |
| P2 | [Git status overhead and correctness](shared/prompt.sh) | Prompt status refreshed the Git index on disk. It also performed unnecessary ahead/behind and rename work and inherited `status.showUntrackedFiles=no`, concealing the documented dirty marker. | Disable optional locks and unused calculations; request normal untracked-file reporting. |
| P2 | [Cache writes](shared/welcome.sh) | A symlinked cache directory or stale cache file could redirect writes outside the intended cache. Writes were non-atomic. | Reject symlink cache locations, use private temporary files and atomic replacement, and allow display when caching fails. |
| P2 | [Cache freshness](shared/welcome.sh) | Cache names discarded the image extension, so replacing `custom.png` with an older `custom.jpg` reused the wrong art. Zsh's local `path` variable hid `PATH`, breaking the `stat` helper and stale-image detection. The BSD/GNU `stat` fallback also relied on ambiguous output. | Keep the full filename in the key and use native file timestamp comparisons. |
| P2 | [Image conversion](shared/img2ascii.sh) | Conversion failures were masked by the final successful `awk` process; animated images returned multiple dimension records; output dimensions were unbounded; grayscale/alpha handling was unreliable. | Check converter failures, select one frame, bound dimensions, normalize color, and share one conversion pipeline. |
| P2 | [Virtual-environment activation](shared/aliases.sh) | A script returning status 7 produced a success message and status 0. Relative `source` could also consult Bash's source search path. | Explicitly source the local activation path and propagate its failure. |
| P2 | [Prompt hook integration](bash/.bash-prompt) | Bash's prompt builder changed `$?` before an existing `PROMPT_COMMAND` hook could inspect it. | Preserve the incoming exit status; retain scalar/array hook contents and idempotent sourcing. |
| P2 | [Directory helpers](shared/aliases.sh) | Leading-dash names were treated as options. `mcd` could enter another directory through `CDPATH`; extra arguments were silently ignored. | Validate arguments and use unambiguous local paths and option terminators. |
| P3 | [Shell startup and helpers](shared/welcome.sh) | Welcome time arithmetic could interpret hours `08`/`09` as octal in Bash. Missing venvs prompted even without an interactive input stream. | Use decimal time conversion and actionable noninteractive errors. |
| P3 | [Installation](README.md) | The suggested copy-and-paste installation could not resolve the wrappers' shared-file dependencies. Relative Bash wrapper resolution was also affected by `CDPATH`. | Document sourcing an intact checkout and make wrapper path discovery independent of `CDPATH`. |
| P3 | [Maintainability and verification](tests/test_configs.py) | Image conversion duplicated a substantial AWK pipeline; prompt basename lookups spawned avoidable processes; no regression tests existed. | Share the pipeline, use shell parameter expansion, and add isolated behavior tests. |

## Initial audit verification

- **47 regression tests passed** with `python3 -m unittest discover -s tests -v` (3.373 seconds in the final run). Cases run against both available shells, including actual interactive prompt rendering, malicious branch/venv labels, arithmetic payloads, Git state changes and index preservation, hook integration, venv activation, directory handling, cache freshness/symlinks, and image conversion failures.
- **Syntax checks passed** for every shared script under both Bash and Zsh and each shell's wrappers under its own interpreter. `git diff --check` also passed.
- **Local versions:** macOS, Bash 3.2.57, Zsh 5.9, Python 3.9.6, ImageMagick 7.1.2-33.
- **Real image checks passed** for RGB, grayscale, alpha, animated GIF, leading-dash filenames, and tall images. Both standalone wrappers produced the expected output. Additional literal `*`, bracket, and colon filename smoke checks succeeded with the installed ImageMagick.
- **Idle measurement:** after the first custom prompt initialized, an instrumented `git` command recorded **3 calls before / 0 calls after** during 3.2 idle seconds in isolated Zsh PTYs. This measures eliminated invocations, not a general CPU or latency benchmark.
- **Resource settings:** ImageMagick's local resource listing confirmed the memory/map/disk and width/height/time environment limits are recognized. Tests also verify conversion does not change the parent shell's `pipefail` setting or leak resource variables.
- **Not run:** Linux, Bash 5, real ImageMagick 6, or ShellCheck (not installed). The legacy `convert` selection is covered with a deterministic stub; Bash array hook registration is tested, but execution of multiple array hooks requires a newer Bash than the local 3.2.

The baseline tests reproduced the security issues and other failures before fixes. Tests and exploit markers use disposable directories and clean shells; installed dotfiles are not loaded. The Terminal profile passes `plutil` parsing. Git's status options and the documented 2.18 minimum were checked against the [Git 2.18 status documentation](https://git-scm.com/docs/git-status/2.18.0).

## Follow-up: restore branch updates across terminal panes

The initial removal of idle refresh also removed useful behavior. The Zsh prompt now checks the small `HEAD` file about once per second while the main command line is active. It performs a full prompt/Git refresh only when that content changes, so switching branches in one pane updates other idle panes in the same working tree without a click or newline. Paths are resolved through Git to support nested directories and linked worktrees.

A single sleeping Zsh helper uses native `zselect` and [ZLE file-descriptor callbacks](https://zsh.sourceforge.io/Doc/Release/Zsh-Line-Editor.html), rather than replacing `TMOUT` or alarm traps. Explicit cleanup stops the helper on command execution and shell exit, even when another plugin inherited its pipe. Continuation prompts and variable editors do not start it. `DC_PROMPT_AUTO_REFRESH=0` disables this behavior.

**58 tests passed** in the final run (17.011 seconds), including 11 new PTY tests. These verify automatic updates between two terminal sessions, preserved text and cursor position, no idle Git calls for unchanged repositories, startup races, independent worktrees, inert malicious branch names, opt-out, existing user widgets, and helper cleanup with inherited descriptors. `git diff --check` passed. Claude Opus 5.5 implemented the first pass; Codex added and independently tested lifecycle safeguards.

The lightweight check detects branch/HEAD changes only. The subsequent focus refresh below adds a trigger for external edits or staging on the same branch. Bash retains its existing command-boundary behavior. These checks were run on macOS with Zsh 5.9; Linux remains unverified.

## Follow-up: refresh dirty markers on terminal focus

Zsh now requests [terminal focus events](https://invisible-island.net/xterm/ctlseqs/ctlseqs.html) while editing the main command line. Focus-in rebuilds the prompt once, updating staged `+` and unstaged/untracked `*` markers; focus-out does no Git work. The HEAD-only idle check remains unchanged. Reporting is disabled before commands, continuation prompts, variable editors, and shell exit, and custom focus key bindings take precedence. `DC_PROMPT_FOCUS_REFRESH=0` disables this independently of the branch watcher; `DC_PROMPT_GIT=0` disables both.

Claude Opus 5.5 implemented the prompt and initial documentation changes. Codex added the regression tests, reviewed the implementation, and added an inactive-handler guard and cleanup when a repository disappears. Tests use disposable Git repositories and isolated Zsh PTYs, including injected focus sequences; they do not load installed dotfiles.

**70 tests passed** with `python3 -m unittest discover -s tests -v` (44.506 seconds), including 12 new focus-related tests. They verify external edits/staging/untracked files and returning to a clean tree, exactly one status read per focus-in, no focus-out or unchanged-idle Git calls, preserved text/cursor/exit status, vi modes, existing bindings and keymap switches, opt-outs, inert branch labels, repeated sourcing, and reporting cleanup for commands, continuation prompts, variable editors, and exit. Syntax checks and `git diff --check` passed. A sandbox-sensitive process-group kill in test teardown was changed to target the owned child directly if graceful shutdown stalls.

Actual pane/window focus delivery in Ghostty and macOS Terminal remains unverified. Ghostty's [focus event encoder](https://github.com/ghostty-org/ghostty/blob/main/src/terminal/focus.zig) implements the required protocol, but UI automation disallowed access to Ghostty, preventing a real click test. A terminal that does not emit the events retains normal prompt and automatic HEAD refresh. No terminal application or installed shell configuration was changed.

## Boundaries and opportunities

- Local shell configuration and virtual-environment activation scripts are executable code. Keep the checkout, configured shared directory, and activation scripts trusted. The `venv` helper intentionally sources the requested local environment.
- Welcome artwork is trusted local content. Text art may intentionally contain terminal escapes. ImageMagick resource limits and input validation do not turn an image decoder into a security sandbox; keep ImageMagick maintained and avoid untrusted images.
- Cache safety assumes the configured artwork directory and its parent directories are controlled by the user. Shell-level symlink checks do not protect against an adversary concurrently replacing trusted parent directories.
- Large working trees can still make synchronous Git status expensive. `DC_PROMPT_GIT=0` disables Git prompt details. Git status remains synchronous; the idle helper only schedules lightweight HEAD checks.
- Cross-platform CI is the main remaining verification opportunity: run the suite on Linux and newer Bash, and include a real ImageMagick 6 job if that fallback remains important. No hosting or CI service configuration was changed.
- Open a new Zsh session after updating. A session that already loaded the old timer retains its old hooks until restarted; the new configuration intentionally leaves existing user timer/trap state alone.
- The Terminal profile contains appearance/window settings and no startup command. A scan of tracked files found no common private-key, AWS access-key, or GitHub-token signatures; this is not an exhaustive secret or history audit.
