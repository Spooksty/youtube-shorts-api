import math
import random
import shutil
from collections import Counter
from pathlib import Path

from app.integrations.base import ApiError, ApiResult, MediaProvider
from app.integrations.factory import media_chain
from app.integrations.placeholder_media import PlaceholderMedia
from app.models import MediaAsset, Script
from app.workflow.context import JobContext
from app.workflow.costs import register_cost

SECONDS_PER_CLIP = 6


def collect_visuals(ctx: JobContext, script: Script, duration: float, context: str = "") -> list[Path]:
    chain = media_chain()
    count = min(max(math.ceil(duration / SECONDS_PER_CLIP), 3), 8)
    clip_len = duration / count + 0.5
    keywords = list(script.keywords) or ["abstract"]
    fallback = list(script.fallback_keywords)

    def fetch(provider: MediaProvider, keyword: str, stem: Path) -> ApiResult | None:
        try:
            return ctx.api("Materiālu iegūšana", lambda: provider.find_clip(keyword, stem, clip_len, context))
        except ApiError as e:
            ctx.log("Materiālu iegūšana", "warn", f"{provider.name}, {keyword}: {e}")
            return None
        finally:
            for cost in provider.take_costs():
                register_cost(ctx.db, ctx.job.id, cost)

    files: list[Path] = []
    used = Counter()
    with ctx.step("Materiālu iegūšana") as s:
        for i in range(count):
            stem = ctx.folder / f"visual_{i + 1}"
            keyword = keywords[i % len(keywords)]
            result, provider = None, None
            for p in chain:
                result = fetch(p, keyword, stem)
                if result:
                    provider = p
                    break
                if p is chain[0] and len(chain) > 1:
                    ctx.log("Materiālu iegūšana", "info", f"{p.name}: nav piemērota materiāla '{keyword}'")

            if result and result.data.get("score") is not None:
                ctx.log("Materiālu iegūšana", "info",
                        f"{provider.name}: '{result.data.get('query', keyword)}', atbilstība {result.data['score']}/10")

            if result is None and files:
                src = random.choice(files)
                path = stem.with_suffix(src.suffix)
                shutil.copy(src, path)
                ctx.log("Materiālu iegūšana", "warn", f"{keyword}: nav materiāla, atkārtots {src.name}")
                files.append(path)
                used["atkārtoti"] += 1
                continue

            if result is None and fallback:
                keyword = fallback[i % len(fallback)]
                result = fetch(chain[0], keyword, stem)
                provider = chain[0] if result else None

            if result is None:
                try:
                    provider = PlaceholderMedia()
                    result = provider.find_clip(keyword, stem, clip_len)
                except ApiError:
                    continue

            path = result.data["path"]
            ctx.db.add(MediaAsset(job_id=ctx.job.id, kind=result.data["kind"], path=ctx.relative(path),
                                  provider=provider.name, keyword=result.data.get("query", keyword),
                                  author=result.data["author"], source_url=result.data["source_url"]))
            files.append(path)
            used[provider.name] += 1

        if not files:
            raise ApiError("Neizdevās iegūt nevienu vizuālo materiālu")
        s.message = ", ".join(f"{name}: {n}" for name, n in used.items())
    return files
