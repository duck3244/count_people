"""run_pipeline 호출 + 결과 검증."""

from pathlib import Path

import pytest

from app.pipeline import run_pipeline


SAMPLE = Path(__file__).resolve().parents[1] / "sample.mp4"


@pytest.mark.skipif(not SAMPLE.exists(), reason="sample.mp4 missing")
def test_pipeline_smoke(tmp_path):
    out = tmp_path / "out.mp4"
    progress_calls = []
    result = run_pipeline(
        str(SAMPLE),
        str(out),
        on_progress=lambda ev: progress_calls.append(ev.frame),
    )
    assert result.frames > 0
    assert out.exists() and out.stat().st_size > 0
    assert result.count_up >= 0 and result.count_down >= 0
    assert progress_calls and progress_calls[-1] == result.frames
    # sample.mp4 회귀 가드 (현재 결과)
    assert (result.count_up, result.count_down) == (1, 3)
