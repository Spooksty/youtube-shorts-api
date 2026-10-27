import hashlib
import json
import time
from pathlib import Path

import httpx

from app.config import settings
from app.integrations.base import ApiResult, MediaProvider, check_response

SEARCH_URL = "https://pixabay.com/api/videos/"
CACHE_SECONDS = 24 * 3600
JUDGE_BATCH = 6


def query_variants(keyword: str) -> list[str]:
    words = keyword.split()
    variants = [" ".join(words[:n]) for n in range(len(words), 1, -1)]
    return variants or [keyword]


def relevant(hit: dict, query: str) -> bool:
    tags = hit.get("tags", "").lower()
    words = [w for w in query.lower().split() if len(w) > 2]
    return all(w[:5] in tags for w in words)


def pick_rendition(hit: dict) -> dict | None:
    for size in ("medium", "small", "large"):
        r = (hit.get("videos") or {}).get(size) or {}
        if r.get("url") and r.get("width"):
            return r
    return None


class PixabayAdapter(MediaProvider):
    name = "Pixabay"

    def __init__(self, client: httpx.Client | None = None, cache_dir: Path | None = None):
        self.client = client or httpx.Client(timeout=30)
        self.cache_dir = cache_dir or settings.data_dir / "cache" / "pixabay"
        self.used: set[int] = set()

    def search(self, query: str) -> list[dict]:
        params = {"q": query[:100], "video_type": "film", "safesearch": "true", "per_page": 30}
        cache = self.cache_dir / (hashlib.sha1(json.dumps(params, sort_keys=True).encode()).hexdigest() + ".json")
        if cache.exists() and time.time() - cache.stat().st_mtime < CACHE_SECONDS:
            return json.loads(cache.read_text(encoding="utf-8"))

        resp = self.client.get(SEARCH_URL, params={**params, "key": settings.pixabay_api_key})
        check_response(resp)
        hits = resp.json().get("hits", [])
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        cache.write_text(json.dumps(hits), encoding="utf-8")
        return hits

    def choose(self, hits: list[dict], query: str, min_duration: float,
               topic: str = "") -> tuple[dict, dict, int | None] | None:
        candidates = []
        for hit in hits:
            r = pick_rendition(hit)
            if hit["id"] in self.used or not r or hit.get("duration", 0) < min(min_duration, 4):
                continue
            if not relevant(hit, query):
                continue
            portrait = r["height"] > r["width"]
            if settings.pixabay_portrait_only and not portrait:
                continue
            candidates.append((not portrait, hit, r))
        if not candidates:
            return None
        candidates.sort(key=lambda c: c[0])
        candidates = candidates[:JUDGE_BATCH]

        thumbs = [c[2].get("thumbnail") for c in candidates]
        scores = self.judge_scores(thumbs, topic or query, query) if all(thumbs) else None
        if scores is None:
            return candidates[0][1], candidates[0][2], None
        best = max(range(len(candidates)), key=lambda i: (scores[i], -i))
        if scores[best] < settings.vision_min_score:
            return None
        return candidates[best][1], candidates[best][2], scores[best]

    def find_clip(self, keyword: str, out_stem: Path, min_duration: float, context: str = "") -> ApiResult | None:
        for query in query_variants(keyword):
            picked = self.choose(self.search(query), query, min_duration, context)
            if not picked:
                continue
            hit, rendition, score = picked
            self.used.add(hit["id"])
            out = out_stem.with_suffix(".mp4")
            with self.client.stream("GET", rendition["url"], follow_redirects=True, timeout=120) as r:
                check_response(r)
                with open(out, "wb") as fh:
                    for chunk in r.iter_bytes():
                        fh.write(chunk)
            return ApiResult({"kind": "clip", "path": out, "author": hit.get("user"),
                              "source_url": hit.get("pageURL"), "query": query, "score": score},
                             "pixabay", "videos.search", units=1)
        return None
