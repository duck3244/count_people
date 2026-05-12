"""
객체 감지 관련 기능을 제공하는 모듈
"""

from __future__ import annotations

from typing import List, Optional, Tuple

import numpy as np
import torch

from ultralytics import YOLO

import config


BoxInfo = Tuple[int, int, int, int, float, int, str]


class ObjectDetector:
    """YOLO 객체 감지기 클래스"""

    def __init__(
        self,
        model_path: str = config.MODEL_PATH,
        device: Optional[str] = None,
    ) -> None:
        """
        Args:
            model_path: YOLO 모델 파일 경로
            device: 'cuda', 'cpu' 등. None이면 자동 선택.
        """
        self.model = YOLO(model_path)

        if device is None:
            device = 'cuda' if torch.cuda.is_available() else 'cpu'
        self.device = device
        self.model.to(device)

        self.confidence_threshold = config.CONFIDENCE_THRESHOLD
        self.target_class = config.TARGET_CLASS

        # 모델 단계 클래스 필터링용 인덱스 미리 계산
        self.target_class_idx = next(
            (idx for idx, name in self.model.names.items() if name == self.target_class),
            None,
        )
        if self.target_class_idx is None:
            raise ValueError(
                f"모델에 '{self.target_class}' 클래스가 없습니다. "
                f"사용 가능한 클래스: {list(self.model.names.values())}"
            )


    def detect(self, frame: np.ndarray) -> Tuple[List[BoxInfo], np.ndarray]:
        """
        이미지 프레임에서 객체를 감지합니다.

        Returns:
            (시각화용 박스 리스트, SORT용 검출 배열 [N,5])
        """
        results = self.model.predict(
            frame,
            classes=[self.target_class_idx],
            conf=self.confidence_threshold,
            verbose=False,
        )

        boxes_info: List[BoxInfo] = []
        det_rows: List[List[float]] = []

        for r in results:
            boxes = r.boxes
            if boxes is None or len(boxes) == 0:
                continue

            xyxy = boxes.xyxy.cpu().numpy()
            confs = boxes.conf.cpu().numpy()
            clses = boxes.cls.cpu().numpy().astype(int)

            for (x1, y1, x2, y2), conf, cls in zip(xyxy, confs, clses):
                x1i, y1i, x2i, y2i = int(x1), int(y1), int(x2), int(y2)
                class_name = self.model.names[int(cls)]
                boxes_info.append((x1i, y1i, x2i, y2i, float(conf), int(cls), class_name))
                det_rows.append([x1i, y1i, x2i, y2i, float(conf)])

        if det_rows:
            detections = np.asarray(det_rows, dtype=float)
        else:
            detections = np.empty((0, 5), dtype=float)

        return boxes_info, detections
