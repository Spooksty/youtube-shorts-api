import json

import httpx

from app.config import settings
from app.integrations.base import ApiError, ApiResult, LLMProvider, check_response

SYSTEM_PROMPT = """You write scripts for YouTube Shorts. Answer only with JSON:
{"script": str, "title": str, "description": str, "tags": [str],
 "keywords": [str], "fallback_keywords": [str]}
script - spoken text, about 75 words (30 seconds), no stage directions.
title - max 100 characters, in the same language as the script.
keywords - 5 English stock footage search queries, one per scene in script order, 2-3 words each.
Every query must start with the main subject of the video and add what it is doing or where,
e.g. for jellyfish: "jellyfish swimming", "jellyfish tentacles", "jellyfish glowing dark".
Never use abstract terms (biology, science, life, regeneration) - only things a camera can film.
fallback_keywords - 3 simpler queries that still contain the main subject, e.g. "jellyfish"."""

USD_TO_EUR = 0.92


class OpenAIAdapter(LLMProvider):
    name = "OpenAI"

    def generate_script(self, prompt: str, topic: str, language: str) -> ApiResult:
        resp = httpx.post(
            "https://api.openai.com/v1/chat/completions",
            headers={"Authorization": f"Bearer {settings.openai_api_key}"},
            json={
                "model": settings.openai_model,
                "response_format": {"type": "json_object"},
                "messages": [
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": prompt},
                ],
            },
            timeout=60,
        )
        check_response(resp)
        body = resp.json()
        try:
            data = json.loads(body["choices"][0]["message"]["content"])
        except (KeyError, json.JSONDecodeError) as e:
            raise ApiError(f"Nederīga OpenAI atbilde: {e}")

        usage = body.get("usage", {})
        inp, out = usage.get("prompt_tokens", 0), usage.get("completion_tokens", 0)
        cost = (inp * 0.15 + out * 0.6) / 1_000_000 * USD_TO_EUR
        return ApiResult(data, "openai", "chat.completions", units=inp + out, cost_eur=round(cost, 6))
