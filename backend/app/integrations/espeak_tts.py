import re
import subprocess
from pathlib import Path

from app.integrations.base import ApiError, ApiResult, TTSProvider, WordTiming, maybe_fail
from app.media_utils import probe_duration

VOICES = {"en": "en-us", "lv": "lv"}


def estimate_timings(text: str, duration: float) -> list[WordTiming]:
    words = text.split()
    weights = []
    for w in words:
        weight = len(re.sub(r"\W", "", w)) + 2
        if w[-1] in ".!?":
            weight += 5
        elif w[-1] in ",;:":
            weight += 2
        weights.append(weight)

    per_unit = duration / sum(weights)
    timings, t = [], 0.0
    for w, weight in zip(words, weights):
        end = t + weight * per_unit
        timings.append(WordTiming(w, round(t, 3), round(end, 3)))
        t = end
    return timings


class EspeakTTS(TTSProvider):
    name = "eSpeak NG (lokāls)"

    def synthesize(self, text: str, voice_id: str, language: str, out_dir: Path) -> ApiResult:
        maybe_fail("elevenlabs")
        out = out_dir / "voice.wav"
        voice = VOICES.get(language, "en-us")
        proc = subprocess.run(["espeak-ng", "-v", voice, "-s", "155", "-w", str(out), text],
                              capture_output=True, text=True)
        if proc.returncode != 0:
            raise ApiError(f"espeak-ng: {proc.stderr.strip()}")

        duration = probe_duration(out)
        timings = estimate_timings(text, duration)
        # roughly what ElevenLabs would charge
        return ApiResult({"audio": out, "timings": timings, "duration": duration},
                         "elevenlabs", "text-to-speech", units=len(text),
                         cost_eur=round(len(text) * 0.00018, 5), simulated=True)
