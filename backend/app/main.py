"""FastAPI 엔트리포인트.

- lifespan: 모델 워밍업 + 앱 상태에 detector/store 등록
- CORS: dev에서 Vite(:5173)
- 라우터: /api/jobs (REST), /api/jobs/{id}/progress (WS)
"""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager

import numpy as np
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from detector import ObjectDetector

from .api import jobs as jobs_router
from .api import ws as ws_router
from .jobs import SingleJobStore
from .settings import settings


def _configure_logging() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    )


_configure_logging()
logger = logging.getLogger("people_counter.app")


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("YOLO 모델 로드: %s", settings.model_path)
    detector = ObjectDetector(settings.model_path)
    # 워밍업: 더미 프레임 1회 추론
    dummy = np.zeros((360, 640, 3), dtype=np.uint8)
    detector.detect(dummy)
    logger.info("모델 워밍업 완료 (device=%s)", detector.device)

    store = SingleJobStore(settings.storage_dir)
    app.state.detector = detector
    app.state.store = store
    yield
    logger.info("앱 종료")


app = FastAPI(title="People Counter API", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=list(settings.cors_origins),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(jobs_router.router)
app.include_router(ws_router.router)


@app.get("/api/health")
def health() -> dict:
    return {"ok": True}
