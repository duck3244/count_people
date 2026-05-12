"""
공통 처리 파이프라인 — CLI와 FastAPI에서 공유.

run_pipeline() 한 함수가:
- 비디오 캡처/라이터 셋업
- 영상 해상도에 맞춰 카운팅 라인 정규화 좌표 → 픽셀 좌표 변환
- 검출/추적/카운팅/시각화/저장 루프
- on_progress 콜백 + cancel_event 협조 종료
- (선택) 결과 imshow 표시
까지 책임집니다.
"""

from __future__ import annotations

import threading
import time
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Callable, Optional

import cv2

import config
from counter import PeopleCounter
from detector import ObjectDetector
from helper import create_video_writer
from visualizer import Visualizer


@dataclass
class ProgressEvent:
    frame: int
    total_frames: Optional[int]
    count_up: int
    count_down: int
    fps: float
    elapsed_sec: float

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class PipelineResult:
    frames: int
    count_up: int
    count_down: int
    fps: float
    elapsed_sec: float
    interrupted: bool
    width: int
    height: int
    src_fps: float
    output_path: str

    def to_dict(self) -> dict:
        return asdict(self)


ProgressCallback = Callable[[ProgressEvent], None]


def _apply_lines_for_resolution(
    counter: PeopleCounter,
    visualizer: Visualizer,
    width: int,
    height: int,
) -> None:
    """영상 해상도에 맞춰 카운팅 라인 픽셀 좌표를 갱신."""
    up = config.denormalize_line(config.LIMITS_UP_NORM, width, height)
    down = config.denormalize_line(config.LIMITS_DOWN_NORM, width, height)
    counter.limits_up, counter.limits_down = up, down
    visualizer.limits_up, visualizer.limits_down = up, down


def run_pipeline(
    input_path: str,
    output_path: str,
    *,
    model_path: str = config.MODEL_PATH,
    device: Optional[str] = None,
    detector: Optional[ObjectDetector] = None,
    on_progress: Optional[ProgressCallback] = None,
    progress_every: int = 1,
    cancel_event: Optional[threading.Event] = None,
    display: bool = False,
) -> PipelineResult:
    """
    한 영상을 처음부터 끝까지 처리한다.

    Args:
        input_path:  입력 비디오
        output_path: 출력 비디오 (mp4v 컨테이너)
        model_path:  YOLO 가중치 (detector 미지정 시)
        device:      'cuda'/'cpu'/None(자동)
        detector:    이미 워밍업된 ObjectDetector를 주입 (FastAPI 싱글톤용)
        on_progress: 매 프레임 호출되는 콜백 (스로틀은 호출자가 관리)
        progress_every: 콜백 호출 간격(프레임). 1=매 프레임
        cancel_event: set() 시 다음 프레임에서 즉시 종료
        display:     True면 cv2.imshow + 'q'키 종료 (CLI 전용)
    """
    cap = cv2.VideoCapture(input_path)
    if not cap.isOpened():
        raise RuntimeError(f"비디오 파일을 열 수 없습니다: {input_path}")

    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    src_fps = cap.get(cv2.CAP_PROP_FPS) or 0.0
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT)) or None

    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    writer = create_video_writer(cap, output_path)

    if detector is None:
        detector = ObjectDetector(model_path, device=device)

    counter = PeopleCounter()
    visualizer = Visualizer()
    _apply_lines_for_resolution(counter, visualizer, width, height)

    frame_count = 0
    count_up = count_down = 0
    interrupted = False
    t0 = time.time()

    try:
        while True:
            if cancel_event is not None and cancel_event.is_set():
                interrupted = True
                break

            success, frame = cap.read()
            if not success:
                break
            frame_count += 1

            boxes_info, detections = detector.detect(frame)
            tracking_results, activated_lines = counter.update(detections)
            count_up, count_down = counter.get_counts()

            frame = visualizer.draw_detection_boxes(frame, boxes_info)
            frame = visualizer.draw_tracking_boxes(frame, tracking_results)
            frame = visualizer.draw_counting_lines(frame, activated_lines)
            frame = visualizer.draw_count_info(frame, count_up, count_down)

            cv2.putText(frame, f"Frame: {frame_count}", (20, 120),
                        cv2.FONT_HERSHEY_PLAIN, 1.5, (255, 255, 255), 2)

            writer.write(frame)

            if on_progress is not None and (frame_count % progress_every == 0):
                elapsed = time.time() - t0
                fps_now = frame_count / elapsed if elapsed > 0 else 0.0
                on_progress(ProgressEvent(
                    frame=frame_count,
                    total_frames=total_frames,
                    count_up=count_up,
                    count_down=count_down,
                    fps=fps_now,
                    elapsed_sec=elapsed,
                ))

            if display:
                cv2.imshow("People Counter", frame)
                if cv2.waitKey(1) == ord("q"):
                    interrupted = True
                    break
    finally:
        cap.release()
        writer.release()
        if display:
            cv2.destroyAllWindows()

    elapsed = time.time() - t0
    fps_avg = frame_count / elapsed if elapsed > 0 else 0.0

    return PipelineResult(
        frames=frame_count,
        count_up=count_up,
        count_down=count_down,
        fps=fps_avg,
        elapsed_sec=elapsed,
        interrupted=interrupted,
        width=width,
        height=height,
        src_fps=src_fps,
        output_path=output_path,
    )
