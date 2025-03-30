"""
설정 및 상수 값을 관리하는 모듈
"""

# 입력 및 출력 파일 경로
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

# 카운팅 라인 설정
LIMITS_DOWN = [150, 220, 250, 220]  # 아래 방향 카운팅 라인 [x1, y1, x2, y2]
LIMITS_UP = [70, 170, 160, 170]     # 위 방향 카운팅 라인 [x1, y1, x2, y2]
COUNT_MARGIN = 15  # 라인 주변 여유 공간

# 시각화 설정
DETECTION_COLOR = (0, 255, 255)  # 감지된 객체 박스 색상 (BGR)
TRACKER_COLOR = (255, 0, 255)    # 추적된 객체 박스 색상 (BGR)
LINE_COLOR = (0, 0, 255)         # 카운팅 라인 색상 (BGR)
ACTIVE_LINE_COLOR = (0, 255, 0)  # 활성화된 카운팅 라인 색상 (BGR)
COUNT_UP_COLOR = (139, 195, 75)  # 상향 카운트 텍스트 색상 (BGR)
COUNT_DOWN_COLOR = (50, 50, 230) # 하향 카운트 텍스트 색상 (BGR)
