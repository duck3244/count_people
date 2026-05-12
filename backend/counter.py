"""
사람 수 카운팅 관련 기능을 제공하는 모듈
"""

from __future__ import annotations

from typing import Iterable, List, Sequence, Tuple

import numpy as np

import config

from sort import Sort


Point = Tuple[int, int]
Line = Sequence[int]  # [x1, y1, x2, y2]


class PeopleCounter:
    """
    사람 카운터 클래스
    """
    def __init__(self) -> None:
        # SORT 트래커 초기화
        self.tracker = Sort(
            max_age=config.MAX_AGE,
            min_hits=config.MIN_HITS,
            iou_threshold=config.IOU_THRESHOLD,
        )

        # 카운팅 데이터 초기화 (O(1) 멤버십 검사를 위해 set 사용)
        self.counted_up: set[int] = set()
        self.counted_down: set[int] = set()

        # 트랙 ID별 직전 프레임 중심점
        self._prev_centers: dict[int, Point] = {}

        # 카운팅 라인 설정
        self.limits_up: Line = config.LIMITS_UP
        self.limits_down: Line = config.LIMITS_DOWN


    def reset_counts(self) -> None:
        """카운트와 트랙 히스토리를 재설정합니다."""
        self.counted_up.clear()
        self.counted_down.clear()
        self._prev_centers.clear()


    def update(
        self,
        detections: np.ndarray,
    ) -> Tuple[np.ndarray, List[str]]:
        """
        감지된 객체를 추적하고 카운트를 업데이트합니다.

        Args:
            detections: SORT 트래커용 감지 배열 [x1, y1, x2, y2, confidence]

        Returns:
            (추적 결과 [x1,y1,x2,y2,id], 활성화된 라인 목록 ['up'|'down', ...])
        """
        tracking_results = self.tracker.update(detections)

        activated_lines: List[str] = []
        current_ids: set[int] = set()

        for result in tracking_results:
            x1, y1, x2, y2, tid = (int(v) for v in result)
            current_ids.add(tid)

            cx, cy = (x1 + x2) // 2, (y1 + y2) // 2
            prev = self._prev_centers.get(tid)
            self._prev_centers[tid] = (cx, cy)

            # 첫 등장 프레임에는 비교할 직전 위치가 없으므로 카운팅 생략
            if prev is None:
                continue

            dy = cy - prev[1]

            # 위쪽 라인을 위로(↑) 가로지르는 경우 → up 카운트
            if (
                tid not in self.counted_up
                and dy < 0
                and self._segment_crosses(prev, (cx, cy), self.limits_up)
            ):
                self.counted_up.add(tid)
                activated_lines.append('up')

            # 아래쪽 라인을 아래로(↓) 가로지르는 경우 → down 카운트
            if (
                tid not in self.counted_down
                and dy > 0
                and self._segment_crosses(prev, (cx, cy), self.limits_down)
            ):
                self.counted_down.add(tid)
                activated_lines.append('down')

        # 더 이상 추적되지 않는 트랙의 히스토리 정리
        stale = set(self._prev_centers).difference(current_ids)
        for tid in stale:
            self._prev_centers.pop(tid, None)

        return tracking_results, activated_lines


    def _segment_crosses(self, p1: Point, p2: Point, line: Line) -> bool:
        """선분 p1-p2 가 카운팅 라인과 실제로 교차하는지 판정."""
        lx1, ly1, lx2, ly2 = line

        seg_xmin, seg_xmax = (p1[0], p2[0]) if p1[0] <= p2[0] else (p2[0], p1[0])
        line_xmin, line_xmax = (lx1, lx2) if lx1 <= lx2 else (lx2, lx1)
        if seg_xmax < line_xmin or seg_xmin > line_xmax:
            return False

        return self._segments_intersect(p1, p2, (lx1, ly1), (lx2, ly2))


    def _segments_intersect(
        self,
        a: Point,
        b: Point,
        c: Point,
        d: Point,
    ) -> bool:
        """2D 선분 a-b 와 c-d 의 엄밀한 교차 판정."""
        def ccw(p: Point, q: Point, r: Point) -> int:
            return (r[1] - p[1]) * (q[0] - p[0]) - (q[1] - p[1]) * (r[0] - p[0])

        d1, d2 = ccw(c, d, a), ccw(c, d, b)
        d3, d4 = ccw(a, b, c), ccw(a, b, d)
        return (
            ((d1 > 0 and d2 < 0) or (d1 < 0 and d2 > 0))
            and ((d3 > 0 and d4 < 0) or (d3 < 0 and d4 > 0))
        )


    def get_counts(self) -> Tuple[int, int]:
        """현재 카운트 값(상향, 하향)을 반환합니다."""
        return len(self.counted_up), len(self.counted_down)
