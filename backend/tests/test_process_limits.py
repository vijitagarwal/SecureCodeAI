import os
import subprocess
import sys
import time

import pytest

from app.core.config import settings
from app.scanners.bandit import _execute
from app.scanners.base import ScannerError


# These commands are app-owned process fixtures, never uploaded source.
def test_actual_process_timeout_reaps_child_and_cleans_directory(tmp_path, monkeypatch):
    processes = []
    popen = subprocess.Popen

    def tracked(*args, **kwargs):
        process = popen(*args, **kwargs)
        processes.append(process)
        return process

    monkeypatch.setattr(subprocess, "Popen", tracked)
    started = time.monotonic()
    with pytest.raises(subprocess.TimeoutExpired):
        _execute([sys.executable, "-I", "-c", "import time; time.sleep(60)"], 0.2, tmp_path)
    assert time.monotonic() - started < 5
    assert processes[0].poll() is not None
    assert list(tmp_path.iterdir()) == []


def test_output_flood_is_bounded_and_does_not_spool_to_disk(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "max_scanner_output_bytes", 1024)
    with pytest.raises(ScannerError, match="output limit"):
        _execute([sys.executable, "-I", "-c", "import os\nwhile True: os.write(1, b'x' * 65536)"], 5, tmp_path)
    assert list(tmp_path.iterdir()) == []


def test_invalid_output_encoding_is_a_scanner_failure(tmp_path):
    with pytest.raises(ScannerError, match="UTF-8"):
        _execute([sys.executable, "-I", "-c", "import os; os.write(1, b'\\xff')"], 5, tmp_path)


def test_subprocess_receives_no_application_secrets(tmp_path, monkeypatch):
    monkeypatch.setenv("API_KEY", "fixture-secret-not-for-use")
    result = _execute([sys.executable, "-I", "-c", "import os; print(os.environ.get('API_KEY', 'absent'))"], 5, tmp_path)
    assert result.stdout.strip() == "absent"


@pytest.mark.skipif(os.name != "posix", reason="POSIX process-group termination; Windows direct-child only")
def test_descendant_cannot_hold_output_pipe_after_timeout(tmp_path):
    command = "import subprocess,sys,time; subprocess.Popen([sys.executable,'-c','import time; time.sleep(60)']); time.sleep(60)"
    started = time.monotonic()
    with pytest.raises(subprocess.TimeoutExpired):
        _execute([sys.executable, "-I", "-c", command], 0.5, tmp_path)
    assert time.monotonic() - started < 5
    assert list(tmp_path.iterdir()) == []
