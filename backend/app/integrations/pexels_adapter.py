from pathlib import Path

import httpx

from app.config import settings
from app.integrations.base import ApiResult, MediaProvider, check_response


def pick_file(video: dict) -> dict | None:
    files = [f for f in video.get("video_files", []) if f.get("height") and f.get("width")
             and f["height"] > f["width"] and f.get("file_type") == "video/mp4"]
    if not files:
        return None
    files.sort(key=lambda f: abs(f["height"] - 1920))
    return files[0]


class PexelsAdapter(MediaProvider):
    name = "Pexels"

    def find_clip(self, keyword: str, out_stem: Path, min_duration: float, context: str = "") -> ApiResult | None:
        out_path = out_stem.with_suffix(".mp4")
        resp = httpx.get(
            "https://api.pexels.com/videos/search",
            params={"query": keyword, "orientation": "portrait", "per_page": 10},
            headers={"Authorization": settings.pexels_api_key},
            timeout=30,
        )
        check_response(resp)
        for video in resp.json().get("videos", []):
            if video.get("duration", 0) < min(min_duration, 4):
                continue
            f = pick_file(video)
            if not f:
                continue
            with httpx.stream("GET", f["link"], timeout=120, follow_redirects=True) as r:
                check_response(r)
                with open(out_path, "wb") as fh:
                    for chunk in r.iter_bytes():
                        fh.write(chunk)
            return ApiResult({"kind": "clip", "path": out_path, "author": video["user"]["name"],
                              "source_url": video["url"]},
                             "pexels", "videos.search", units=1)
        return None
