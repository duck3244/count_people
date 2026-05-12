"""API DTO."""

from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel


JobStatus = Literal["queued", "running", "completed", "failed", "cancelled"]


class JobCreated(BaseModel):
    job_id: str


class JobView(BaseModel):
    id: str
    status: JobStatus
    progress: float  # 0.0 ~ 1.0 (또는 -1: 알 수 없음)
    frame: int
    total_frames: Optional[int]
    count_up: int
    count_down: int
    fps: float
    elapsed_sec: float
    error: Optional[str] = None
    created_at: float
    finished_at: Optional[float] = None
    has_video: bool


class ActiveJobView(BaseModel):
    job_id: Optional[str]


class ProgressMessage(BaseModel):
    type: Literal["progress", "status", "done", "error"]
    job_id: str
    status: JobStatus
    frame: int = 0
    total_frames: Optional[int] = None
    count_up: int = 0
    count_down: int = 0
    fps: float = 0.0
    elapsed_sec: float = 0.0
    error: Optional[str] = None
