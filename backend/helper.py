from __future__ import annotations

from typing import Optional

import cv2


def create_video_writer(
    video_cap: cv2.VideoCapture,
    output_filename: str,
    fps: Optional[float] = None,
) -> cv2.VideoWriter:
    """
    입력 비디오 캡처의 속성에 맞춘 VideoWriter를 생성합니다.

    Args:
        video_cap: cv2.VideoCapture 객체
        output_filename: 출력 비디오 파일 경로
        fps: 출력 fps를 강제할 경우 지정. None이면 입력 fps 사용

    Returns:
        cv2.VideoWriter 객체
    """
    frame_width = int(video_cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    frame_height = int(video_cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

    src_fps = video_cap.get(cv2.CAP_PROP_FPS)
    # 일부 컨테이너는 fps를 0이나 NaN으로 보고하므로 안전한 기본값으로 폴백
    if fps is None:
        fps = src_fps if src_fps and src_fps > 0 else 30.0

    # 소문자 'mp4v' 가 더 폭넓게 인식됨
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    writer = cv2.VideoWriter(output_filename, fourcc, float(fps),
                             (frame_width, frame_height))

    return writer
