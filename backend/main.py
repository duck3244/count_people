"""
PeopleCounter CLI 진입점.

핵심 처리 루프는 app/pipeline.py:run_pipeline() 으로 추출되어
FastAPI 서버(app/main.py)와 공유됩니다.
"""

from __future__ import annotations

import argparse
import csv
import json
import logging
import sys
from pathlib import Path
from typing import Optional

from tqdm import tqdm

import config
from app.pipeline import ProgressEvent, run_pipeline


logger = logging.getLogger("people_counter")


def parse_args(argv: Optional[list[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="YOLOv8 + SORT 기반 사람 카운터 (CLI)",
    )
    parser.add_argument("--input", "-i", default=config.INPUT_VIDEO_PATH)
    parser.add_argument("--output", "-o", default=config.OUTPUT_VIDEO_PATH)
    parser.add_argument("--model", "-m", default=config.MODEL_PATH)
    parser.add_argument("--device", default=None,
                        help="'cuda' | 'cpu' | 'cuda:0' (미지정 시 자동)")
    parser.add_argument("--no-display", action="store_true",
                        help="cv2.imshow 비활성화 (헤드리스)")
    parser.add_argument("--results", default=None,
                        help="결과 저장 경로 (.json | .csv)")
    parser.add_argument("--quiet", action="store_true",
                        help="진행 바 / INFO 로그 억제")
    parser.add_argument("--log-level", default="INFO",
                        choices=["DEBUG", "INFO", "WARNING", "ERROR"])
    return parser.parse_args(argv)


def configure_logging(level: str, quiet: bool) -> None:
    logging.basicConfig(
        level=logging.WARNING if quiet else getattr(logging, level),
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    )


def save_results(path: str, payload: dict) -> None:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    suffix = p.suffix.lower()
    if suffix == ".json":
        p.write_text(json.dumps(payload, ensure_ascii=False, indent=2))
    elif suffix == ".csv":
        with p.open("w", newline="") as f:
            w = csv.writer(f)
            w.writerow(payload.keys())
            w.writerow(payload.values())
    else:
        raise ValueError(f"지원하지 않는 결과 파일 확장자: {suffix} (.json|.csv)")
    logger.info("결과 저장: %s", p)


def main(argv: Optional[list[str]] = None) -> int:
    args = parse_args(argv)
    configure_logging(args.log_level, args.quiet)

    show_window = config.SHOW_WINDOW and not args.no_display

    progress: Optional[tqdm] = None
    if not args.quiet:
        progress = tqdm(unit="frame", dynamic_ncols=True)

    last_total: Optional[int] = None

    def on_progress(ev: ProgressEvent) -> None:
        nonlocal last_total
        if progress is None:
            return
        if last_total is None and ev.total_frames is not None:
            progress.total = ev.total_frames
            last_total = ev.total_frames
        progress.set_postfix(up=ev.count_up, down=ev.count_down)
        progress.n = ev.frame
        progress.refresh()

    logger.info("처리 시작: %s → %s", args.input, args.output)
    if show_window:
        logger.info("종료하려면 미리보기 창에서 'q' 키를 누르세요.")

    try:
        result = run_pipeline(
            args.input,
            args.output,
            model_path=args.model,
            device=args.device,
            on_progress=on_progress,
            display=show_window,
        )
    except RuntimeError as e:
        logger.error("%s", e)
        return 1
    finally:
        if progress is not None:
            progress.close()

    logger.info("처리 완료: frames=%d elapsed=%.2fs (%.1f FPS)",
                result.frames, result.elapsed_sec, result.fps)
    logger.info("최종 카운트 - 상향: %d, 하향: %d",
                result.count_up, result.count_down)

    if args.results:
        save_results(args.results, {
            "input": args.input,
            "output": args.output,
            "model": args.model,
            "device": args.device or "auto",
            "frames": result.frames,
            "elapsed_sec": round(result.elapsed_sec, 3),
            "fps": round(result.fps, 2),
            "count_up": result.count_up,
            "count_down": result.count_down,
            "interrupted": result.interrupted,
        })

    return 130 if result.interrupted else 0


if __name__ == "__main__":
    sys.exit(main())
