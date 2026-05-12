"""
설정 및 상수 값을 관리하는 모듈

좌표는 정규화(0.0 ~ 1.0)로 저장합니다. 실제 픽셀 좌표는
런타임에 영상 해상도(width, height)와 곱해 계산됩니다.
"""

from typing import Sequence, Tuple

# 입력 및 출력 파일 경로 (CLI 기본값)
INPUT_VIDEO_PATH = "sample.mp4"
OUTPUT_VIDEO_PATH = "output.mp4"

# YOLO 모델 경로
MODEL_PATH = "yolov8n.pt"

# 객체 감지 설정
CONFIDENCE_THRESHOLD = 0.3
TARGET_CLASS = "person"

# 트래커 설정
MAX_AGE = 20
MIN_HITS = 3
IOU_THRESHOLD = 0.3

# 카운팅 라인 (정규화 좌표 [x1, y1, x2, y2], 0.0 ~ 1.0)
# 기존 sample.mp4 (640x360) 기준 픽셀 좌표를 정규화
LIMITS_DOWN_NORM: Sequence[float] = (150 / 640, 220 / 360, 250 / 640, 220 / 360)
LIMITS_UP_NORM:   Sequence[float] = ( 70 / 640, 170 / 360, 160 / 640, 170 / 360)

# 실행 옵션
SHOW_WINDOW = True   # CLI에서만 의미 있음. 서버 파이프라인은 항상 무시.

# 시각화 설정
DETECTION_COLOR = (0, 255, 255)
TRACKER_COLOR   = (255, 0, 255)
LINE_COLOR      = (0, 0, 255)
ACTIVE_LINE_COLOR = (0, 255, 0)
COUNT_UP_COLOR   = (139, 195, 75)
COUNT_DOWN_COLOR = (50, 50, 230)


def denormalize_line(
    norm_line: Sequence[float], width: int, height: int
) -> Tuple[int, int, int, int]:
    """정규화 라인을 픽셀 좌표로 변환."""
    x1, y1, x2, y2 = norm_line
    return (
        int(round(x1 * width)),
        int(round(y1 * height)),
        int(round(x2 * width)),
        int(round(y2 * height)),
    )


# CLI 호환을 위한 sample.mp4(640x360) 기준 픽셀 좌표.
# 새 코드는 LIMITS_*_NORM + denormalize_line 사용 권장.
LIMITS_DOWN = denormalize_line(LIMITS_DOWN_NORM, 640, 360)
LIMITS_UP   = denormalize_line(LIMITS_UP_NORM,   640, 360)
