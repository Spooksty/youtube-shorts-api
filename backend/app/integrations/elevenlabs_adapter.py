import base64
from pathlib import Path

import httpx

from app.config import settings
from app.integrations.base import ApiResult, TTSProvider, WordTiming, check_response
from app.media_utils import probe_duration


def chars_to_words(chars: list[str], starts: list[float], ends: list[float]) -> list[WordTiming]:
    words, current, start, prev_end = [], "", None, 0.0
    for ch, s, e in zip(chars, starts, ends):
        if ch.isspace():
            if current:
                words.append(WordTiming(current, start, prev_end))
            current, start = "", None
            continue
        if start is None:
            start = s
        current += ch
        prev_end = e
    if current:
        words.append(WordTiming(current, start, prev_end))
    return words


class ElevenLabsAdapter(TTSProvider):
    name = "ElevenLabs"

    def list_voices(self) -> list[dict]:
        resp = httpx.get("https://api.elevenlabs.io/v1/voices",
                         headers={"xi-api-key": settings.elevenlabs_api_key}, timeout=20)
        check_response(resp)
        return [{"id": v["voice_id"], "name": v["name"]} for v in resp.json().get("voices", [])]

    def synthesize(self, text: str, voice_id: str, language: str, out_dir: Path) -> ApiResult:
        resp = httpx.post(
            f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}/with-timestamps",
            params={"output_format": "mp3_44100_128"},
            headers={"xi-api-key": settings.elevenlabs_api_key},
            json={"text": text, "model_id": "eleven_multilingual_v2"},
            timeout=120,
        )
        check_response(resp)
        body = resp.json()
        out = out_dir / "voice.mp3"
        out.write_bytes(base64.b64decode(body["audio_base64"]))

        al = body["alignment"]
        timings = chars_to_words(al["characters"], al["character_start_times_seconds"],
                                 al["character_end_times_seconds"])
        return ApiResult({"audio": out, "timings": timings, "duration": probe_duration(out)},
                         "elevenlabs", "text-to-speech", units=len(text),
                         cost_eur=round(len(text) * 0.00018, 5))
