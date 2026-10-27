import json
import subprocess
from pathlib import Path


def ffprobe(path: Path) -> dict:
    proc = subprocess.run(
        ["ffprobe", "-v", "error", "-print_format", "json", "-show_format", "-show_streams", str(path)],
        capture_output=True, text=True,
    )
    if proc.returncode != 0:
        raise RuntimeError(f"ffprobe: {proc.stderr.strip()}")
    return json.loads(proc.stdout)


def probe_duration(path: Path) -> float:
    return float(ffprobe(path)["format"]["duration"])
