import json

from app.integrations.base import WordTiming
from app.integrations.factory import get_tts
from app.models import Channel, MediaAsset, Script
from app.workflow.context import JobContext


def record_voice(ctx: JobContext, channel: Channel, script: Script):
    tts = get_tts()
    with ctx.step("Balss ierakstīšana") as s:
        result = ctx.api("Balss ierakstīšana",
                         lambda: tts.synthesize(script.text, channel.voice_id, channel.language, ctx.folder))
        audio = result.data["audio"]
        timings: list[WordTiming] = result.data["timings"]
        duration = result.data["duration"]

        (ctx.folder / "timings.json").write_text(
            json.dumps([t.__dict__ for t in timings], ensure_ascii=False), encoding="utf-8")
        ctx.db.add(MediaAsset(job_id=ctx.job.id, kind="audio", path=ctx.relative(audio), provider=tts.name))
        s.message = f"{tts.name}, {duration:.1f} s, {len(timings)} vārdi"

    return audio, timings, duration
