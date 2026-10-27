import random
import re
import subprocess
from pathlib import Path

from app.integrations.base import ApiError, ApiResult, MediaProvider, maybe_fail

FONT = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
PALETTES = [
    ("0x0f2027", "0x2c5364"), ("0x42275a", "0x734b6d"), ("0x134e5e", "0x71b280"),
    ("0x3a1c71", "0xd76d77"), ("0x1f4037", "0x99f2c8"), ("0x232526", "0x414345"),
    ("0x355c7d", "0xc06c84"), ("0x0b486b", "0xf56217"),
]


class PlaceholderMedia(MediaProvider):
    name = "Placeholder (lokāli ģenerēts)"

    def find_clip(self, keyword: str, out_stem: Path, min_duration: float, context: str = "") -> ApiResult | None:
        maybe_fail("pexels")
        out_path = out_stem.with_suffix(".mp4")
        c0, c1 = random.choice(PALETTES)
        label = re.sub(r"[^\w ]", "", keyword).upper()
        duration = max(min_duration, 3)
        src = (f"gradients=s=540x960:d={duration:.2f}:r=30:speed=0.015:"
               f"c0={c0}:c1={c1}:seed={random.randint(1, 10_000)}")
        vf = (f"drawtext=fontfile={FONT}:text='{label}':fontsize=44:fontcolor=white@0.25:"
              f"x=(w-text_w)/2:y=h*0.2")
        proc = subprocess.run(
            ["ffmpeg", "-y", "-loglevel", "error", "-f", "lavfi", "-i", src, "-vf", vf,
             "-c:v", "libx264", "-preset", "ultrafast", "-pix_fmt", "yuv420p", str(out_path)],
            capture_output=True, text=True,
        )
        if proc.returncode != 0:
            raise ApiError(f"ffmpeg placeholder: {proc.stderr.strip()[-300:]}")

        return ApiResult({"kind": "clip", "path": out_path, "author": "Placeholder", "source_url": None},
                         "pexels", "videos.search", units=1, simulated=True)
