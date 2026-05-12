"""WebSocket 라우터: /api/jobs/{id}/progress"""

from __future__ import annotations

import asyncio
import logging
from contextlib import suppress

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from ..jobs import JobNotFound, SingleJobStore
from ..schemas import ProgressMessage

logger = logging.getLogger("people_counter.ws")

router = APIRouter(prefix="/api/jobs", tags=["jobs-ws"])


@router.websocket("/{job_id}/progress")
async def progress_ws(ws: WebSocket, job_id: str) -> None:
    store: SingleJobStore = ws.app.state.store
    await ws.accept()

    try:
        job = store.get(job_id)
    except JobNotFound:
        await ws.send_json({"type": "error", "error": "job not found"})
        await ws.close(code=1008)
        return

    # 현재 상태 1회 송신 (재연결/늦은 구독자 대비)
    await ws.send_json(ProgressMessage(
        type="status",
        job_id=job.id,
        status=job.status,
        frame=job.frame,
        total_frames=job.total_frames,
        count_up=job.count_up,
        count_down=job.count_down,
        fps=job.fps,
        elapsed_sec=job.elapsed_sec,
    ).model_dump())

    queue = store.subscribe(job_id)

    async def reader():
        # 클라이언트 메시지(ping 등)를 단순히 소비. 끊김 감지 용도.
        try:
            while True:
                await ws.receive_text()
        except WebSocketDisconnect:
            return

    reader_task = asyncio.create_task(reader())
    try:
        while True:
            done, _ = await asyncio.wait(
                {asyncio.create_task(queue.get()), reader_task},
                return_when=asyncio.FIRST_COMPLETED,
            )
            if reader_task in done:
                break
            for d in done:
                msg: ProgressMessage = d.result()
                await ws.send_json(msg.model_dump())
                if msg.type in ("done", "error"):
                    return
    except WebSocketDisconnect:
        pass
    finally:
        reader_task.cancel()
        with suppress(Exception):
            await reader_task
        store.unsubscribe(job_id, queue)
