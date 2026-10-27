from app.db import SessionLocal, utcnow
from app.generation.montage import assemble, build_subtitles, technical_check
from app.generation.script import generate_script
from app.generation.topic import select_topic
from app.generation.tts import record_voice
from app.generation.visuals import collect_visuals
from app.models import Job, JobStatus, MediaAsset, Video
from app.publishing.upload import publish
from app.workflow.context import JobContext, PipelineError
from app.workflow.costs import budget_reached
from app.workflow.notifications import notify


def generate(ctx: JobContext):
    db, job = ctx.db, ctx.job
    channel = job.channel

    with ctx.step("Budžeta pārbaude") as s:
        reason = None
        if not channel.is_active:
            reason = "kanāls nav aktīvs"
        elif budget_reached(db):
            reason = "mēneša budžets sasniegts"
        s.message = f"Uzdevums atlikts: {reason}" if reason else "Budžets pieejams"
    if reason:
        notify(db, "warning", f"Uzdevums #{job.id} atlikts: {reason}", job.id)
        ctx.finish(JobStatus.POSTPONED)
        return

    job.started_at = utcnow()

    with ctx.step("Tēmas izvēle") as s:
        topic = select_topic(db, job)
        job.topic_id = topic.id
        s.message = topic.title

    script = generate_script(ctx, channel, topic)
    audio, timings, duration = record_voice(ctx, channel, script)
    clips = collect_visuals(ctx, script, duration, context=topic.title)

    with ctx.step("Montāža") as s:
        subs = ctx.folder / "subtitles.ass"
        build_subtitles(timings, subs)
        db.add(MediaAsset(job_id=job.id, kind="subtitles", path=ctx.relative(subs), provider="Balss laika zīmogi"))
        final = assemble(ctx.folder, clips, audio, duration)
        s.message = f"{len(clips)} materiāli, subtitri, {duration:.1f} s audio"

    with ctx.step("Tehniskā pārbaude") as s:
        check = technical_check(final)
        if not check["passed"]:
            raise PipelineError("Tehniskā pārbaude neizdevās: " + "; ".join(check["problems"]))
        s.message = f"{check['width']}×{check['height']}, {check['duration']:.1f} s, audio: jā"

    db.add(Video(job_id=job.id, script_id=script.id, title=script.title[:100], description=script.description,
                 tags=script.tags, path=ctx.relative(final), duration=check["duration"],
                 width=check["width"], height=check["height"], has_audio=check["has_audio"],
                 check_passed=True))

    if channel.schedule and channel.schedule.auto_publish:
        job.publish_after = utcnow()
        ctx.log("Pārskats", "ok", "Automātiskā publicēšana ieslēgta")
        ctx.finish(JobStatus.APPROVED)
    else:
        notify(db, "info", f"Video #{job.id} ({channel.name}) gaida apstiprinājumu", job.id)
        ctx.finish(JobStatus.PENDING_REVIEW)


def fail(job_id: int, error: Exception):
    with SessionLocal() as db:
        job = db.get(Job, job_id)
        job.status = JobStatus.ERROR
        job.error_message = str(error)
        job.finished_at = utcnow()
        notify(db, "error", f"Uzdevums #{job.id} ({job.channel.name}) neizdevās: {error}", job.id)
        db.commit()


def run_job(job_id: int):
    try:
        with SessionLocal() as db:
            generate(JobContext(db, db.get(Job, job_id)))
    except Exception as e:
        fail(job_id, e)


def run_publish(job_id: int):
    try:
        with SessionLocal() as db:
            publish(JobContext(db, db.get(Job, job_id)))
    except Exception as e:
        fail(job_id, e)
