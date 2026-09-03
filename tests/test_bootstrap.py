"""The one-line start: both bootstrap scripts, driven with shimmed installers."""

import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SH = shutil.which("sh")
PWSH = shutil.which("pwsh") or shutil.which("powershell")


def _shim_bin(directory: Path, log: Path, windows: bool) -> Path:
    """Fake uv and npm that record their arguments instead of installing anything."""
    shims = directory / "bin"
    shims.mkdir()
    for tool in ("uv", "npm"):
        if windows:
            (shims / f"{tool}.cmd").write_text(
                f'@echo {tool} %* >> "{log}"\r\n', encoding="utf-8"
            )
        else:
            script = shims / tool
            script.write_text(
                f'#!/bin/sh\nprintf \'%s\\n\' "{tool} $*" >> "{log}"\n', encoding="utf-8"
            )
            script.chmod(0o755)
    return shims


class BootstrapScriptTests(unittest.TestCase):
    def _environment(self, shims: Path, target: Path, windows: bool) -> dict[str, str]:
        environment = {
            key: value for key, value in os.environ.items() if key != "ORS_API_KEY"
        }
        separator = ";" if windows else ":"
        environment["PATH"] = str(shims) + separator + environment.get("PATH", "")
        environment["LOCATION3_REPO"] = str(ROOT)
        environment["LOCATION3_DIR"] = str(target)
        environment["LOCATION3_LAUNCH"] = "0"
        # The clone source is this working tree; on a machine where it is owned by
        # another account git refuses it, so the test alone marks it safe for git.
        environment["GIT_CONFIG_COUNT"] = "1"
        environment["GIT_CONFIG_KEY_0"] = "safe.directory"
        environment["GIT_CONFIG_VALUE_0"] = "*"
        return environment

    def _assert_bootstrapped(self, output: str, log: Path, target: Path) -> None:
        self.assertIn("uv sync", log.read_text(encoding="utf-8"))
        self.assertIn("npm install", log.read_text(encoding="utf-8"))
        self.assertTrue((target / ".git").exists(), "the repository was cloned")
        self.assertTrue((target / "skills/location-research/SKILL.md").exists())
        self.assertIn("ORS_API_KEY  not set", output)
        self.assertIn("labelled distance boundary", output)
        self.assertIn("Not launching", output)
        self.assertIn("location-research skill", output)

    @unittest.skipUnless(SH, "no POSIX shell available")
    def test_posix_script_clones_installs_reports_and_stops_before_launch(self):
        with tempfile.TemporaryDirectory() as directory:
            work = Path(directory)
            log = work / "calls.log"
            shims = _shim_bin(work, log, windows=False)
            target = work / "clone"
            completed = subprocess.run(
                [SH, str(ROOT / "scripts/bootstrap.sh"), "codex"],
                cwd=work, env=self._environment(shims, target, windows=False),
                capture_output=True, text=True, timeout=120,
            )
            self.assertEqual(completed.returncode, 0, completed.stdout + completed.stderr)
            self.assertIn("agent      codex", completed.stdout)
            self._assert_bootstrapped(completed.stdout, log, target)

    @unittest.skipUnless(SH, "no POSIX shell available")
    def test_posix_script_refuses_an_unknown_agent_before_touching_anything(self):
        with tempfile.TemporaryDirectory() as directory:
            work = Path(directory)
            completed = subprocess.run(
                [SH, str(ROOT / "scripts/bootstrap.sh"), "gemini"],
                cwd=work, env={**os.environ, "LOCATION3_DIR": str(work / "clone")},
                capture_output=True, text=True, timeout=60,
            )
            self.assertNotEqual(completed.returncode, 0)
            self.assertIn("unknown agent", completed.stderr)
            self.assertFalse((work / "clone").exists())

    @unittest.skipUnless(PWSH and os.name == "nt", "PowerShell smoke test runs on Windows")
    def test_powershell_script_clones_installs_reports_and_stops_before_launch(self):
        with tempfile.TemporaryDirectory() as directory:
            work = Path(directory)
            log = work / "calls.log"
            shims = _shim_bin(work, log, windows=True)
            target = work / "clone"
            environment = self._environment(shims, target, windows=True)
            environment["LOCATION3_AGENT"] = "claude"
            completed = subprocess.run(
                [PWSH, "-NoProfile", "-NonInteractive", "-File", str(ROOT / "scripts/bootstrap.ps1")],
                cwd=work, env=environment, capture_output=True, text=True, timeout=120,
            )
            self.assertEqual(completed.returncode, 0, completed.stdout + completed.stderr)
            self.assertIn("agent      claude", completed.stdout)
            self._assert_bootstrapped(completed.stdout, log, target)

    def test_scripts_never_print_or_store_the_routing_key(self):
        for name in ("bootstrap.sh", "bootstrap.ps1"):
            text = (ROOT / "scripts" / name).read_text(encoding="utf-8")
            with self.subTest(script=name):
                # The key may be tested for presence, never echoed or written.
                for line in text.splitlines():
                    if "ORS_API_KEY" in line and ("echo" in line or "Write-Host" in line or "say " in line):
                        self.assertNotIn("$ORS_API_KEY", line)
                        self.assertNotIn("$env:ORS_API_KEY", line)
                        self.assertNotIn("${ORS_API_KEY", line)
