import json
import os
import signal
import subprocess
import sys
import tempfile
import threading
import time
from pathlib import Path
from typing import Any

from app.core.config import settings
from app.db.models import FindingConfidence, FindingSeverity
from app.scanners.base import ScannerError, ScannerFinding, ScannerResult, SecurityScanner


class BanditScanner(SecurityScanner):
    _MAX_FILENAME_LENGTH = 255
    _MAX_TITLE_LENGTH = 500
    _MAX_SNIPPET_LENGTH = 10_000

    def __init__(self, timeout_seconds: int | None = None):
        self.timeout_seconds = timeout_seconds if timeout_seconds is not None else settings.scanner_timeout_seconds
        if self.timeout_seconds <= 0:
            raise ValueError("Bandit timeout must be positive.")

    def scan(self, target_path: str) -> ScannerResult:
        target_path = str(Path(target_path).resolve())
        command = [sys.executable, "-I", "-m", "bandit", "--ignore-nosec", "-f", "json", target_path]
        try:
            completed = _execute(command, self.timeout_seconds, Path(target_path).parent)
        except FileNotFoundError as error:
            raise ScannerError("Bandit is not available.") from error
        except subprocess.TimeoutExpired as error:
            raise ScannerError("Bandit scan timed out.", public_message="The scan timed out. Try a smaller file.") from error
        except OSError as error:
            raise ScannerError("Bandit could not be started.") from error

        if not completed.stdout.strip():
            raise ScannerError("Bandit returned no usable output.")
        try:
            payload = json.loads(completed.stdout)
        except json.JSONDecodeError as error:
            raise ScannerError("Bandit returned malformed JSON.") from error

        if not isinstance(payload, dict):
            raise ScannerError("Bandit returned an invalid JSON document.")
        if completed.returncode not in {0, 1}:
            raise ScannerError("Bandit exited unexpectedly.")
        errors = payload.get("errors", [])
        if not isinstance(errors, list):
            raise ScannerError("Bandit returned invalid errors.")
        if errors:
            raise ScannerError(
                "Bandit could not parse the source.",
                public_message="Python could not be fully analyzed. Check its syntax and source encoding.",
            )
        raw_results = payload.get("results")
        if not isinstance(raw_results, list):
            raise ScannerError("Bandit returned invalid finding data.")
        if len(raw_results) > settings.max_findings:
            raise ScannerError("Finding limit exceeded.", public_message="Too many findings. Split this file into smaller scans.")
        findings = [self._parse_finding(item) for item in raw_results]
        return ScannerResult(
            findings=findings,
            metadata={"exit_code": completed.returncode, "metrics": payload.get("metrics", {})},
        )

    @staticmethod
    def _parse_finding(item: dict[str, Any]) -> ScannerFinding:
        if not isinstance(item, dict):
            raise ScannerError("Bandit returned an invalid finding.")
        try:
            severity = FindingSeverity(str(item["issue_severity"]).upper())
            confidence = FindingConfidence(str(item["issue_confidence"]).upper())
            raw_file_path = item["filename"]
            rule_id = item["test_id"]
            title = item["issue_text"]
        except (KeyError, ValueError, TypeError) as error:
            raise ScannerError("Bandit returned an invalid finding.") from error
        if severity not in {FindingSeverity.LOW, FindingSeverity.MEDIUM, FindingSeverity.HIGH}:
            raise ScannerError("Bandit returned an invalid severity.")
        if not isinstance(raw_file_path, str) or not raw_file_path or "\x00" in raw_file_path:
            raise ScannerError("Bandit returned an invalid filename.")
        if not isinstance(rule_id, str) or not rule_id or len(rule_id) > 100:
            raise ScannerError("Bandit returned an invalid rule ID.")
        if not isinstance(title, str) or not title or len(title) > BanditScanner._MAX_TITLE_LENGTH:
            raise ScannerError("Bandit returned an invalid issue title.")

        file_path = _safe_basename(raw_file_path)
        if len(file_path) > BanditScanner._MAX_FILENAME_LENGTH:
            raise ScannerError("Bandit returned an invalid filename.")
        line_number = item.get("line_number")
        if line_number is not None and (
            isinstance(line_number, bool) or not isinstance(line_number, int) or line_number < 1
        ):
            raise ScannerError("Bandit returned an invalid line number.")
        code_snippet = item.get("code")
        if code_snippet is not None and (
            not isinstance(code_snippet, str) or len(code_snippet) > BanditScanner._MAX_SNIPPET_LENGTH
        ):
            raise ScannerError("Bandit returned an invalid code snippet.")

        raw_metadata = dict(item)
        raw_metadata["filename"] = file_path
        return ScannerFinding(
            tool="bandit",
            rule_id=rule_id,
            title=title,
            description=title,
            severity=severity,
            confidence=confidence,
            file_path=file_path,
            line_number=line_number,
            code_snippet=code_snippet,
            raw_metadata=raw_metadata,
        )


