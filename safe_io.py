"""
Shared guarded JSON file reader, used by both Forecasting_Agent and
fpa_data_layer (independent packages, no other shared module between them).

Guards against path traversal / symlink-following: the resolved path must
be a regular file, inside an allowed base directory, under a size cap.
Consolidated here after the same guard logic got written twice in two
places — the second time skylos caught it as a fresh duplicate.
"""
import json
from pathlib import Path

DEFAULT_MAX_BYTES = 1_000_000  # these are small driver/forecast JSON files, not user uploads


def read_json_file(path, base_dir, max_bytes=DEFAULT_MAX_BYTES):
    """base_dir is required (not optional) — callers must state what directory
    the path is expected to stay inside of."""
    resolved = Path(path).resolve()
    base_resolved = Path(base_dir).resolve()
    if resolved != base_resolved and base_resolved not in resolved.parents:
        raise ValueError(f"Path escapes allowed directory {base_dir}: {path}")
    if not resolved.is_file():
        raise FileNotFoundError(f"Expected a regular file, not found: {path}")
    if resolved.stat().st_size > max_bytes:
        raise ValueError(f"File too large ({resolved.stat().st_size} bytes): {path}")
    with open(resolved, "r") as f:  # pragma: no skylos -- path validated above: in-root, regular file, size-capped
        return json.load(f)
