"""REST 라우터: /api/jobs"""

from __future__ import annotations

import asyncio
import logging
import os
import re
from pathlib import Path
from typing import Optional

import cv2
from fastapi import APIRouter, BackgroundTasks, HTTPException, Request, UploadFile, status
from fastapi.responses import FileResponse, JSONResponse, Response, StreamingResponse

from ..jobs import ConflictError, JobNotFound, SingleJobStore
from ..runner import run_job
from ..schemas import ActiveJobView, JobCreated, JobView
from ..settings import settings

logger = logging.getLogger("people_counter.api")

router = APIRouter(prefix="/api/jobs", tags=["jobs"])

CHUNK = 1024 * 1024  # 1MB


def _store(req: Request) -> SingleJobStore:
    return req.app.state.store


@router.get("/active", response_model=ActiveJobView)
def get_active(req: Request) -> ActiveJobView:
    store = _store(req)
    job = store.active()
    return ActiveJobView(job_id=job.id if job else None)


@router.post("", response_model=JobCreated, status_code=status.HTTP_201_CREATED)
async def create_job(req: Request, file: UploadFile) -> JobCreated:
    store = _store(req)

    # 확장자 검증
    suffix = Path(file.filename or "").suffix.lower()
    if suffix not in settings.allowed_extensions:
        raise HTTPException(
            status_code=415,
            detail=f"허용되지 않은 파일 형식: '{suffix}'. "
                   f"허용: {', '.join(settings.allowed_extensions)}",
        )

    try:
        job = store.create()
    except ConflictError as e:
        raise HTTPException(status_code=409, detail=str(e))

    # 디스크에 청크 단위 저장 + 사이즈 검증
    written = 0
    try:
        with job.input_path.open("wb") as f:
            while True:
                chunk = await file.read(CHUNK)
                if not chunk:
                    break
                written += len(chunk)
                if written > settings.max_upload_bytes:
                    raise HTTPException(
                        status_code=413,
                        detail=f"파일이 너무 큽니다 (>{settings.max_upload_bytes // (1024*1024)}MB)",
                    )
                f.write(chunk)
    except HTTPException:
        store.mark_failed(job.id, "upload too large")
        raise
    except Exception as e:  # noqa: BLE001
        store.mark_failed(job.id, f"upload failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

    # cv2가 실제로 영상을 열 수 있는지 검증
    cap = cv2.VideoCapture(str(job.input_path))
    if not cap.isOpened():
        cap.release()
        store.mark_failed(job.id, "invalid video file")
        raise HTTPException(status_code=415, detail="유효하지 않은 비디오 파일입니다.")
    job.total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT)) or None
    cap.release()

    # 백그라운드 실행 (FastAPI BackgroundTasks가 아니라 asyncio.create_task로
    # 응답 후 비동기 진행되며 store를 통해 진행 상황 노출)
    detector = req.app.state.detector
    asyncio.create_task(run_job(job, store, detector))

    return JobCreated(job_id=job.id)


@router.get("/{job_id}", response_model=JobView)
def get_job(req: Request, job_id: str) -> JobView:
    store = _store(req)
    try:
        job = store.get(job_id)
    except JobNotFound:
        raise HTTPException(status_code=404, detail="job not found")
    return job.to_view()


@router.delete("/{job_id}", status_code=status.HTTP_202_ACCEPTED)
def cancel_job(req: Request, job_id: str) -> dict:
    store = _store(req)
    try:
        store.cancel(job_id)
    except JobNotFound:
        raise HTTPException(status_code=404, detail="job not found")
    return {"job_id": job_id, "cancelled": True}


@router.get("/{job_id}/result")
def get_result(req: Request, job_id: str) -> JSONResponse:
    store = _store(req)
    try:
        job = store.get(job_id)
    except JobNotFound:
        raise HTTPException(status_code=404, detail="job not found")
    if job.status != "completed":
        raise HTTPException(status_code=409, detail=f"job is {job.status}")
    return JSONResponse({
        "job_id": job.id,
        "frames": job.frame,
        "count_up": job.count_up,
        "count_down": job.count_down,
        "fps": round(job.fps, 2),
        "elapsed_sec": round(job.elapsed_sec, 3),
    })


_RANGE_RE = re.compile(r"bytes=(\d+)-(\d*)")


@router.get("/{job_id}/video")
def get_video(req: Request, job_id: str) -> Response:
    """결과 영상 스트리밍 (HTTP Range 지원)."""
    store = _store(req)
    try:
        job = store.get(job_id)
    except JobNotFound:
        raise HTTPException(status_code=404, detail="job not found")
    if not job.output_path.exists():
        raise HTTPException(status_code=404, detail="video not ready")

    file_size = job.output_path.stat().st_size
    range_header = req.headers.get("range")

    if not range_header:
        return FileResponse(
            job.output_path,
            media_type="video/mp4",
            headers={"Accept-Ranges": "bytes", "Content-Length": str(file_size)},
        )

    m = _RANGE_RE.match(range_header)
    if not m:
        raise HTTPException(status_code=416, detail="invalid range header")
    start = int(m.group(1))
    end = int(m.group(2)) if m.group(2) else file_size - 1
    end = min(end, file_size - 1)
    if start > end:
        raise HTTPException(status_code=416, detail="range not satisfiable")
    length = end - start + 1

    def _iter():
        with job.output_path.open("rb") as f:
            f.seek(start)
            remaining = length
            while remaining > 0:
                chunk = f.read(min(CHUNK, remaining))
                if not chunk:
                    break
                remaining -= len(chunk)
                yield chunk

    headers = {
        "Content-Range": f"bytes {start}-{end}/{file_size}",
        "Accept-Ranges": "bytes",
        "Content-Length": str(length),
    }
    return StreamingResponse(_iter(), status_code=206, media_type="video/mp4", headers=headers)
