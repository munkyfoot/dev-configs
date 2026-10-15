"""Interactive Zsh regression tests using real terminal sessions and Git repos."""
import errno
import fcntl
import os
import pty
import re
import select
import shlex
import shutil
import signal
import struct
import termios
import time
import unittest

from test_configs import ANSI, ROOT, ShellFixture


class Terminal:
    def __init__(self, directory, env):
        self.pid, self.fd = pty.fork()
        if self.pid == 0:
            try:
                os.chdir(directory)
                os.execve(shutil.which("zsh"), ["zsh", "-f", "-i"], env)
            finally:
                os._exit(127)
        fcntl.ioctl(self.fd, termios.TIOCSWINSZ, struct.pack("HHHH", 24, 160, 0, 0))
        self.output = ""

    def send(self, value):
        os.write(self.fd, value.encode())

    def read_for(self, seconds):
        end = time.monotonic() + seconds
        chunks = []
        while time.monotonic() < end:
            ready, _, _ = select.select([self.fd], [], [], max(0, end - time.monotonic()))
            if not ready:
                break
            try:
                data = os.read(self.fd, 65536)
            except OSError as error:
                if error.errno == errno.EIO:
                    break
                raise
            if not data:
                break
            chunks.append(data.decode("utf-8", errors="replace"))
        text = "".join(chunks)
        self.output += text
        return ANSI.sub("", text)

    def expect(self, text, timeout=4):
        received = ""
        end = time.monotonic() + timeout
        while time.monotonic() < end:
            received += self.read_for(min(0.1, max(0, end - time.monotonic())))
            if text in received:
                return received
        raise AssertionError(f"No {text!r} in terminal output: {received!r}")

    def close(self):
        if self.fd is None:
            return
        exited, _ = os.waitpid(self.pid, os.WNOHANG)
        if exited:
            os.close(self.fd)
            self.fd = None
            return
        # Kill only this disposable terminal's process group, never the user's shell.
        try:
            os.killpg(self.pid, signal.SIGHUP)
        except ProcessLookupError:
            pass
        end = time.monotonic() + 2
        while time.monotonic() < end:
            result, _ = os.waitpid(self.pid, os.WNOHANG)
            if result:
                break
            time.sleep(0.02)
        else:
            # Target our owned child directly if its shutdown is still stuck;
            # process-group signals can be restricted by the test sandbox.
            try:
                os.kill(self.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
            os.waitpid(self.pid, 0)
        os.close(self.fd)
        self.fd = None


@unittest.skipUnless(shutil.which("zsh"), "Zsh unavailable")
class PromptRefreshTests(ShellFixture):
    def start_terminal(self, *, directory=None, env=None, setup=""):
        terminal = Terminal(directory or self.work, {**self.env, **(env or {})})
        self.addCleanup(terminal.close)
        terminal.read_for(0.15)
        terminal.send(setup + '\nsource "$REPO_ROOT/zsh/.zsh-prompt"\n')
        return terminal

    def instrument_git(self):
        metadata = self.work / ".git" if (self.work / ".git").exists() else self.work
        bindir = metadata / "test-bin"
        bindir.mkdir()
        self.git_log = metadata / "git-calls"
        binary = bindir / "git"
        binary.write_text('#!/bin/sh\nprintf "%s\\n" "$*" >> "$GIT_CALL_LOG"\nexec '
                          + shlex.quote(shutil.which("git")) + ' "$@"\n')
        binary.chmod(0o755)
        self.env["GIT_CALL_LOG"] = str(self.git_log)
        self.env["PATH"] = str(bindir) + os.pathsep + self.env["PATH"]

    def expect_clock_ticks(self, terminal):
        output = terminal.read_for(2.3)
        times = set(re.findall(r"\b\d{1,2}:\d{2}:\d{2}\b", output))
        self.assertGreaterEqual(len(times), 2, f"Clock did not tick: {output!r}")
        return output

    def test_branch_switch_updates_other_pane_without_enter_preserving_cursor(self):
        self.init_repo()
        first = self.start_terminal()
        first.expect(" main ")
        second = self.start_terminal()
        second.expect(" main ")
        second.send("printf ac\x02")  # Cursor before c; refresh must leave it there.
        second.read_for(0.1)
        first.send("git switch -qc test\n")
        first.expect(" test ")
        second.expect(" test ")
        second.send("b\x05 > .git/buffer-result\n")
        second.expect(" test ")
        self.assertEqual((self.work / ".git" / "buffer-result").read_text(), "abc")

    def test_clock_ticks_without_git_calls_preserving_buffer_and_cursor(self):
        self.init_repo()
        self.instrument_git()
        terminal = self.start_terminal()
        terminal.expect(" main ")
        terminal.send("printf ac\x02")
        terminal.read_for(0.1)
        initial_calls = self.git_log.read_text()
        self.expect_clock_ticks(terminal)
        self.assertEqual(self.git_log.read_text(), initial_calls)
        terminal.send("b\x05 > .git/clock-buffer-result\n")
        terminal.expect(" main ")
        self.assertEqual((self.work / ".git" / "clock-buffer-result").read_text(), "abc")

    def test_clock_ticks_outside_git_even_after_focus_refresh(self):
        self.instrument_git()
        terminal = self.start_terminal()
        terminal.expect(" ❯ ")
        initial_calls = self.git_log.read_text()
        self.expect_clock_ticks(terminal)
        self.assertEqual(self.git_log.read_text(), initial_calls)
        terminal.send("\x1b[I")
        terminal.expect(" ❯ ")
        after_focus = self.git_log.read_text()
        self.expect_clock_ticks(terminal)
        self.assertEqual(self.git_log.read_text(), after_focus)

    def test_clock_can_be_disabled_without_disabling_branch_refresh(self):
        self.init_repo()
        terminal = self.start_terminal(env={"DC_PROMPT_CLOCK_REFRESH": "0"})
        terminal.expect(" main ")
        self.assertNotRegex(terminal.read_for(1.3), r"\d{1,2}:\d{2}:\d{2}")
        self.git("switch", "-qc", "test")
        terminal.expect(" test ")

    def test_disabling_clock_and_branch_refresh_starts_no_idle_handler(self):
        self.init_repo()
        terminal = self.start_terminal(env={"DC_PROMPT_CLOCK_REFRESH": "0",
                                            "DC_PROMPT_AUTO_REFRESH": "0"})
        terminal.expect(" main ")
        terminal.send('observe_idle() { zle -F -L > "$HOME/.git/idle-handlers"; }; '
                      'add-zle-hook-widget line-init observe_idle\n')
        terminal.expect(" main ")
        self.assertEqual((self.work / ".git" / "idle-handlers").read_text(), "")
        self.assertNotRegex(terminal.read_for(1.3), r"\d{1,2}:\d{2}:\d{2}")
        (self.work / "tracked").write_text("changed\n")
        terminal.send("\x1b[I")
        terminal.expect(" main* ")  # Focus refresh is independent too.

    def test_clock_preserves_previous_command_exit_status(self):
        self.init_repo()
        terminal = self.start_terminal()
        terminal.expect(" main ")
        terminal.send("false\n")
        terminal.expect(" main ")
        self.expect_clock_ticks(terminal)
        terminal.send('print -r -- "$?" > .git/clock-exit-status\n')
        terminal.expect(" main ")
        self.assertEqual((self.work / ".git" / "clock-exit-status").read_text().strip(), "1")

    def test_focus_refreshes_external_staged_and_unstaged_changes_without_idle_scans(self):
        self.init_repo()
        self.instrument_git()
        terminal = self.start_terminal()
        terminal.expect(" main ")
        terminal.send("printf ac\x02")
        terminal.read_for(0.1)

        def focus_and_expect(label):
            before = self.git_log.read_text()
            terminal.send("\x1b[O")  # Losing focus should do no work.
            terminal.read_for(1.1)
            self.assertEqual(self.git_log.read_text(), before)
            terminal.send("\x1b[I")
            terminal.expect(" " + label + " ")
            calls = self.git_log.read_text()[len(before):].splitlines()
            self.assertEqual(sum(" status " in call for call in calls), 1, calls)

        (self.work / "tracked").write_text("changed\n")
        focus_and_expect("main*")
        self.git("add", "tracked")
        focus_and_expect("main+")
        (self.work / "new").write_text("untracked\n")
        focus_and_expect("main+*")
        self.git("reset", "--hard", "-q", "HEAD")
        (self.work / "new").unlink()
        focus_and_expect("main")
        terminal.send("b\x05 > .git/focus-buffer-result\n")
        terminal.expect(" main ")
        self.assertEqual((self.work / ".git" / "focus-buffer-result").read_text(), "abc")

    def test_focus_refresh_is_independent_of_idle_branch_refresh(self):
        self.init_repo()
        terminal = self.start_terminal(env={"DC_PROMPT_AUTO_REFRESH": "0"})
        terminal.expect(" main ")
        self.git("switch", "-qc", "test")
        (self.work / "tracked").write_text("changed\n")
        terminal.send("\x1b[I")
        terminal.expect(" test* ")

    def test_focus_refresh_can_be_disabled(self):
        self.init_repo()
        self.instrument_git()
        terminal = self.start_terminal(env={"DC_PROMPT_FOCUS_REFRESH": "0"})
        terminal.expect(" main ")
        self.assertNotIn("\x1b[?1004h", terminal.output)
        (self.work / "tracked").write_text("changed\n")
        before = self.git_log.read_text()
        terminal.send("\x1b[O\x1b[I")
        self.assertNotIn(" main* ", terminal.read_for(0.2))
        self.assertEqual(self.git_log.read_text(), before)

    def test_disabling_git_disables_focus_reporting_and_git_calls(self):
        self.init_repo()
        self.instrument_git()
        terminal = self.start_terminal(env={"DC_PROMPT_GIT": "0"})
        terminal.read_for(0.4)
        self.assertNotIn("\x1b[?1004h", terminal.output)
        self.assertFalse(self.git_log.exists())
        self.expect_clock_ticks(terminal)
        terminal.send("\x1b[O\x1b[I")
        terminal.read_for(0.2)
        self.assertFalse(self.git_log.exists())

    def test_focus_refresh_works_in_vi_insert_and_command_modes(self):
        self.init_repo()
        terminal = self.start_terminal(setup="bindkey -v")
        terminal.expect(" main ")
        (self.work / "tracked").write_text("changed\n")
        terminal.send("\x1b[I")
        terminal.expect(" main* ")
        terminal.send("printf ac\x1b")  # vi command mode with cursor on c.
        terminal.read_for(0.5)
        self.git("add", "tracked")
        terminal.send("\x1b[O\x1b[I")
        terminal.expect(" main+ ")
        terminal.send("ib\x1b")
        terminal.read_for(0.5)
        terminal.send("A > .git/vi-result\n")
        terminal.expect(" main+ ")
        self.assertEqual((self.work / ".git" / "vi-result").read_text(), "abc")

    def test_existing_focus_bindings_survive_repeated_source(self):
        self.init_repo()
        self.instrument_git()
        setup = '''user_focus_in() { print in >> "$HOME/.git/focus-events"; }
user_focus_out() { print out >> "$HOME/.git/focus-events"; }
zle -N user_focus_in
zle -N user_focus_out
bindkey '^[[I' user_focus_in
bindkey '^[[O' user_focus_out
'''
        terminal = self.start_terminal(setup=setup)
        terminal.expect(" main ")
        terminal.send('source "$REPO_ROOT/zsh/.zsh-prompt"\n')
        terminal.expect(" main ")
        self.assertNotIn("\x1b[?1004h", terminal.output)
        before = self.git_log.read_text()
        terminal.send("\x1b[O\x1b[I")
        terminal.read_for(0.2)
        self.assertEqual((self.work / ".git" / "focus-events").read_text(), "out\nin\n")
        self.assertEqual(self.git_log.read_text(), before)

    def test_switching_to_keymap_with_custom_focus_binding_disables_reporting(self):
        self.init_repo()
        setup = '''bindkey -v
user_focus_out() { print out >> "$HOME/.git/focus-events"; }
zle -N user_focus_out
bindkey -M vicmd '^[[O' user_focus_out
'''
        terminal = self.start_terminal(setup=setup)
        terminal.expect(" main ")
        self.assertIn("\x1b[?1004h", terminal.output)
        start = len(terminal.output)
        terminal.send("\x1b")
        terminal.read_for(0.5)
        self.assertIn("\x1b[?1004l", terminal.output[start:])
        terminal.send("\x1b[O")
        terminal.read_for(0.1)
        self.assertEqual((self.work / ".git" / "focus-events").read_text(), "out\n")
        start = len(terminal.output)
        terminal.send("i")
        terminal.read_for(0.1)
        self.assertIn("\x1b[?1004h", terminal.output[start:])
        (self.work / "tracked").write_text("changed\n")
        terminal.send("\x1b[I")
        terminal.expect(" main* ")

    def test_reporting_stops_for_commands_variable_editors_and_shell_exit(self):
        self.init_repo()
        terminal = self.start_terminal()
        terminal.expect(" main ")
        self.assertIn("\x1b[?1004h", terminal.output)
        start = len(terminal.output)
        terminal.send("value=hello; vared -p 'EDIT> ' value\n")
        terminal.expect("EDIT> hello")
        output = terminal.output[start:]
        self.assertIn("\x1b[?1004l", output)
        self.assertNotIn("\x1b[?1004h", output)
        start = len(terminal.output)
        terminal.send("\n")
        terminal.expect(" main ")
        self.assertIn("\x1b[?1004h", terminal.output[start:])
        start = len(terminal.output)
        terminal.send("exit\n")
        terminal.read_for(0.3)
        self.assertIn("\x1b[?1004l", terminal.output[start:])
        self.assertNotIn("\x1b[?1004h", terminal.output[start:])

    def test_focus_repeated_source_reads_status_once_and_keeps_labels_inert(self):
        self.init_repo()
        branch = "evil$(>PROMPT_EXECUTED)"
        self.git("switch", "-qc", branch)
        self.instrument_git()
        terminal = self.start_terminal(setup="setopt promptsubst")
        terminal.expect(" " + branch + " ")
        terminal.send('source "$REPO_ROOT/zsh/.zsh-prompt"\n')
        terminal.expect(" " + branch + " ")
        (self.work / "tracked").write_text("changed\n")
        before = self.git_log.read_text()
        terminal.send("\x1b[I")
        terminal.expect(" " + branch + "* ")
        calls = self.git_log.read_text()[len(before):].splitlines()
        self.assertEqual(sum(" status " in call for call in calls), 1, calls)
        self.assertFalse((self.work / "PROMPT_EXECUTED").exists())

    def test_focus_reporting_stops_at_continuation_prompt(self):
        self.init_repo()
        terminal = self.start_terminal(setup="PS2='CONT> '")
        terminal.expect(" main ")
        start = len(terminal.output)
        terminal.send("printf '%s' \\\n")
        terminal.expect("CONT> ")
        self.assertIn("\x1b[?1004l", terminal.output[start:])
        self.assertNotIn("\x1b[?1004h", terminal.output[start:])
        start = len(terminal.output)
        terminal.send("ok > .git/continuation-result\n")
        terminal.expect(" main ")
        self.assertIn("\x1b[?1004h", terminal.output[start:])
        self.assertEqual((self.work / ".git" / "continuation-result").read_text(), "ok")

    def test_dumb_terminal_does_not_enable_focus_reporting(self):
        self.init_repo()
        terminal = self.start_terminal(env={"TERM": "dumb"})
        terminal.expect(" main ")
        self.assertNotIn("\x1b[?1004h", terminal.output)

    def test_focus_refresh_preserves_previous_command_exit_status(self):
        self.init_repo()
        terminal = self.start_terminal()
        terminal.expect(" main ")
        terminal.send("false\n")
        terminal.expect(" main ")
        (self.work / "tracked").write_text("changed\n")
        terminal.send("\x1b[I")
        terminal.expect(" main* ")
        terminal.send('print -r -- "$?" > .git/focus-exit-status\n')
        terminal.expect(" main* ")
        self.assertEqual((self.work / ".git" / "focus-exit-status").read_text().strip(), "1")

    def test_live_refresh_can_be_disabled(self):
        self.init_repo()
        terminal = self.start_terminal(env={"DC_PROMPT_AUTO_REFRESH": "0"})
        terminal.expect(" main ")
        self.git("switch", "-qc", "test")
        self.assertNotIn(" test ", self.expect_clock_ticks(terminal))
        terminal.send("\n")
        terminal.expect(" test ")

    def test_linked_worktree_and_subdirectory_use_their_own_head(self):
        self.init_repo()
        linked = self.work / ".git" / "linked-worktree"
        self.git("worktree", "add", "-qb", "linked", str(linked))
        nested = linked / "nested"
        nested.mkdir()
        terminal = self.start_terminal(directory=nested)
        terminal.expect(" linked ")
        self.git("switch", "-qc", "main-other")
        self.assertNotIn(" main-other ", terminal.read_for(1.2))
        self.git("-C", str(linked), "switch", "-qc", "linked-other")
        terminal.expect(" linked-other ")

    def test_background_refresh_keeps_branch_name_inert(self):
        self.init_repo()
        terminal = self.start_terminal(setup="setopt promptsubst")
        terminal.expect(" main ")
        branch = "evil$(>PROMPT_EXECUTED)"
        self.git("switch", "-qc", branch)
        terminal.expect(" " + branch + " ")
        self.expect_clock_ticks(terminal)
        self.assertFalse((self.work / "PROMPT_EXECUTED").exists())

    def test_repeated_source_preserves_widgets_and_closes_idle_handler_for_commands(self):
        self.init_repo()
        setup = '''function zle-line-init() { print user-init >> "$HOME/.git/user-hooks"; }
zle -N zle-line-init
function zle-line-finish() { print user-finish >> "$HOME/.git/user-hooks"; }
zle -N zle-line-finish
TRAPALRM() { :; }
TMOUT=123
'''
        terminal = self.start_terminal(setup=setup)
        terminal.expect(" main ")
        terminal.send('source "$REPO_ROOT/zsh/.zsh-prompt"\n')
        terminal.expect(" main ")
        terminal.send('function observe_handlers() { zle -F -L > "$HOME/.git/idle-handlers"; }; '
                      'add-zle-hook-widget line-init observe_handlers\n')
        terminal.expect(" main ")
        handlers = (self.work / ".git" / "idle-handlers").read_text().splitlines()
        self.assertEqual(len(handlers), 1, handlers)
        terminal.send('zle -F -L > "$HOME/.git/command-handlers"; '
                      'print -r -- "$TMOUT" > "$HOME/.git/timeout-setting"\n')
        terminal.expect(" main ")
        self.assertEqual((self.work / ".git" / "command-handlers").read_text(), "")
        self.assertEqual((self.work / ".git" / "timeout-setting").read_text().strip(), "123")
        hooks = (self.work / ".git" / "user-hooks").read_text()
        self.assertIn("user-init", hooks)
        self.assertIn("user-finish", hooks)

    def test_checkout_during_prompt_build_is_not_missed(self):
        self.init_repo()
        self.git("branch", "test")
        terminal = self.start_terminal()
        terminal.expect(" main ")
        terminal.send('functions[original_prompt_git]=$functions[prompt_git]; '
                      'prompt_git() { original_prompt_git; '
                      'if [[ ! -f "$HOME/.git/raced" ]]; then '
                      'git switch -q test; : > "$HOME/.git/raced"; fi; }\n')
        # The first render can still be main; the automatic check must catch up.
        terminal.expect(" test ")

    def test_ticker_exits_after_shell_exits(self):
        self.init_repo()
        terminal = self.start_terminal(setup="zmodload zsh/system")
        terminal.expect(" main ")
        terminal.send('function observe_worker() { print -r -- "$sysparams[procsubstpid]" '
                      '> "$HOME/.git/worker-pid"; }; '
                      'add-zle-hook-widget line-init observe_worker\n')
        terminal.expect(" main ")
        pid = int((self.work / ".git" / "worker-pid").read_text())
        self.assertGreater(pid, 0)
        terminal.send("exit\n")
        deadline = time.monotonic() + 2
        while time.monotonic() < deadline:
            terminal.read_for(0.05)
            try:
                os.kill(pid, 0)
            except ProcessLookupError:
                break
        else:
            self.fail("Ticker remained alive more than two seconds after shell exit")

    def test_variable_editor_does_not_install_a_prompt_ticker(self):
        self.init_repo()
        terminal = self.start_terminal()
        terminal.expect(" main ")
        terminal.send('function observe_context() { zle -F -L > "$HOME/.git/$CONTEXT-handlers"; }; '
                      'add-zle-hook-widget line-init observe_context\n')
        terminal.expect(" main ")
        terminal.send("value=hello; vared -p 'EDIT> ' value\n")
        terminal.expect("EDIT> hello")
        self.assertEqual((self.work / ".git" / "vared-handlers").read_text(), "")
        self.assertNotRegex(terminal.read_for(1.3), r"\d{1,2}:\d{2}:\d{2}")
        terminal.send("\n")
        terminal.expect(" main ")

    def test_command_cleanup_survives_an_early_returning_user_widget(self):
        self.init_repo()
        setup = 'function zle-line-finish() { return 1; }; zle -N zle-line-finish'
        terminal = self.start_terminal(setup=setup)
        terminal.expect(" main ")
        start = len(terminal.output)
        terminal.send('zle -F -L > "$HOME/.git/command-handlers"\n')
        terminal.expect(" main ")
        self.assertEqual((self.work / ".git" / "command-handlers").read_text(), "")
        self.assertIn("\x1b[?1004l", terminal.output[start:])

    def test_ticker_stops_even_when_another_plugin_inherits_its_pipe(self):
        self.init_repo()
        terminal = self.start_terminal()
        terminal.expect(" main ")
        # Simulate a short-lived async plugin that inherits open descriptors.
        terminal.send('function inherit_pipe() { '
                      'print -r -- "$sysparams[procsubstpid]" > "$HOME/.git/worker-pid"; '
                      '(zselect -t 200) &!; }; '
                      'add-zle-hook-widget line-init inherit_pipe\n')
        terminal.expect(" main ")
        pid = int((self.work / ".git" / "worker-pid").read_text())
        terminal.send('add-zle-hook-widget -d line-init inherit_pipe\n')
        terminal.expect(" main ")
        deadline = time.monotonic() + 0.8
        while time.monotonic() < deadline:
            try:
                os.kill(pid, 0)
            except ProcessLookupError:
                break
            terminal.read_for(0.05)
        else:
            self.fail("Old ticker stayed alive because another process inherited its pipe")


if __name__ == "__main__":
    unittest.main()
