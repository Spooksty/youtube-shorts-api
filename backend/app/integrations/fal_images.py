from pathlib import Path

from app.config import settings
from app.integrations.base import ApiError, ApiResult
from app.integrations.fal_video import FalQueue

PROMPT = ("A realistic cinematic photograph showing {keyword}, related to {context}. "
          "Natural scene, dramatic lighting, rich colors, shallow depth of field. "
          "The image contains no words, letters, signs, titles or watermarks.")


class FalImages(FalQueue):
    name = "fal.ai attēli"

    def generate(self, keyword: str, context: str, out: Path):
        result = self.run(settings.fal_image_model, {
            "prompt": PROMPT.format(keyword=keyword, context=context or keyword),
            "image_size": {"width": 768, "height": 1344},
            "num_images": 1,
            "output_format": "jpeg",
        })
        if any(result.get("has_nsfw_concepts") or []):
            raise ApiError("fal.ai attēls noraidīts (drošības filtrs)")
        images = result.get("images") or []
        if not images:
            raise ApiError("fal.ai atbildē nav attēla")
        self.download(images[0]["url"], out)

    def find_clip(self, keyword: str, out_stem: Path, min_duration: float, context: str = "") -> ApiResult | None:
        out = out_stem.with_suffix(".jpg")
        self.generate(keyword, context, out)
        attempts = 1
        score = (self.judge_scores([out], context or keyword, keyword) or [None])[0]
        if score is not None and score < settings.vision_min_score:
            retry = out.with_name(out.stem + "_2.jpg")
            self.generate(keyword, context, retry)
            attempts = 2
            score2 = (self.judge_scores([retry], context or keyword, keyword) or [None])[0]
            if score2 is not None and score2 > score:
                retry.replace(out)
                score = score2
            else:
                retry.unlink(missing_ok=True)

        return ApiResult({"kind": "image", "path": out, "author": f"MI ģenerēts ({settings.fal_image_model})",
                          "source_url": None, "score": score},
                         "fal", "text-to-image", units=attempts, cost_eur=settings.fal_image_cost_eur * attempts)
