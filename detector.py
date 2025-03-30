"""
객체 감지 관련 기능을 제공하는 모듈
"""

import numpy as np

from ultralytics import YOLO

import config


class ObjectDetector:
    """
    YOLO 객체 감지기 클래스
    """
    def __init__(self, model_path=config.MODEL_PATH):
        """
        YOLO 모델을 초기화합니다.
        
        Args:
            model_path (str): YOLO 모델 파일 경로
        """
        self.model = YOLO(model_path)
        self.confidence_threshold = config.CONFIDENCE_THRESHOLD
        self.target_class = config.TARGET_CLASS


    def detect(self, frame):
        """
        이미지 프레임에서 객체를 감지합니다.
        
        Args:
            frame: 객체를 감지할 이미지 프레임
            
        Returns:
            tuple: (원본 프레임에 표시할 박스 리스트, SORT 트래커용 감지 배열)
                  각 박스는 (x1, y1, x2, y2, conf, cls, name) 형식
        """
        # 객체 감지 수행
        results = self.model.predict(frame, stream=True, verbose=False)
        
        # 감지된 객체를 저장할 리스트와 배열 초기화
        detections = np.empty((0, 5))  # SORT 트래커용 감지 배열
        boxes_info = []  # 화면에 표시할 박스 정보
        
        # 결과 처리
        for r in results:
            boxes = r.boxes
            for box in boxes:
                # 박스 좌표 추출
                x1, y1, x2, y2 = box.xyxy[0]
                x1, y1, x2, y2 = int(x1), int(y1), int(x2), int(y2)
                
                # 신뢰도 점수
                conf = float(box.conf[0])
                
                # 클래스 ID 및 이름
                cls = int(box.cls[0])
                class_name = self.model.names[cls]
                
                # 대상 클래스와 신뢰도 임계값 확인
                if class_name == self.target_class and conf > self.confidence_threshold:
                    # 화면에 표시할 정보 저장
                    boxes_info.append((x1, y1, x2, y2, conf, cls, class_name))
                    
                    # SORT 트래커용 배열 구성 [x1, y1, x2, y2, confidence]
                    detection_array = np.array([x1, y1, x2, y2, conf])
                    detections = np.vstack((detections, detection_array))
        
        return boxes_info, detections

