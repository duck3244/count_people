"""
사람 수 카운팅 관련 기능을 제공하는 모듈
"""

import config

from sort import Sort


class PeopleCounter:
    """
    사람 카운터 클래스
    """
    def __init__(self):
        """
        카운터를 초기화합니다.
        """
        # SORT 트래커 초기화
        self.tracker = Sort(
            max_age=config.MAX_AGE,
            min_hits=config.MIN_HITS,
            iou_threshold=config.IOU_THRESHOLD
        )
        
        # 카운팅 데이터 초기화
        self.total_count_up = []
        self.total_count_down = []
        
        # 카운팅 라인 설정
        self.limits_up = config.LIMITS_UP
        self.limits_down = config.LIMITS_DOWN
        self.count_margin = config.COUNT_MARGIN


    def reset_counts(self):
        """
        카운트를 재설정합니다.
        """
        self.total_count_up = []
        self.total_count_down = []


    def update(self, detections):
        """
        감지된 객체를 추적하고 카운트를 업데이트합니다.
        
        Args:
            detections: SORT 트래커용 감지 배열 [x1, y1, x2, y2, confidence]
            
        Returns:
            tuple: (추적 결과, 활성화된 라인 목록)
                  추적 결과는 [x1, y1, x2, y2, id] 형식
                  활성화된 라인 목록은 'up' 또는 'down' 문자열 목록
        """
        # SORT 트래커 업데이트
        tracking_results = self.tracker.update(detections)
        
        activated_lines = []
        
        # 추적 결과 처리
        for result in tracking_results:
            x1, y1, x2, y2, id = result
            x1, y1, x2, y2, id = int(x1), int(y1), int(x2), int(y2), int(id)
            
            # 객체의 중심점 계산
            w, h = x2 - x1, y2 - y1
            cx, cy = x1 + w // 2, y1 + h // 2
            
            # 하향 카운팅 라인 교차 감지
            if self._is_crossing_down_line(cx, cy):
                if id not in self.total_count_down:
                    self.total_count_down.append(id)
                    activated_lines.append('down')
            
            # 상향 카운팅 라인 교차 감지
            if self._is_crossing_up_line(cx, cy):
                if id not in self.total_count_up:
                    self.total_count_up.append(id)
                    activated_lines.append('up')
        
        return tracking_results, activated_lines


    def _is_crossing_down_line(self, cx, cy):
        """
        객체가 하향 카운팅 라인을 교차하는지 확인합니다.
        """
        return (
            self.limits_down[0] < cx < self.limits_down[2] and 
            self.limits_down[1] - self.count_margin < cy < self.limits_down[1] + self.count_margin
        )


    def _is_crossing_up_line(self, cx, cy):
        """
        객체가 상향 카운팅 라인을 교차하는지 확인합니다.
        """
        return (
            self.limits_up[0] < cx < self.limits_up[2] and 
            self.limits_up[1] - self.count_margin < cy < self.limits_up[1] + self.count_margin
        )


    def get_counts(self):
        """
        현재 카운트 값을 반환합니다.
        
        Returns:
            tuple: (상향 카운트, 하향 카운트)
        """
        return len(self.total_count_up), len(self.total_count_down)

