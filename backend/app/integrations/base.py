import random
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable

import httpx

from app.config import settings


class ApiError(Exception):
    pass


class TransientApiError(ApiError):
    pass


@dataclass
class ApiResult:
    data: Any
    service: str
    operation: str
    units: float = 0
    cost_eur: float = 0
    simulated: bool = False
    extra: dict = field(default_factory=dict)


@dataclass
class WordTiming:
    word: str
    start: float
    end: float


class LLMProvider(ABC):
    name = "llm"

    @abstractmethod
    def generate_script(self, prompt: str, topic: str, language: str) -> ApiResult: ...


class TTSProvider(ABC):
    name = "tts"

    @abstractmethod
    def synthesize(self, text: str, voice_id: str, language: str, out_dir: Path) -> ApiResult: ...

    def list_voices(self) -> list[dict]:
        return []


class MediaProvider(ABC):
    name = "media"
    judge = None

    def add_cost(self, result: ApiResult):
        self.__dict__.setdefault("_costs", []).append(result)

    def take_costs(self) -> list[ApiResult]:
        return self.__dict__.pop("_costs", [])

    def judge_scores(self, images: list, topic: str, scene: str) -> list[int] | None:
        if not self.judge:
            return None
        try:
            result = self.judge.score(images, topic, scene)
        except (ApiError, httpx.HTTPError):
            return None
        self.add_cost(result)
        return result.data

    @abstractmethod
    def find_clip(self, keyword: str, out_stem: Path, min_duration: float, context: str = "") -> ApiResult | None: ...


class VideoPlatform(ABC):
    name = "platform"

    @abstractmethod
    def upload(self, video_path: Path, title: str, description: str, tags: list[str], channel_ref: str) -> ApiResult: ...

    @abstractmethod
    def fetch_stats(self, video_ids: list[str]) -> ApiResult: ...


def call_with_retry(fn: Callable[[], ApiResult], retries: int = 3, base_delay: float = 1.0,
                    on_retry: Callable[[int, Exception], None] | None = None):
    attempt = 0
    while True:
        try:
            return fn()
        except (TransientApiError, httpx.TimeoutException, httpx.ConnectError) as e:
            if attempt >= retries:
                raise ApiError(f"{e} (pēc {retries} atkārtojumiem)") from e
            attempt += 1
            if on_retry:
                on_retry(attempt, e)
            time.sleep(base_delay * 2 ** (attempt - 1))


def check_response(resp: httpx.Response):
    if resp.status_code == 429 or resp.status_code >= 500:
        raise TransientApiError(f"HTTP {resp.status_code}")
    if resp.status_code >= 400:
        raise ApiError(f"HTTP {resp.status_code}: {resp.text[:200]}")


def maybe_fail(service: str):
    if random.random() < settings.mock_failure_rate:
        raise TransientApiError(f"{service}: HTTP 503 (simulēta pagaidu kļūda)")
