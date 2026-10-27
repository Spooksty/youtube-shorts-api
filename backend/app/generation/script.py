import re

from sqlalchemy import select

from app.integrations.factory import get_llm
from app.models import Channel, PromptTemplate, Script, Topic
from app.workflow.context import JobContext, PipelineError

DEFAULT_TEMPLATE = (
    'Write a YouTube Shorts script about "{topic}" for viewers aged {audience_age}. '
    "Language: {language}. Style: {style}. Start with a strong hook in the first sentence."
)

BANNED_WORDS = {"kill", "suicide", "drugs", "nazi", "porn", "gun", "weapon", "racist"}

MIN_WORDS, MAX_WORDS = 50, 150
MAX_ATTEMPTS = 3


class SafeDict(dict):
    def __missing__(self, key):
        return "{" + key + "}"


def render_prompt(template: str, topic: Topic, channel: Channel) -> str:
    return template.format_map(SafeDict(
        topic=topic.title, audience_age=channel.audience_age, language=channel.language,
        style=channel.style, niche=channel.niche,
    ))


def validate_script(data: dict, language: str) -> str | None:
    text = data.get("script") or ""
    title = data.get("title") or ""
    words = text.split()

    if len(words) < MIN_WORDS:
        return f"Skripts par īsu ({len(words)} vārdi, min {MIN_WORDS})"
    if len(words) > MAX_WORDS:
        return f"Skripts par garu ({len(words)} vārdi, max {MAX_WORDS})"
    if not title or len(title) > 100:
        return f"Nederīgs virsraksta garums ({len(title)})"
    if not data.get("keywords"):
        return "Nav vizuālo atslēgvārdu"

    lowered = set(re.findall(r"\w+", text.lower()))
    banned = lowered & BANNED_WORDS
    if banned:
        return f"Aizliegts saturs: {', '.join(sorted(banned))}"

    if language == "en":
        letters = [c for c in text if c.isalpha()]
        non_ascii = sum(1 for c in letters if not c.isascii())
        if letters and non_ascii / len(letters) > 0.05:
            return "Skripts nav angļu valodā"
    return None


def pick_template(ctx: JobContext, channel: Channel) -> str:
    tpl = ctx.db.scalars(select(PromptTemplate)
                         .where(PromptTemplate.channel_id == channel.id, PromptTemplate.is_active)
                         .order_by(PromptTemplate.version.desc())).first()
    return tpl.body if tpl else DEFAULT_TEMPLATE


def generate_script(ctx: JobContext, channel: Channel, topic: Topic) -> Script:
    llm = get_llm()
    prompt = render_prompt(pick_template(ctx, channel), topic, channel)

    for attempt in range(1, MAX_ATTEMPTS + 1):
        with ctx.step("Skripta ģenerēšana") as s:
            result = ctx.api("Skripta ģenerēšana",
                             lambda: llm.generate_script(prompt, topic.title, channel.language))
            data = result.data
            s.message = f"{llm.name}, mēģinājums {attempt}, {len(data.get('script', '').split())} vārdi"

        reason = validate_script(data, channel.language)
        script = Script(
            job_id=ctx.job.id, attempt=attempt, text=data.get("script", ""),
            title=data.get("title", "")[:300], description=data.get("description", ""),
            tags=data.get("tags", []), keywords=data.get("keywords", []),
            fallback_keywords=data.get("fallback_keywords", []),
            is_valid=reason is None, validation_message=reason,
        )
        ctx.db.add(script)
        ctx.db.commit()

        if reason is None:
            ctx.log("Skripta pārbaude", "ok", "Pārbaude izturēta")
            return script
        ctx.log("Skripta pārbaude", "warn", reason)

    raise PipelineError(f"Skripts neizturēja pārbaudi {MAX_ATTEMPTS} mēģinājumos")
