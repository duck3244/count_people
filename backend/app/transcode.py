"""
mp4v 출력을 브라우저 친화적인 H.264(libx264)로 트랜스코딩.

OpenCV의 mp4v 컨테이너는 Chrome에선 재생되지만 Safari/일부 환경에서 깨짐.
처리 후 1단계 ffmpeg 호출로 호환성 문제를 영구 해결.
"""

from __future__ import annotations

import logging
import shutil
import subprocess
from pathlib import Path

logger = logging.getLogger("people_counter.transcode")


def has_ffmpeg() -> bool:
    return shutil.which("ffmpeg") is not None


def transcode_to_h264(src: str | Path, dst: str | Path) -> Path:
    """
    src(mp4v) → dst(H.264 + faststart). 실패 시 RuntimeError.
    같은 경로로 in-place 트랜스코딩이 필요하면 호출자가 임시 파일 사용 후 rename.
    """
    src_p = Path(src)
    dst_p = Path(dst)
    if not src_p.exists():
        raise FileNotFoundError(f"트랜스코딩 입력 없음: {src_p}")
    dst_p.parent.mkdir(parents=True, exist_ok=True)

    cmd = [
        "ffmpeg",
        "-y",
        "-loglevel", "error",
        "-i", str(src_p),
        "-c:v", "libx264",
        "-preset", "veryfast",
        "-crf", "23",
        "-pix_fmt", "yuv420p",
        "-movflags", "+faststart",
        "-an",  # 오디오 없음
        str(dst_p),
    ]
    logger.debug("ffmpeg cmd: %s", " ".join(cmd))
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(
            f"ffmpeg 트랜스코딩 실패 (code={result.returncode}): {result.stderr.strip()}"
        )
    return dst_p
