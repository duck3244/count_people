import numpy as np
import pytest

from sort import iou_batch


def test_identical_boxes_iou_one():
    bb = np.array([[0.0, 0.0, 10.0, 10.0]])
    iou = iou_batch(bb, bb)
    assert iou.shape == (1, 1)
    assert iou[0, 0] == pytest.approx(1.0)


def test_disjoint_boxes_iou_zero():
    a = np.array([[0.0, 0.0, 5.0, 5.0]])
    b = np.array([[10.0, 10.0, 20.0, 20.0]])
    iou = iou_batch(a, b)
    assert iou[0, 0] == pytest.approx(0.0)


def test_half_overlap():
    # 두 박스가 정확히 절반씩 겹침: union=1.5*A, intersection=0.5*A → IoU=1/3
    a = np.array([[0.0, 0.0, 10.0, 10.0]])
    b = np.array([[5.0, 0.0, 15.0, 10.0]])
    iou = iou_batch(a, b)
    assert iou[0, 0] == pytest.approx(1.0 / 3.0)


def test_batch_shape_and_values():
    a = np.array([[0.0, 0.0, 10.0, 10.0],
                  [20.0, 20.0, 30.0, 30.0]])
    b = np.array([[0.0, 0.0, 10.0, 10.0],
                  [25.0, 25.0, 35.0, 35.0],
                  [100.0, 100.0, 110.0, 110.0]])
    iou = iou_batch(a, b)
    assert iou.shape == (2, 3)
    assert iou[0, 0] == pytest.approx(1.0)
    assert iou[0, 2] == pytest.approx(0.0)
    assert iou[1, 0] == pytest.approx(0.0)
    # (20,20,30,30) ∩ (25,25,35,35) = 5×5=25, union=200-25=175 → 1/7
    assert iou[1, 1] == pytest.approx(25.0 / 175.0)
