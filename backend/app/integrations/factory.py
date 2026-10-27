from app.config import settings
from app.integrations.base import LLMProvider, MediaProvider, TTSProvider, VideoPlatform


def get_llm() -> LLMProvider:
    if settings.openai_api_key:
        from app.integrations.openai_adapter import OpenAIAdapter
        return OpenAIAdapter()
    from app.integrations.template_llm import TemplateLLM
    return TemplateLLM()


def get_tts() -> TTSProvider:
    if settings.elevenlabs_api_key:
        from app.integrations.elevenlabs_adapter import ElevenLabsAdapter
        return ElevenLabsAdapter()
    from app.integrations.espeak_tts import EspeakTTS
    return EspeakTTS()


def make_media(name: str) -> MediaProvider | None:
    if name == "pixabay" and settings.pixabay_api_key:
        from app.integrations.pixabay_adapter import PixabayAdapter
        return PixabayAdapter()
    if name == "pexels" and settings.pexels_api_key:
        from app.integrations.pexels_adapter import PexelsAdapter
        return PexelsAdapter()
    if name == "fal_images" and settings.fal_key:
        from app.integrations.fal_images import FalImages
        return FalImages()
    if name in ("fal", "fal_video") and settings.fal_key:
        from app.integrations.fal_video import FalVideo
        return FalVideo()
    if name == "openai" and settings.openai_api_key:
        from app.integrations.openai_images import OpenAIImages
        return OpenAIImages()
    if name == "placeholder":
        from app.integrations.placeholder_media import PlaceholderMedia
        return PlaceholderMedia()
    return None


def media_chain() -> list[MediaProvider]:
    names = [n.strip() for n in settings.media_provider.split(",") if n.strip()]
    if names == ["auto"]:
        names = ["pixabay", "pexels", "fal_images" if settings.fal_key else "openai"]
    chain = [p for p in map(make_media, names) if p]
    if settings.vision_check and settings.openai_api_key:
        from app.integrations.vision_judge import VisionJudge
        judge = VisionJudge()
        for p in chain:
            p.judge = judge
    if not chain:
        from app.integrations.placeholder_media import PlaceholderMedia
        chain = [PlaceholderMedia()]
    return chain


def get_platform() -> VideoPlatform:
    from app.integrations.mock_youtube import MockYouTube
    return MockYouTube()


def active_providers() -> dict:
    return {
        "llm": get_llm().name,
        "tts": get_tts().name,
        "media": " → ".join(p.name for p in media_chain()),
        "platform": get_platform().name,
    }
