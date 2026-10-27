import os
from pathlib import Path


class Settings:
    database_url = os.getenv("DATABASE_URL", "postgresql+psycopg://yt:yt@localhost:5432/ytauto")
    data_dir = Path(os.getenv("DATA_DIR", "/data"))
    timezone = os.getenv("TZ", "Europe/Riga")
    secret_key = os.getenv("SECRET_KEY", "dev-secret-change-me")

    admin_username = os.getenv("ADMIN_USERNAME", "admin")
    admin_password = os.getenv("ADMIN_PASSWORD", "admin123")

    openai_api_key = os.getenv("OPENAI_API_KEY", "")
    openai_model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
    openai_image_model = os.getenv("OPENAI_IMAGE_MODEL", "gpt-image-1-mini")
    openai_image_quality = os.getenv("OPENAI_IMAGE_QUALITY", "low")
    openai_image_cost_eur = float(os.getenv("OPENAI_IMAGE_COST_EUR", "0.01"))
    fal_key = os.getenv("FALLAI_API_KEY") or os.getenv("FAL_KEY", "")
    fal_video_model = os.getenv("FAL_VIDEO_MODEL", "minimax/h3-max-turbo/text-to-video")
    fal_video_resolution = os.getenv("FAL_VIDEO_RESOLUTION", "768P")
    fal_video_cost_per_second_eur = float(os.getenv("FAL_VIDEO_COST_PER_SECOND_EUR", "0.037"))

    fal_image_model = os.getenv("FAL_IMAGE_MODEL", "fal-ai/flux/schnell")
    fal_image_cost_eur = float(os.getenv("FAL_IMAGE_COST_EUR", "0.003"))

    vision_check = os.getenv("VISION_CHECK", "true").lower() == "true"
    vision_model = os.getenv("VISION_MODEL", "gpt-4o-mini")
    vision_min_score = int(os.getenv("VISION_MIN_SCORE", "7"))

    pixabay_api_key = os.getenv("PIXABAY_API_KEY", "")
    pixabay_portrait_only = os.getenv("PIXABAY_PORTRAIT_ONLY", "false").lower() == "true"

    # tried in order: pixabay, pexels, fal_images, openai, fal_video, placeholder
    media_provider = os.getenv("MEDIA_PROVIDER", "auto").split("#")[0].strip()

    elevenlabs_api_key = os.getenv("ELEVENLABS_API_KEY", "")

    pexels_api_key = os.getenv("PEXELS_API_KEY", "")

    mock_failure_rate = float(os.getenv("MOCK_FAILURE_RATE", "0.1"))

    session_timeout_minutes = 60
    max_failed_logins = 5
    lockout_minutes = 15


settings = Settings()
