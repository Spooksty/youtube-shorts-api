import math
import time
from pathlib import Path

import httpx

from app.config import settings
from app.integrations.base import ApiError, ApiResult, MediaProvider, check_response

QUEUE_URL = "https://queue.fal.run"

PROMPT = ("Vertical short-form video shot. {keyword}. Context: {context}. "
          "Cinematic, realistic, smooth camera movement, no text, no captions, no watermarks.")


class FalQueue(MediaProvider):
    def __init__(self, client: httpx.Client | None = None, poll_seconds: float = 2, timeout_seconds: float = 600):
        self.client = client or httpx.Client(timeout=60)
        self.poll_seconds = poll_seconds
        self.timeout_seconds = timeout_seconds
        self.headers = {"Authorization": f"Key {settings.fal_key}"}

    def run(self, model: str, payload: dict) -> dict:
        resp = self.client.post(f"{QUEUE_URL}/{model}", headers=self.headers, json=payload)
        check_response(resp)
        request = resp.json()

        deadline = time.monotonic() + self.timeout_seconds
        while time.monotonic() < deadline:
            resp = self.client.get(request["status_url"], headers=self.headers)
            check_response(resp)
            status = resp.json().get("status")
            if status == "COMPLETED":
                result = self.client.get(request["response_url"], headers=self.headers)
                check_response(result)
                return result.json()
            if status not in ("IN_QUEUE", "IN_PROGRESS"):
                raise ApiError(f"fal.ai statuss {status}")
            time.sleep(self.poll_seconds)
        raise ApiError("fal.ai neatbildēja laikā")

    def download(self, url: str, out: Path):
        with self.client.stream("GET", url, follow_redirects=True) as r:
            check_response(r)
            with open(out, "wb") as fh:
                for chunk in r.iter_bytes():
                    fh.write(chunk)


class FalVideo(FalQueue):
    name = "fal.ai video"

    def find_clip(self, keyword: str, out_stem: Path, min_duration: float, context: str = "") -> ApiResult | None:
        duration = min(max(math.ceil(min_duration), 3), 15)
        result = self.run(settings.fal_video_model, {
            "prompt": PROMPT.format(keyword=keyword, context=context or keyword),
            "duration": duration,
            "resolution": settings.fal_video_resolution,
            "aspect_ratio": "9:16",
            "prompt_expansion_mode": "disabled",
        })
        url = (result.get("video") or {}).get("url")
        if not url:
            raise ApiError("fal.ai atbildē nav video")
        out = out_stem.with_suffix(".mp4")
        self.download(url, out)
        return ApiResult({"kind": "clip", "path": out, "author": f"MI ģenerēts ({settings.fal_video_model})",
                          "source_url": None},
                         "fal", "text-to-video", units=duration,
                         cost_eur=round(duration * settings.fal_video_cost_per_second_eur, 4))
