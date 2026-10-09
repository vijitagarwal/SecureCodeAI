from __future__ import annotations

import re


_DRIVE_PATH = re.compile(r"^[A-Za-z]:[\\/]")
_UNC_PATH = re.compile(r"^[\\/]{2}[^\\/]+[\\/][^\\/]+")
_DIFF_HEADER_PREFIXES = ("diff --git ", "--- ", "+++ ", "rename from ", "rename to ", "copy from ", "copy to ")


def contains_unsafe_diff_path(diff_text: str) -> bool:
    for line in diff_text.splitlines():
        candidate = line.strip()
        if not candidate:
            continue
        if candidate.startswith(_DIFF_HEADER_PREFIXES):
            paths = _extract_paths(candidate)
            if any(not _is_safe_diff_path(path) for path in paths):
                return True
    return False


def _extract_paths(line: str) -> tuple[str, ...]:
    if line.startswith("diff --git "):
        parts = line.split()
        if len(parts) >= 4:
            left = parts[2]
            right = parts[3]
            if left.startswith("a/"):
                left = left[2:]
            if right.startswith("b/"):
                right = right[2:]
            return left, right
        return ()
    for prefix in ("--- ", "+++ ", "rename from ", "rename to ", "copy from ", "copy to "):
        if line.startswith(prefix):
            return (line[len(prefix) :].strip().strip('"'),)
    return ()


def _is_safe_diff_path(path: str) -> bool:
    if not path or "\x00" in path:
        return False
    if path.startswith(("/", "\\")) or path.startswith("\\\\"):
        return False
    if _DRIVE_PATH.match(path) or _UNC_PATH.match(path):
        return False
    normalized = path.replace("\\", "/")
    segments = [segment for segment in normalized.split("/") if segment]
    if any(segment == ".." for segment in segments):
        return False
    return True
