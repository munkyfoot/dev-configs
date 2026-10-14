"""Behavioral regression tests; isolated shells never load the user's dotfiles."""
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SHELLS = [name for name in ("bash", "zsh") if shutil.which(name)]
ANSI = re.compile(r"\x1b\[[0-?]*[ -/]*[@-~]")


class ConfigTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="dev-configs-test-")
        self.addCleanup(self.temp.cleanup)
        self.work = Path(self.temp.name).resolve()
        self.env = {
            "PATH": os.environ.get("PATH", os.defpath),
            "HOME": str(self.work), "TERM": "xterm-256color", "USER": "tester",
            "LC_ALL": "C", "BASH_SILENCE_DEPRECATION_WARNING": "1", "GIT_CONFIG_NOSYSTEM": "1",
            "GIT_CONFIG_GLOBAL": os.devnull,
            "GIT_AUTHOR_NAME": "Test", "GIT_AUTHOR_EMAIL": "test@example.invalid",
            "GIT_COMMITTER_NAME": "Test", "GIT_COMMITTER_EMAIL": "test@example.invalid",
            "REPO_ROOT": str(ROOT), "DC_SHARED_DIR": str(ROOT / "shared"),
        }

    def shell(self, name, script, *, interactive=False, env=None):
        args = [shutil.which(name)]
        args += ["--noprofile", "--norc"] if name == "bash" else ["-f"]
        if interactive:
            args += ["-i"]
            return subprocess.run(args, input=script + "\nexit\n", text=True,
                                  capture_output=True, cwd=self.work,
                                  env={**self.env, **(env or {})}, timeout=15)
        return subprocess.run(args + ["-c", script], text=True, capture_output=True,
                              cwd=self.work, env={**self.env, **(env or {})}, timeout=15)

    def both(self, script, expected=None, *, env=None):
        for name in SHELLS:
            with self.subTest(shell=name):
                result = self.shell(name, script, env=env)
                self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
                if expected is not None:
                    self.assertEqual(result.stdout.strip(), expected)

    def git(self, *args):
        return subprocess.check_output(["git", *args], cwd=self.work,
                                       env=self.env, text=True, stderr=subprocess.PIPE).strip()

    def init_repo(self):
        self.git("init", "-q", "-b", "main")
        (self.work / "tracked").write_text("original\n")
        self.git("add", "tracked")
        self.git("commit", "-qm", "initial")

    def git_label(self, expected):
        self.both('source "$DC_SHARED_DIR/prompt.sh"; prompt_git', expected)

    def stub(self, name, body):
        directory = self.work / "bin"
        directory.mkdir(exist_ok=True)
        target = directory / name
        target.write_text("#!/bin/sh\n" + body)
        target.chmod(0o755)
        self.env["PATH"] = str(directory) + os.pathsep + os.environ.get("PATH", os.defpath)

    def test_syntax(self):
        for name in SHELLS:
            for file in list((ROOT / "shared").glob("*.sh")) + list((ROOT / name).glob(".*")):
                with self.subTest(shell=name, file=file.name):
                    result = subprocess.run([shutil.which(name), "-n", str(file)], capture_output=True, text=True)
                    self.assertEqual(result.returncode, 0, result.stderr)

    def test_git_status_markers(self):
        self.init_repo()
        self.git_label("main")
        (self.work / "tracked").write_text("modified\n")
        self.git_label("main*")
        self.git("add", "tracked")
        self.git_label("main+")
        (self.work / "untracked").write_text("new\n")
        self.git_label("main+*")

    def test_git_untracked_config_does_not_hide_dirty(self):
        self.init_repo()
        self.git("config", "status.showUntrackedFiles", "no")
        (self.work / "new").write_text("new")
        self.git_label("main*")

    def test_git_detached_tag_and_hash(self):
        self.init_repo()
        self.git("tag", "v1.0")
        self.git("checkout", "-q", "--detach")
        self.git_label("v1.0")
        self.git("tag", "-d", "v1.0")
        self.git_label(self.git("rev-parse", "HEAD")[:7])

    def test_git_unborn(self):
        self.git("init", "-q", "-b", "main")
        self.git_label("main")

    def test_git_merge_conflict(self):
        self.init_repo()
        self.git("checkout", "-qb", "other")
        (self.work / "tracked").write_text("other\n")
        self.git("commit", "-qam", "other")
        self.git("checkout", "-q", "main")
        (self.work / "tracked").write_text("main\n")
        self.git("commit", "-qam", "main")
        result = subprocess.run(["git", "merge", "other"], cwd=self.work,
                                env=self.env, capture_output=True)
        self.assertNotEqual(result.returncode, 0)
        self.git_label("main+*")

    def test_git_ignored_files_are_clean(self):
        self.init_repo()
        (self.work / ".git" / "info" / "exclude").write_text("ignored\n")
        (self.work / "ignored").touch()
        self.git_label("main")

    def test_git_outside_repo(self):
        self.both('source "$DC_SHARED_DIR/prompt.sh"; output=$(prompt_git); test -z "$output"')

    def test_git_can_be_disabled_without_invoking_git(self):
        self.stub("git", 'printf x >> "$HOME/git-called"\n')
        self.both('source "$DC_SHARED_DIR/prompt.sh"; output=$(prompt_git); test -z "$output"',
                  env={"DC_PROMPT_GIT": "0"})
        self.assertFalse((self.work / "git-called").exists())

    def test_git_does_not_take_optional_locks(self):
        self.init_repo()
        index = self.work / ".git" / "index"
        # Make the stat cache stale without changing content; status normally refreshes it.
        os.utime(self.work / "tracked", (1_600_000_000, 1_600_000_000))
        before = index.read_bytes(), index.stat().st_mtime_ns
        self.git_label("main")
        self.assertEqual((index.read_bytes(), index.stat().st_mtime_ns), before)

    def test_prompt_untrusted_venv_does_not_execute(self):
        for name in SHELLS:
            for payload in ("$(>PROMPT_EXECUTED)", "`>PROMPT_EXECUTED`"):
                for subst in ([False, True] if name == "zsh" else [True]):
                    with self.subTest(shell=name, payload=payload, promptsubst=subst):
                        script = "setopt promptsubst\n" if name == "zsh" and subst else ""
                        script += f'source "$REPO_ROOT/{name}/.{name}-prompt"\n'
                        result = self.shell(name, script, interactive=True,
                                            env={"VIRTUAL_ENV": "/tmp/" + payload})
                        marker = self.work / "PROMPT_EXECUTED"
                        executed = marker.exists()
                        marker.unlink(missing_ok=True)
                        self.assertFalse(executed, result.stderr)
                        self.assertIn(payload, ANSI.sub("", result.stderr))

    def test_prompt_untrusted_branch_does_not_execute(self):
        self.init_repo()
        for name in SHELLS:
            for payload in ("evil$(>PROMPT_EXECUTED)", "evil`>PROMPT_EXECUTED`"):
                with self.subTest(shell=name, payload=payload):
                    self.git("checkout", "-q", "-B", payload)
                    script = "setopt promptsubst\n" if name == "zsh" else ""
                    script += f'source "$REPO_ROOT/{name}/.{name}-prompt"\n'
                    result = self.shell(name, script, interactive=True)
                    marker = self.work / "PROMPT_EXECUTED"
                    executed = marker.exists()
                    marker.unlink(missing_ok=True)
                    self.assertFalse(executed, result.stderr)
                    self.assertIn(payload, ANSI.sub("", result.stderr))

    def test_prompt_control_characters_and_zsh_percent_are_literal(self):
        for name in SHELLS:
            with self.subTest(shell=name):
                result = self.shell(name, f'source "$REPO_ROOT/{name}/.{name}-prompt"\n',
                                    interactive=True, env={"VIRTUAL_ENV": "/tmp/safe\x1b[2J%F{red}name"})
                self.assertNotIn("\x1b[2J", result.stderr)
                self.assertIn("%F{red}name", ANSI.sub("", result.stderr))

    def test_bash_prompt_preserves_previous_status_and_hooks(self):
        if "bash" not in SHELLS:
            self.skipTest("Bash unavailable")
        result = self.shell("bash", '''
PROMPT_COMMAND='printf "status=%s\\n" "$?"'
source "$REPO_ROOT/bash/.bash-prompt"
source "$REPO_ROOT/bash/.bash-prompt"
false
eval "$PROMPT_COMMAND"
''')
        self.assertEqual(result.stdout.strip(), "status=1", result.stderr)

    def test_bash_array_prompt_hook_is_preserved_once(self):
        if "bash" not in SHELLS:
            self.skipTest("Bash unavailable")
        result = self.shell("bash", '''
PROMPT_COMMAND=('printf one' 'printf two')
source "$REPO_ROOT/bash/.bash-prompt"
source "$REPO_ROOT/bash/.bash-prompt"
printf '%s\\n' "${PROMPT_COMMAND[@]}"
''')
        self.assertEqual(result.stdout.splitlines().count("__build_bash_prompt"), 1)
        self.assertIn("printf one", result.stdout)
        self.assertIn("printf two", result.stdout)

    def test_bash_relative_wrappers_ignore_cdpath(self):
        if "bash" not in SHELLS:
            self.skipTest("Bash unavailable")
        checkout = self.work / "checkout"
        shutil.copytree(ROOT / "bash", checkout / "bash")
        shutil.copytree(ROOT / "shared", checkout / "shared")
        (self.work / "other" / "bash").mkdir(parents=True)
        result = self.shell("bash", '''
unset DC_SHARED_DIR
cd "$HOME/checkout"
CDPATH="$HOME/other"
source bash/.bash-aliases
declare -F venv >/dev/null
''')
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_bash_promptvars_option_is_preserved(self):
        if "bash" not in SHELLS:
            self.skipTest("Bash unavailable")
        result = self.shell("bash", '''shopt -u promptvars
source "$REPO_ROOT/bash/.bash-prompt"
shopt -q promptvars && printf OPTION_CHANGED
''', interactive=True, env={"VIRTUAL_ENV": "/tmp/plain-env"})
        self.assertIn("(plain-env)", ANSI.sub("", result.stderr))
        self.assertNotIn("OPTION_CHANGED", result.stdout)

    def test_zsh_preserves_alarm_and_timeout(self):
        if "zsh" not in SHELLS:
            self.skipTest("Zsh unavailable")
        result = self.shell("zsh", '''
TRAPALRM() { print user-alarm; }
before=$functions[TRAPALRM]
TMOUT=123
source "$REPO_ROOT/zsh/.zsh-prompt"
source "$REPO_ROOT/zsh/.zsh-prompt"
[[ $TMOUT == 123 && $functions[TRAPALRM] == "$before" ]] || exit 1
count=0
for hook in $precmd_functions; do [[ $hook != build_prompt ]] || (( count += 1 )); done
[[ $count == 1 ]]
''')
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_venv_activation_success(self):
        target = self.work / ".venv" / "bin"
        target.mkdir(parents=True)
        (target / "activate").write_text('VIRTUAL_ENV="$PWD/.venv"\n')
        self.both('source "$DC_SHARED_DIR/aliases.sh"; venv >/dev/null && test "$VIRTUAL_ENV" = "$PWD/.venv"')

    def test_venv_activation_failure_is_preserved(self):
        target = self.work / ".venv" / "bin"
        target.mkdir(parents=True)
        (target / "activate").write_text("return 7\n")
        for name in SHELLS:
            with self.subTest(shell=name):
                result = self.shell(name, 'source "$DC_SHARED_DIR/aliases.sh"; venv')
                self.assertEqual(result.returncode, 7, result.stdout + result.stderr)
                self.assertNotIn("activated:", result.stdout)

    def test_venv_rejects_unknown_flags(self):
        for name in SHELLS:
            with self.subTest(shell=name):
                result = self.shell(name, 'source "$DC_SHARED_DIR/aliases.sh"; venv --invalid')
                self.assertNotEqual(result.returncode, 0)
                self.assertFalse((self.work / ".venv").exists())

    def test_venv_creation_failure_is_not_success(self):
        self.stub("python3", "exit 5\n")
        for name in SHELLS:
            result = self.shell(name, 'source "$DC_SHARED_DIR/aliases.sh"; venv -f')
            self.assertNotEqual(result.returncode, 0)
            self.assertNotIn("activated:", result.stdout)

    def test_venv_force_creates_and_activates(self):
        self.stub("python3", '''mkdir -p .venv/bin
printf 'VIRTUAL_ENV="$PWD/.venv"\n' > .venv/bin/activate
''')
        self.both('source "$DC_SHARED_DIR/aliases.sh"; venv -f >/dev/null && test "$VIRTUAL_ENV" = "$PWD/.venv"')

    def test_venv_noninteractive_does_not_prompt(self):
        for name in SHELLS:
            with self.subTest(shell=name):
                result = self.shell(name, 'source "$DC_SHARED_DIR/aliases.sh"; venv </dev/null')
                self.assertNotEqual(result.returncode, 0)
                self.assertNotIn("(y/N)", result.stdout + result.stderr)

    def test_mcd_paths(self):
        self.both('source "$DC_SHARED_DIR/aliases.sh"; mcd "-space dir" >/dev/null && test "${PWD##*/}" = "-space dir"')

    def test_mcd_ignores_cdpath(self):
        other = self.work / "other"
        (other / "new").mkdir(parents=True)
        self.both('source "$DC_SHARED_DIR/aliases.sh"; CDPATH="$PWD/other"; mcd new >/dev/null && test "$PWD" = "$HOME/new"')

    def test_mcode_path_not_option(self):
        self.stub("code", 'printf "%s\\n" "$@" > "$HOME/code-args"\n')
        self.both('source "$DC_SHARED_DIR/aliases.sh"; mcode "--extension-dir"')
        args = (self.work / "code-args").read_text().splitlines()
        protected = args[:1] == ["--"]
        if protected:
            args = args[1:]
        self.assertEqual(len(args), 1)
        self.assertTrue(protected or not args[0].startswith("-"), args)
        self.assertEqual((self.work / args[0]).resolve(), (self.work / "--extension-dir").resolve())

    def test_helpers_reject_extra_arguments(self):
        self.stub("code", "exit 0\n")
        for name in SHELLS:
            for helper in ("mcd", "mcode", "venv"):
                with self.subTest(shell=name, helper=helper):
                    result = self.shell(name, f'source "$DC_SHARED_DIR/aliases.sh"; {helper} one two')
                    self.assertNotEqual(result.returncode, 0)

    def test_welcome_noninteractive_and_disabled_are_quiet(self):
        for name in SHELLS:
            with self.subTest(shell=name):
                script = f'source "$REPO_ROOT/{name}/.{name}-welcome"'
                result = self.shell(name, script)
                self.assertEqual(result.stdout + result.stderr, "")
                result = self.shell(name, script, interactive=True, env={"WELCOME_DISABLE": "1"})
                self.assertNotIn("Good ", result.stdout + result.stderr)

    def test_welcome_only_once(self):
        for name in SHELLS:
            with self.subTest(shell=name):
                result = self.shell(name, f'source "$REPO_ROOT/{name}/.{name}-welcome"\n' * 2,
                                    interactive=True, env={"WELCOME_USER_NAME": "Tester"})
                self.assertEqual(result.stdout.count("Good "), 1, result.stdout + result.stderr)

    def test_ordinals(self):
        self.both('''source "$DC_SHARED_DIR/img2ascii.sh"; source "$DC_SHARED_DIR/welcome.sh"
for day in 01 02 03 04 11 12 13 21 22 23 31; do _dc_ordinal_suffix "$day"; printf ' '; done
''', "st nd rd th th th th st nd rd st")

    def test_welcome_handles_hour_08_as_decimal(self):
        self.stub("date", '''case "$1" in
  +%H|+%d) printf '08';;
  '+%A, %B') printf 'Wednesday, October';;
  '+%H %d %A %B') printf '08 08 Wednesday October';;
  *) exit 1;;
esac
''')
        for name in SHELLS:
            result = self.shell(name, 'source "$DC_SHARED_DIR/welcome.sh"; dc_welcome_banner "$HOME"')
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("Good morning", result.stdout)
            self.assertIn("October 8th", result.stdout)
            self.assertEqual(result.stderr, "")

    def test_welcome_ascii_directory_can_start_with_dash(self):
        (self.work / "-art").mkdir()
        (self.work / "-art" / "custom.txt").write_text("DASH_ART")
        for name in SHELLS:
            result = self.shell(name, 'source "$DC_SHARED_DIR/welcome.sh"; dc_welcome_banner "$HOME"',
                                env={"WELCOME_IMAGES_DIR": "-art"})
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("DASH_ART", result.stdout)
            self.assertEqual(result.stderr, "")

    def test_welcome_ascii_precedence(self):
        (self.work / "custom.txt").write_text("CUSTOM_ART\n")
        (self.work / "custom.png").touch()
        self.both('''source "$DC_SHARED_DIR/img2ascii.sh"; source "$DC_SHARED_DIR/welcome.sh"
img2ascii() { printf 'CONVERTED'; }
out=$(dc_welcome_banner "$HOME")
[[ "$out" == *CUSTOM_ART* && "$out" != *CONVERTED* ]]
''', env={"WELCOME_IMAGES_DIR": str(self.work)})

    def test_welcome_cache_hit_and_stale_image(self):
        (self.work / "custom.png").touch()
        self.both('''source "$DC_SHARED_DIR/img2ascii.sh"; source "$DC_SHARED_DIR/welcome.sh"
img2ascii() { printf x >> "$HOME/conversions"; printf 'CACHED_ART'; }
dc_welcome_banner "$HOME" >/dev/null
dc_welcome_banner "$HOME" >/dev/null
''', env={"WELCOME_IMAGES_DIR": str(self.work), "COLUMNS": "20"})
        self.assertEqual((self.work / "conversions").read_text(), "x")
        os.utime(self.work / "custom.png", (2_000_000_000, 2_000_000_000))
        self.both('''source "$DC_SHARED_DIR/img2ascii.sh"; source "$DC_SHARED_DIR/welcome.sh"
img2ascii() { printf x >> "$HOME/conversions"; printf 'NEW_ART'; }
dc_welcome_banner "$HOME" >/dev/null
''', env={"WELCOME_IMAGES_DIR": str(self.work), "COLUMNS": "20"})
        self.assertEqual((self.work / "conversions").read_text(), "xxx")

    def test_welcome_refuses_symlink_cache_directory(self):
        (self.work / "custom.png").touch()
        target = self.work / "outside"
        target.mkdir()
        (self.work / ".ascii-cache").symlink_to(target, target_is_directory=True)
        self.both('''source "$DC_SHARED_DIR/img2ascii.sh"; source "$DC_SHARED_DIR/welcome.sh"
img2ascii() { printf 'SAFE_ART'; }
dc_welcome_banner "$HOME" >/dev/null
''', env={"WELCOME_IMAGES_DIR": str(self.work), "COLUMNS": "20"})
        self.assertEqual(list(target.iterdir()), [])

    def test_welcome_cache_symlink_does_not_overwrite_target(self):
        (self.work / "custom.png").touch()
        script = '''source "$DC_SHARED_DIR/img2ascii.sh"; source "$DC_SHARED_DIR/welcome.sh"
img2ascii() { printf 'CACHED_ART'; }
dc_welcome_banner "$HOME" >/dev/null
'''
        env = {"WELCOME_IMAGES_DIR": str(self.work), "COLUMNS": "20"}
        self.shell(SHELLS[0], script, env=env)
        files = list((self.work / ".ascii-cache").glob("*.txt"))
        self.assertEqual(len(files), 1)
        victim = self.work / "victim"
        victim.write_text("KEEP_ME")
        os.utime(victim, (1_000_000_000, 1_000_000_000))
        files[0].unlink()
        files[0].symlink_to(victim)
        self.both(script, env=env)
        self.assertEqual(victim.read_text(), "KEEP_ME")

    def test_welcome_conversion_failure_does_not_cache_partial_output(self):
        (self.work / "custom.png").touch()
        script = '''source "$DC_SHARED_DIR/img2ascii.sh"; source "$DC_SHARED_DIR/welcome.sh"
img2ascii() { printf 'PARTIAL_OUTPUT'; return 1; }
dc_welcome_banner "$HOME"
'''
        for name in SHELLS:
            result = self.shell(name, script, env={"WELCOME_IMAGES_DIR": str(self.work), "COLUMNS": "20"})
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertNotIn("PARTIAL_OUTPUT", result.stdout)
        self.assertEqual(list((self.work / ".ascii-cache").glob("*.txt")), [])

    def test_welcome_unusable_cache_still_displays_art(self):
        (self.work / "custom.png").touch()
        (self.work / ".ascii-cache").write_text("not a directory")
        for name in SHELLS:
            result = self.shell(name, '''source "$DC_SHARED_DIR/img2ascii.sh"; source "$DC_SHARED_DIR/welcome.sh"
img2ascii() { printf 'UNCACHED_ART'; }
dc_welcome_banner "$HOME"
''', env={"WELCOME_IMAGES_DIR": str(self.work), "COLUMNS": "20"})
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("UNCACHED_ART", result.stdout)

    def test_welcome_cache_filename_preserves_extension(self):
        (self.work / "custom.png").touch()
        script = '''source "$DC_SHARED_DIR/img2ascii.sh"; source "$DC_SHARED_DIR/welcome.sh"
img2ascii() { printf '%s' "${1##*/}"; }
dc_welcome_banner "$HOME"
'''
        self.shell(SHELLS[0], script, env={"WELCOME_IMAGES_DIR": str(self.work), "COLUMNS": "20"})
        (self.work / "custom.png").unlink()
        (self.work / "custom.jpg").touch()
        os.utime(self.work / "custom.jpg", (1_000_000_000, 1_000_000_000))
        for name in SHELLS:
            result = self.shell(name, script, env={"WELCOME_IMAGES_DIR": str(self.work), "COLUMNS": "20"})
            self.assertIn("custom.jpg", result.stdout)

    def test_width_and_missing_image_validation(self):
        (self.work / "image.png").touch()
        for name in SHELLS:
            for args in ("", "missing.png", "image.png 0", "image.png -1", "image.png 501",
                         "image.png nope", "image.png 1+1", "image.png 999999999999999999999999999"):
                with self.subTest(shell=name, args=args):
                    result = self.shell(name, f'source "$DC_SHARED_DIR/img2ascii.sh"; img2ascii {args}')
                    self.assertNotEqual(result.returncode, 0, result.stdout)

    def test_conversion_failure_is_not_success(self):
        (self.work / "image.png").touch()
        self.stub("magick", 'case " $* " in *" identify "*) printf "2 2"; exit 0;; esac\nexit 9\n')
        for name in SHELLS:
            result = self.shell(name, 'source "$DC_SHARED_DIR/img2ascii.sh"; img2ascii image.png 2')
            self.assertNotEqual(result.returncode, 0, name + result.stdout)

    def test_width_validation_precedes_conversion_and_arithmetic(self):
        (self.work / "image.png").touch()
        self.stub("magick", 'printf x >> "$HOME/converter-called"\nprintf "2 2"\n')
        for name in SHELLS:
            for width in ("0", "501", "1+1", "a[$(>WIDTH_EXECUTED)]"):
                with self.subTest(shell=name, width=width):
                    result = self.shell(name, 'source "$DC_SHARED_DIR/img2ascii.sh"; img2ascii image.png "$TEST_WIDTH"',
                                        env={"TEST_WIDTH": width})
                    self.assertNotEqual(result.returncode, 0)
                    self.assertFalse((self.work / "converter-called").exists())
                    self.assertFalse((self.work / "WIDTH_EXECUTED").exists())

    def test_default_width_is_bounded(self):
        for name in SHELLS:
            result = self.shell(name, 'source "$DC_SHARED_DIR/img2ascii.sh"; _dc_img2ascii_default_width',
                                env={"COLUMNS": "999999999999999999999999"})
            self.assertEqual(result.returncode, 0, result.stderr)
            # Zsh may discard an overflowing COLUMNS value before the function runs.
            self.assertGreater(int(result.stdout), 0)
            self.assertLessEqual(int(result.stdout), 500)

    def test_legacy_converter_fallback_and_shell_options(self):
        (self.work / "image.png").touch()
        self.stub("convert", '''printf '%s\n' '# ImageMagick pixel enumeration: 2,1,0,255,srgb' \\
  '0,0: (255,0,0) #FF0000 srgb(255,0,0)' '1,0: (0,0,255) #0000FF srgb(0,0,255)'
''')
        (self.work / "bin" / "awk").symlink_to(shutil.which("awk"))
        self.env["PATH"] = str(self.work / "bin")
        for name in SHELLS:
            result = self.shell(name, '''source "$DC_SHARED_DIR/img2ascii.sh"
set +o pipefail
img2ascii image.png 2 || exit 1
[[ ! -o pipefail ]] || exit 2
[[ -z "${MAGICK_TIME_LIMIT:-}" ]] || exit 3
''')
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual([len(line) for line in ANSI.sub("", result.stdout).splitlines()], [2])
            self.assertIn("[38;2;255;0;0m", result.stdout)
            self.assertIn("[38;2;0;0;255m", result.stdout)

    @unittest.skipUnless(shutil.which("magick"), "ImageMagick 7 unavailable")
    def test_tall_image_is_bounded_before_resizing(self):
        subprocess.run([shutil.which("magick"), "-size", "1x100", "xc:red",
                        str(self.work / "tall.png")], check=True)
        for name in SHELLS:
            with self.subTest(shell=name):
                result = self.shell(name, 'source "$DC_SHARED_DIR/img2ascii.sh"; img2ascii tall.png 500')
                self.assertEqual(result.returncode, 0, result.stderr)
                lines = ANSI.sub("", result.stdout).splitlines()
                self.assertGreater(len(lines), 0)
                self.assertLessEqual(len(lines), 500)
                self.assertTrue(all(0 < len(line) <= 500 for line in lines))

    @unittest.skipUnless(shutil.which("magick"), "ImageMagick 7 unavailable")
    def test_real_image_formats_and_dash_path(self):
        magick = shutil.which("magick")
        for filename, color in (("rgb.png", "red"), ("gray.png", "gray50"),
                                ("alpha.png", "rgba(255,0,0,0.5)"), ("-dash.png", "blue")):
            subprocess.run([magick, "-size", "4x4", "xc:" + color, str(self.work / filename)], check=True)
        subprocess.run([magick, "-size", "4x4", "xc:red", "xc:blue", str(self.work / "animated.gif")], check=True)
        for name in SHELLS:
            for filename in ("rgb.png", "gray.png", "alpha.png", "-dash.png", "animated.gif"):
                with self.subTest(shell=name, filename=filename):
                    result = self.shell(name, f'source "$DC_SHARED_DIR/img2ascii.sh"; img2ascii "{filename}" 4')
                    self.assertEqual(result.returncode, 0, result.stderr)
                    lines = ANSI.sub("", result.stdout).splitlines()
                    self.assertEqual([len(line) for line in lines], [4, 4], result.stdout)
                    if filename == "rgb.png":
                        self.assertIn("[38;2;255;0;0m", result.stdout)
                    if filename == "-dash.png":
                        self.assertIn("[38;2;0;0;255m", result.stdout)


if __name__ == "__main__":
    unittest.main()
