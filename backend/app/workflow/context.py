import time
from contextlib import contextmanager
from pathlib import Path
from typing import Callable

from sqlalchemy.orm import Session

from app.config import settings
from app.db import utcnow
from app.integrations.base import ApiResult, call_with_retry
from app.models import Job, JobLog
from app.workflow.costs import register_cost


class PipelineError(Exception):
    pass


class StepHandle:
    def __init__(self):
        self.message = ""


class JobContext:
    def __init__(self, db: Session, job: Job):
        self.db = db
        self.job = job
        self.folder = settings.data_dir / "jobs" / str(job.id)
        self.folder.mkdir(parents=True, exist_ok=True)

    def log(self, step: str, result: str, message: str = "", duration_ms: int = 0):
        self.db.add(JobLog(job_id=self.job.id, step=step, result=result, message=message,
                           duration_ms=duration_ms))
        self.db.commit()

    @contextmanager
    def step(self, name: str):
        self.job.current_step = name
        self.db.commit()
        handle = StepHandle()
        started = time.monotonic()
        try:
            yield handle
        except Exception as e:
            self.db.rollback()
            self.log(name, "error", str(e), int((time.monotonic() - started) * 1000))
            raise
        self.log(name, "ok", handle.message, int((time.monotonic() - started) * 1000))

    def api(self, step: str, fn: Callable[[], ApiResult | None]) -> ApiResult | None:
        def on_retry(n, err):
            self.log(step, "retry", f"{err}, atkārtojums {n}/3")

        result = call_with_retry(fn, on_retry=on_retry)
        if result is not None:
            register_cost(self.db, self.job.id, result)
        return result

    def relative(self, path: Path) -> str:
        return str(path.relative_to(settings.data_dir))

    def finish(self, status: str):
        self.job.status = status
        self.job.current_step = None
        self.job.finished_at = utcnow()
        self.db.commit()
