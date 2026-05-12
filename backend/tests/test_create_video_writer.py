from pathlib import Path
from unittest.mock import MagicMock

import cv2
import pytest

from helper import create_video_writer


def _fake_cap(width=640, height=360, fps=30.0):
    cap = MagicMock(spec=cv2.VideoCapture)
    def _get(prop):
        return {
            cv2.CAP_PROP_FRAME_WIDTH: width,
            cv2.CAP_PROP_FRAME_HEIGHT: height,
            cv2.CAP_PROP_FPS: fps,
        }[prop]
    cap.get.side_effect = _get
    return cap


def test_writer_opens_with_normal_fps(tmp_path: Path):
    cap = _fake_cap(640, 360, 30.0)
    out = tmp_path / "out.mp4"
    writer = create_video_writer(cap, str(out))
    try:
        assert writer.isOpened()
    finally:
        writer.release()


def test_writer_opens_when_source_fps_is_zero(tmp_path: Path):
    cap = _fake_cap(640, 360, 0.0)
    out = tmp_path / "out_zero_fps.mp4"
    writer = create_video_writer(cap, str(out))
    try:
        # fps=0 입력에 대해 fallback(30.0)으로 정상 생성되어야 함
        assert writer.isOpened()
    finally:
        writer.release()


def test_writer_respects_explicit_fps(tmp_path: Path):
    cap = _fake_cap(320, 240, 0.0)
    out = tmp_path / "out_explicit.mp4"
    writer = create_video_writer(cap, str(out), fps=15.0)
    try:
        assert writer.isOpened()
    finally:
        writer.release()
