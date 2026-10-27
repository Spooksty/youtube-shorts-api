import base64
import json
from pathlib import Path

import httpx

from app.config import settings
from app.integrations.base import ApiError, ApiResult, check_response

PROMPT = """You check visuals for a YouTube Short about "{topic}".
This shot should show: "{scene}".
Rate every image, in the order given, from 0 to 10:
10 = clearly shows the subject of the video,
5 = only loosely related (e.g. generic ocean footage for a video about jellyfish),
0 = unrelated, or contains visible text/watermarks.
Answer only with JSON: {{"scores": [int, ...]}}"""

USD_TO_EUR = 0.92


def image_ref(img: str | Path) -> str:
    if isinstance(img, Path):
        mime = "image/png" if img.suffix == ".png" else "image/jpeg"
        return f"data:{mime};base64,{base64.b64encode(img.read_bytes()).decode()}"
    return img


class VisionJudge:
    def __init__(self, client: httpx.Client | None = None):
        self.client = client or httpx.Client(timeout=60)

    def score(self, images: list[str | Path], topic: str, scene: str) -> ApiResult:
        content = [{"type": "text", "text": PROMPT.format(topic=topic, scene=scene)}]
        content += [{"type": "image_url", "image_url": {"url": image_ref(i), "detail": "low"}} for i in images]
        resp = self.client.post(
            "https://api.openai.com/v1/chat/completions",
            headers={"Authorization": f"Bearer {settings.openai_api_key}"},
            json={"model": settings.vision_model, "response_format": {"type": "json_object"},
                  "messages": [{"role": "user", "content": content}]},
        )
        check_response(resp)
        body = resp.json()
        try:
            scores = [int(s) for s in json.loads(body["choices"][0]["message"]["content"])["scores"]]
        except (KeyError, ValueError, TypeError) as e:
            raise ApiError(f"Nederīga vērtējuma atbilde: {e}")
        if len(scores) != len(images):
            raise ApiError(f"Vērtējumu skaits ({len(scores)}) nesakrīt ar attēlu skaitu ({len(images)})")

        usage = body.get("usage", {})
        inp, out = usage.get("prompt_tokens", 0), usage.get("completion_tokens", 0)
        cost = (inp * 0.15 + out * 0.6) / 1_000_000 * USD_TO_EUR
        return ApiResult(scores, "openai", "vision.judge", units=len(images), cost_eur=round(cost, 6))
