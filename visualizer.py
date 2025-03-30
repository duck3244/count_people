"""
시각화 관련 기능을 제공하는 모듈
"""

import cv2
import config


class Visualizer:
    """
    감지 및 카운팅 결과를 시각화하는 클래스
    """
    def __init__(self):
        """
        시각화 도구를 초기화합니다.
        """
        self.detection_color = config.DETECTION_COLOR
        self.tracker_color = config.TRACKER_COLOR
        self.line_color = config.LINE_COLOR
        self.active_line_color = config.ACTIVE_LINE_COLOR
        self.count_up_color = config.COUNT_UP_COLOR
        self.count_down_color = config.COUNT_DOWN_COLOR
        
        # 카운팅 라인 설정
        self.limits_up = config.LIMITS_UP
        self.limits_down = config.LIMITS_DOWN


    def draw_detection_boxes(self, frame, boxes_info):
        """
        감지된 객체 상자를 그립니다.
        
        Args:
            frame: 출력 이미지 프레임
            boxes_info: 감지된 객체 정보 리스트 (x1, y1, x2, y2, conf, cls, name)
            
        Returns:
            프레임: 상자가 그려진 이미지 프레임
        """
        for box in boxes_info:
            x1, y1, x2, y2, conf, cls, name = box
            # 감지된 사람 사각형 그리기
            cv2.rectangle(frame, (x1, y1), (x2, y2), self.detection_color, 2)
        
        return frame


    def draw_tracking_boxes(self, frame, tracking_results):
        """
        추적된 객체 상자와 ID를 그립니다.
        
        Args:
            frame: 출력 이미지 프레임
            tracking_results: 추적 결과 리스트 [x1, y1, x2, y2, id]
            
        Returns:
            프레임: 상자가 그려진 이미지 프레임
        """
        for result in tracking_results:
            x1, y1, x2, y2, id = result
            x1, y1, x2, y2, id = int(x1), int(y1), int(x2), int(y2), int(id)
            
            # 박스 너비와 높이 계산
            w, h = x2 - x1, y2 - y1
            
            # 추적된 객체 사각형 그리기
            cv2.rectangle(frame, (x1, y1), (x2, y2), self.tracker_color, 2)
            
            # 객체 레이블 표시
            cv2.putText(frame, f"Person {id}", (x1, y1-10), cv2.FONT_HERSHEY_SIMPLEX, 
                        0.8, (255, 255, 0), 2, cv2.LINE_AA)
            
            # 객체의 중심점 표시
            cx, cy = x1 + w // 2, y1 + h // 2
            cv2.circle(frame, (cx, cy), 5, self.tracker_color, cv2.FILLED)
        
        return frame


    def draw_counting_lines(self, frame, activated_lines):
        """
        카운팅 라인을 그립니다.
        
        Args:
            frame: 출력 이미지 프레임
            activated_lines: 활성화된 라인 목록 ('up' 또는 'down')
            
        Returns:
            프레임: 라인이 그려진 이미지 프레임
        """
        # 기본 카운팅 라인 그리기
        up_line_color = self.active_line_color if 'up' in activated_lines else self.line_color
        down_line_color = self.active_line_color if 'down' in activated_lines else self.line_color
        
        cv2.line(frame, 
                 (self.limits_up[0], self.limits_up[1]), 
                 (self.limits_up[2], self.limits_up[3]), 
                 up_line_color, 5)
        
        cv2.line(frame, 
                 (self.limits_down[0], self.limits_down[1]), 
                 (self.limits_down[2], self.limits_down[3]), 
                 down_line_color, 5)
        
        return frame


    def draw_count_info(self, frame, count_up, count_down):
        """
        카운트 정보를 그립니다.
        
        Args:
            frame: 출력 이미지 프레임
            count_up: 상향 카운트 수
            count_down: 하향 카운트 수
            
        Returns:
            프레임: 정보가 그려진 이미지 프레임
        """
        cv2.putText(frame, f'Up: {count_up}', (20, 40), 
                    cv2.FONT_HERSHEY_PLAIN, 2, self.count_up_color, 3)
        cv2.putText(frame, f'Down: {count_down}', (20, 80), 
                    cv2.FONT_HERSHEY_PLAIN, 2, self.count_down_color, 3)
        
        return frame

