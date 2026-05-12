import pytest

from counter import PeopleCounter


@pytest.fixture
def counter():
    return PeopleCounter()


def test_clear_crossing_returns_true(counter):
    # 수평 라인 y=100, x=[0,200], 선분이 위에서 아래로 통과
    assert counter._segment_crosses((50, 80), (50, 120), [0, 100, 200, 100])


def test_no_crossing_when_parallel_above(counter):
    # 라인 위쪽에서만 움직이는 경우
    assert not counter._segment_crosses((50, 50), (50, 90), [0, 100, 200, 100])


def test_no_crossing_outside_x_range(counter):
    # 라인의 x 범위 밖에서만 움직이는 경우
    assert not counter._segment_crosses((300, 80), (300, 120), [0, 100, 200, 100])


def test_diagonal_crossing(counter):
    # 대각선 이동이 라인을 가로지르는 경우
    assert counter._segment_crosses((10, 50), (190, 150), [0, 100, 200, 100])


def test_zero_length_movement_no_cross(counter):
    # 정지(같은 점)는 교차로 보지 않음
    assert not counter._segment_crosses((50, 100), (50, 100), [0, 100, 200, 100])
