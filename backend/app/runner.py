"""
백그라운드 워커: pipeline 실행 + progress 스로틀 + 트랜스코딩.
"""

from __future__ import annotations

import asyncio
import logging
import time
from concurrent.futures import ThreadPoolExecutor
from typing import Optional

from detector import ObjectDetector

from .jobs import Job, SingleJobStore
from .pipeline import ProgressEvent, run_pipeline
from .schemas import ProgressMessage
from .settings import settings
from .transcode import has_ffmpeg, transcode_to_h264

logger = logging.getLogger("people_counter.runner")

# YOLO 모델은 GPU에 로드된 단일 인스턴스. 모델 단위 직렬화가 필요해
# 워커 풀 크기는 1로 고정.
_executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="pipeline")


async def run_job(
    job: Job,
    store: SingleJobStore,
    detector: ObjectDetector,
) -> None:
    """이벤트 루프 안에서 호출. 파이프라인은 별도 스레드에서 실행."""
    loop = asyncio.get_running_loop()
    store.mark_running(job.id)
    _publish_status(store, job, "status")

    throttle_interval = 1.0 / max(settings.progress_throttle_hz, 0.1)
    last_emit = 0.0

    def on_progress(ev: ProgressEvent) -> None:
        # 워커 스레드에서 호출됨. publish는 큐 put_nowait이라 스레드 안전.
        nonlocal last_emit
        now = time.time()
        if now - last_emit < throttle_interval:
            return
        last_emit = now
        job.update_from_event(ev)
        store.publish(job.id, ProgressMessage(
            type="progress",
            job_id=job.id,
            status="running",
            frame=ev.frame,
            total_frames=ev.total_frames,
            count_up=ev.count_up,
            count_down=ev.count_down,
            fps=ev.fps,
            elapsed_sec=ev.elapsed_sec,
        ))

    def _do_work():
        result = run_pipeline(
            str(job.input_path),
            str(job.raw_output_path),
            detector=detector,
            on_progress=on_progress,
            cancel_event=job.cancel_event,
            display=False,
        )
        # 트랜스코딩 (취소되지 않은 경우만)
        if (
            settings.transcode_to_h264
            and not result.interrupted
            and has_ffmpeg()
            and job.raw_output_path.exists()
        ):
            try:
                transcode_to_h264(job.raw_output_path, job.output_path)
                # 원본 mp4v는 정리
                job.raw_output_path.unlink(missing_ok=True)
            except Exception as e:
                logger.warning("트랜스코딩 실패, 원본 사용: %s", e)
                job.raw_output_path.replace(job.output_path)
        else:
            # 트랜스코딩 안 함 → raw를 output으로 rename
            if job.raw_output_path.exists():
                job.raw_output_path.replace(job.output_path)
        return result

    try:
        result = await loop.run_in_executor(_executor, _do_work)
    except Exception as e:  # noqa: BLE001
        logger.exception("Job 실행 실패: %s", job.id)
        store.mark_failed(job.id, str(e))
        store.publish(job.id, ProgressMessage(
            type="error", job_id=job.id, status="failed", error=str(e),
        ))
        return

    store.mark_completed(job.id, result)
    final_status = "cancelled" if result.interrupted else "completed"
    store.publish(job.id, ProgressMessage(
        type="done",
        job_id=job.id,
        status=final_status,
        frame=result.frames,
        total_frames=result.frames,
        count_up=result.count_up,
        count_down=result.count_down,
        fps=result.fps,
        elapsed_sec=result.elapsed_sec,
    ))


def _publish_status(store: SingleJobStore, job: Job, kind: str) -> None:
    store.publish(job.id, ProgressMessage(
        type="status", job_id=job.id, status=job.status,
        frame=job.frame, total_frames=job.total_frames,
        count_up=job.count_up, count_down=job.count_down,
        fps=job.fps, elapsed_sec=job.elapsed_sec,
    ))
