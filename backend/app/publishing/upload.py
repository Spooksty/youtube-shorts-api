from app.config import settings
from app.integrations.factory import get_platform
from app.models import Job, JobStatus, Publication
from app.workflow.context import JobContext
from app.workflow.costs import next_publish_window, quota_available
from app.workflow.notifications import notify


def publish(ctx: JobContext) -> bool:
    job: Job = ctx.job
    video = job.video
    channel = job.channel

    if not quota_available(ctx.db):
        window = next_publish_window(channel.schedule)
        job.publish_after = window
        ctx.log("Publicēšana", "warn", f"YouTube kvota nav pieejama, pārcelts uz {window:%d.%m. %H:%M}")
        notify(ctx.db, "warning", f"Video #{job.id} publicēšana pārcelta (nav YouTube kvotas)", job.id)
        ctx.db.commit()
        return False

    platform = get_platform()
    with ctx.step("Publicēšana") as s:
        result = ctx.api("Publicēšana", lambda: platform.upload(
            settings.data_dir / video.path, video.title, video.description, video.tags,
            channel.youtube_channel_id or ""))
        ctx.db.add(Publication(video_id=video.id, channel_id=channel.id, youtube_video_id=result.data,
                               title=video.title, description=video.description, tags=video.tags,
                               ai_generated=True, privacy="private"))
        s.message = f"{platform.name}, YouTube ID {result.data}, MI saturs atzīmēts"

    ctx.finish(JobStatus.PUBLISHED)
    return True
