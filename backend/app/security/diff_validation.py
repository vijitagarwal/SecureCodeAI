_HEADERS = ("diff --git ", "--- ", "+++ ", "rename from ", "rename to ", "copy from ", "copy to ")


def contains_unsafe_diff_path(diff_text: str) -> bool:
    """Accept simple relative review paths only. No patch is ever auto-applied."""
    seen_header = False
    for line in diff_text.splitlines():
        if not line.startswith(_HEADERS):
            continue
        seen_header = True
        if line.startswith("diff --git "):
            paths = line[len("diff --git "):].split()
            if len(paths) != 2:
                return True
        else:
            prefix = next(prefix for prefix in _HEADERS if line.startswith(prefix))
            paths = [line[len(prefix):].split("\t", 1)[0]]
        if any(not _safe_path(path) for path in paths):
            return True
    return bool(diff_text.strip()) and not seen_header


def _safe_path(path: str) -> bool:
    if path.startswith(("a/", "b/")):
        path = path[2:]
    # Reject ambiguous quoted/escaped headers rather than interpreting Git C escapes.
    if not path or any(ord(char) < 32 for char in path) or any(char in path for char in ('"', "'", ":", "\\")):
        return False
    if path.startswith("/"):
        return False
    return all(segment not in {"", ".", ".."} for segment in path.split("/"))