def _safe_basename(file_path: str) -> str:
    """Reduce scanner-controlled paths to a display-only filename."""
    basename = file_path.replace("\\", "/").rsplit("/", 1)[-1]
    if basename in {"", ".", ".."} or "\x00" in basename:
        raise ScannerError("Bandit returned an invalid filename.")
    return basename


def _execute(command: list[str], timeout: int, directory: Path) -> subprocess.CompletedProcess:
    """Drain a bounded pipe, terminate on overflow/deadline, and reap the process.

    No output spool can fill the disk between polling intervals. POSIX children
    share a new process group; Windows guarantees termination of the direct child.
    This is not a sandbox against a compromised scanner.
    """
    environment = {
        key: value for key, value in os.environ.items()
        if key.upper() in {"PATH", "SYSTEMROOT", "WINDIR", "TEMP", "TMP", "LANG", "LC_ALL"}
    }
    with tempfile.TemporaryDirectory(dir=directory) as sandbox:
        environment.update({key: sandbox for key in ("HOME", "USERPROFILE", "LOCALAPPDATA", "APPDATA")})
        with subprocess.Popen(
            command, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
            # Keep the process current directory in the approved upload area.
            # The temporary directory is configuration state only, not cwd;
            # this avoids Windows retaining a cwd handle during cleanup.
            shell=False, cwd=directory, env=environment, start_new_session=os.name == "posix",
        ) as process:
            output = bytearray()
            overflow = threading.Event()
            finished = threading.Event()
            failures = []

            def drain():
                try:
                    while chunk := process.stdout.read1(65536):
                        if len(output) + len(chunk) > settings.max_scanner_output_bytes:
                            overflow.set()
                            return
                        output.extend(chunk)
                except OSError:
                    failures.append(True)
                finally:
                    finished.set()

            reader = threading.Thread(target=drain, name="scanner-output", daemon=True)
            reader.start()
            try:
                deadline = time.monotonic() + timeout
                while process.poll() is None or not finished.is_set():
                    if overflow.is_set():
                        raise ScannerError("Scanner output limit exceeded.")
                    if time.monotonic() >= deadline:
                        raise subprocess.TimeoutExpired(command, timeout)
                    time.sleep(0.01)
                if overflow.is_set():
                    raise ScannerError("Scanner output limit exceeded.")
                if failures:
                    raise ScannerError("Scanner output could not be read.")
                try:
                    stdout = output.decode("utf-8", errors="strict")
                except UnicodeDecodeError as error:
                    raise ScannerError("Scanner output was not UTF-8.") from error
                return subprocess.CompletedProcess(command, process.returncode, stdout, "")
            finally:
                if os.name == "posix":
                    try:
                        os.killpg(process.pid, signal.SIGKILL)
                    except ProcessLookupError:
                        pass
                elif process.poll() is None:
                    process.kill()
                process.wait()
                process.stdout.close()
                reader.join(timeout=2)
                # On Windows a compromised descendant may keep a pipe handle
                # open. Closing our end lets the reader exit without retaining
                # the temporary sandbox.
                if reader.is_alive():
                    raise ScannerError("Scanner output did not close.")
