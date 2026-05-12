"""
단일-사용자 가정 Job 관리.

- 활성 Job은 항상 1개만 허용 (충돌 시 ConflictError 발생).
- 새 Job 시작 시 이전 storage 디렉터리 자동 정리.
- 진행 이벤트는 asyncio queue로 모든 구독자에게 broadcast.
"""

from __future__ import annotations

import asyncio
import logging
import shutil
import threading
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from .pipeline import PipelineResult, ProgressEvent
from .schemas import JobStatus, JobView, ProgressMessage

logger = logging.getLogger("people_counter.jobs")


class ConflictError(RuntimeError):
    """다른 활성 Job이 있을 때 새로 시작 시도."""


class JobNotFound(LookupError):
    pass


@dataclass
class Job:
    id: str
    dir: Path
    input_path: Path
    output_path: Path  # 최종 결과 경로 (트랜스코딩 후 또는 원본)
    raw_output_path: Path  # 트랜스코딩 전 mp4v 경로
    status: JobStatus = "queued"
    frame: int = 0
    total_frames: Optional[int] = None
    count_up: int = 0
    count_down: int = 0
    fps: float = 0.0
    elapsed_sec: float = 0.0
    error: Optional[str] = None
    created_at: float = field(default_factory=time.time)
    finished_at: Optional[float] = None
    cancel_event: threading.Event = field(default_factory=threading.Event)
    result: Optional[PipelineResult] = None

    def progress(self) -> float:
        if self.total_frames and self.total_frames > 0:
            return min(1.0, self.frame / self.total_frames)
        return -1.0

    def to_view(self) -> JobView:
        return JobView(
            id=self.id,
            status=self.status,
            progress=self.progress(),
            frame=self.frame,
            total_frames=self.total_frames,
            count_up=self.count_up,
            count_down=self.count_down,
            fps=self.fps,
            elapsed_sec=self.elapsed_sec,
            error=self.error,
            created_at=self.created_at,
            finished_at=self.finished_at,
            has_video=self.output_path.exists() and self.status == "completed",
        )

    def update_from_event(self, ev: ProgressEvent) -> None:
        self.frame = ev.frame
        self.total_frames = ev.total_frames
        self.count_up = ev.count_up
        self.count_down = ev.count_down
        self.fps = ev.fps
        self.elapsed_sec = ev.elapsed_sec


class SingleJobStore:
    """활성 Job 1개만 보장하는 인메모리 저장소."""

    def __init__(self, storage_dir: Path) -> None:
        self.storage_dir = storage_dir
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        self._jobs: dict[str, Job] = {}
        self._active_id: Optional[str] = None
        self._lock = threading.Lock()
        # job_id -> set[asyncio.Queue[ProgressMessage]]
        self._subscribers: dict[str, set[asyncio.Queue]] = {}

    # -- 라이프사이클 ----------------------------------------------------

    def create(self) -> Job:
        """새 Job 생성. 활성 Job이 있으면 ConflictError."""
        with self._lock:
            if self._active_id is not None:
                active = self._jobs.get(self._active_id)
                if active and active.status in ("queued", "running"):
                    raise ConflictError(
                        f"이미 처리 중인 작업이 있습니다 (job_id={self._active_id})."
                    )
            # 직전 Job storage 정리
            self._purge_storage_except(None)
            self._jobs.clear()
            self._subscribers.clear()

            job_id = uuid.uuid4().hex[:12]
            job_dir = self.storage_dir / job_id
            job_dir.mkdir(parents=True, exist_ok=True)
            job = Job(
                id=job_id,
                dir=job_dir,
                input_path=job_dir / "input.mp4",
                output_path=job_dir / "output.mp4",
                raw_output_path=job_dir / "output_raw.mp4",
            )
            self._jobs[job_id] = job
            self._active_id = job_id
            logger.info("Job 생성: %s (dir=%s)", job_id, job_dir)
            return job

    def get(self, job_id: str) -> Job:
        job = self._jobs.get(job_id)
        if job is None:
            raise JobNotFound(job_id)
        return job

    def active(self) -> Optional[Job]:
        if self._active_id is None:
            return None
        return self._jobs.get(self._active_id)

    def mark_running(self, job_id: str) -> None:
        with self._lock:
            self._jobs[job_id].status = "running"

    def mark_completed(self, job_id: str, result: PipelineResult) -> None:
        with self._lock:
            job = self._jobs[job_id]
            job.status = "cancelled" if result.interrupted else "completed"
            job.result = result
            job.finished_at = time.time()
            job.frame = result.frames
            job.count_up = result.count_up
            job.count_down = result.count_down
            job.fps = result.fps
            job.elapsed_sec = result.elapsed_sec
            self._active_id = None

    def mark_failed(self, job_id: str, error: str) -> None:
        with self._lock:
            job = self._jobs.get(job_id)
            if job is None:
                return
            job.status = "failed"
            job.error = error
            job.finished_at = time.time()
            if self._active_id == job_id:
                self._active_id = None

    def cancel(self, job_id: str) -> None:
        with self._lock:
            job = self._jobs.get(job_id)
            if job is None:
                raise JobNotFound(job_id)
            if job.status in ("completed", "failed", "cancelled"):
                return
            job.cancel_event.set()
            logger.info("Job 취소 요청: %s", job_id)

    # -- 구독 ------------------------------------------------------------

    def subscribe(self, job_id: str) -> asyncio.Queue:
        if job_id not in self._jobs:
            raise JobNotFound(job_id)
        q: asyncio.Queue = asyncio.Queue(maxsize=64)
        self._subscribers.setdefault(job_id, set()).add(q)
        return q

    def unsubscribe(self, job_id: str, q: asyncio.Queue) -> None:
        subs = self._subscribers.get(job_id)
        if subs and q in subs:
            subs.remove(q)

    def publish(self, job_id: str, msg: ProgressMessage) -> None:
        """워커 스레드에서 호출 안전 (queue.put_nowait + 큐 가득 시 drop)."""
        for q in list(self._subscribers.get(job_id, ())):
            try:
                q.put_nowait(msg)
            except asyncio.QueueFull:
                # 느린 구독자 → 가장 오래된 것 폐기 후 다시 시도
                try:
                    q.get_nowait()
                    q.put_nowait(msg)
                except Exception:
                    pass

    # -- 내부 ------------------------------------------------------------

    def _purge_storage_except(self, keep_id: Optional[str]) -> None:
        for child in self.storage_dir.iterdir():
            if not child.is_dir():
                continue
            if keep_id and child.name == keep_id:
                continue
            try:
                shutil.rmtree(child)
            except Exception as e:
                logger.warning("storage 정리 실패 (%s): %s", child, e)
