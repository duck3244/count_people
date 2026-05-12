"""애플리케이션 설정 (환경변수로 오버라이드 가능)."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


def _env_bool(key: str, default: bool) -> bool:
    val = os.environ.get(key)
    if val is None:
        return default
    return val.lower() in ("1", "true", "yes", "on")


def _env_int(key: str, default: int) -> int:
    return int(os.environ.get(key, default))


@dataclass(frozen=True)
class Settings:
    storage_dir: Path
    max_upload_bytes: int
    allowed_extensions: tuple[str, ...]
    transcode_to_h264: bool
    cors_origins: tuple[str, ...]
    progress_throttle_hz: float
    model_path: str

    @classmethod
    def load(cls) -> "Settings":
        backend_root = Path(__file__).resolve().parents[1]
        storage = Path(os.environ.get("PC_STORAGE_DIR", backend_root / "storage"))
        return cls(
            storage_dir=storage,
            max_upload_bytes=_env_int("PC_MAX_UPLOAD_MB", 200) * 1024 * 1024,
            allowed_extensions=(".mp4", ".mov", ".m4v", ".avi", ".mkv", ".webm"),
            transcode_to_h264=_env_bool("PC_TRANSCODE_H264", True),
            cors_origins=tuple(
                o.strip() for o in os.environ.get(
                    "PC_CORS_ORIGINS",
                    "http://localhost:5173,http://127.0.0.1:5173",
                ).split(",") if o.strip()
            ),
            progress_throttle_hz=float(os.environ.get("PC_PROGRESS_HZ", "10")),
            model_path=os.environ.get("PC_MODEL_PATH", str(backend_root / "yolov8n.pt")),
        )


settings = Settings.load()
