# Architecture

People Counter는 YOLOv8 객체 감지와 SORT 추적을 기반으로 비디오에서 사람의 상향/하향 이동을 카운팅하는 시스템입니다. CLI 단독 실행도 지원하지만, 주된 사용 경로는 **React + Vite 프론트엔드 + FastAPI 백엔드** 의 단일 사용자(single-user) 처리 워크플로입니다.

---

## 1. 시스템 개요

```
┌──────────────────────────┐         HTTP (REST)         ┌────────────────────────────────────────────┐
│                          │ ──────────────────────────▶ │                                            │
│   Frontend (Vite + React) │                              │   Backend (FastAPI + Uvicorn)              │
│   - Dropzone 업로드      │ ◀── WebSocket: progress ──── │   - REST: /api/jobs, /api/jobs/{id}, ...   │
│   - 진행률/카운트 표시   │                              │   - WS:  /api/jobs/{id}/progress           │
│   - 결과 영상 재생/다운  │ ◀──── Range: 비디오 스트림 ── │   - Single-Job 상태 머신                   │
│                          │                              │   - Worker Thread (ThreadPoolExecutor)      │
└──────────────────────────┘                              └──────────────────┬─────────────────────────┘
                                                                             │
                                                                             ▼
                                                          ┌──────────────────────────────────┐
                                                          │   Processing Pipeline (sync)     │
                                                          │   detector → SORT → counter →    │
                                                          │   visualizer → VideoWriter       │
                                                          └────────────┬─────────────────────┘
                                                                       │
                                                            ┌──────────┴──────────┐
                                                            ▼                     ▼
                                                  YOLOv8 (Ultralytics)     ffmpeg (transcode → H.264)
                                                       on CPU/CUDA              (선택)
                                                                       │
                                                                       ▼
                                                       storage/{job_id}/{input,output}.mp4
```

핵심 책임은 다음과 같이 분리됩니다.

| 레이어 | 위치 | 책임 |
|---|---|---|
| Presentation | `frontend/src/` | 업로드 UX, 진행률/카운트 표시, 결과 다운로드 |
| Web API | `backend/app/api/` | REST + WebSocket, 입력 검증, Range 스트리밍 |
| Job 오케스트레이션 | `backend/app/jobs.py`, `runner.py` | Job 라이프사이클, 단일 활성 보장, pub/sub |
| Processing Pipeline | `backend/app/pipeline.py` | 프레임 루프, 진행 콜백, 취소 협조 |
| Domain (Computer Vision) | `backend/{detector,counter,visualizer,helper,sort}.py` | YOLO 검출, SORT 추적, 라인 교차 + 방향 판정, 시각화 |
| Configuration | `backend/config.py`, `app/settings.py` | 정규화 좌표, 환경 변수 기반 설정 |

---

## 2. 디렉터리 구조

```
count_people/
├── backend/
│   ├── app/                          # 웹 애플리케이션 레이어 (FastAPI)
│   │   ├── main.py                   # FastAPI 엔트리포인트 + lifespan(모델 워밍업)
│   │   ├── settings.py               # 환경 변수 기반 설정 (storage, CORS, 모델 경로 등)
│   │   ├── schemas.py                # Pydantic DTO (JobView, ProgressMessage)
│   │   ├── jobs.py                   # SingleJobStore: 단일 활성 Job + pub/sub
│   │   ├── runner.py                 # 워커 스레드 + 진행 throttle + 트랜스코딩 트리거
│   │   ├── pipeline.py               # run_pipeline() — CLI/Web 공용 처리 루프
│   │   ├── transcode.py              # ffmpeg를 호출해 mp4v → H.264 변환
│   │   └── api/
│   │       ├── jobs.py               # REST 라우터 (/api/jobs)
│   │       └── ws.py                 # WebSocket 라우터 (/api/jobs/{id}/progress)
│   ├── detector.py                   # YOLO 객체 감지기
│   ├── counter.py                    # 사람 카운팅 (라인 교차 + 방향)
│   ├── visualizer.py                 # 시각화 (박스/라인/카운트 오버레이)
│   ├── helper.py                     # cv2.VideoWriter 팩토리
│   ├── sort.py                       # SORT 추적 알고리즘 (외부 구현)
│   ├── config.py                     # 정규화 좌표, 임계값, 색상 등 상수
│   ├── main.py                       # CLI 진입점 — run_pipeline 재사용
│   ├── requirements.txt
│   ├── yolov8n.pt                    # YOLOv8 nano 가중치
│   ├── sample.mp4 / output.mp4
│   ├── tests/                        # pytest (pipeline / iou / segment / writer)
│   └── storage/{job_id}/             # 런타임 산출물 (input.mp4, output.mp4)
├── frontend/
│   └── src/
│       ├── main.tsx, App.tsx
│       ├── api/client.ts             # fetch 래퍼 + ApiError
│       ├── hooks/useProgress.ts      # WS 우선, 실패 시 1초 폴링 폴백
│       ├── pages/Home.tsx, JobView.tsx
│       ├── components/{Dropzone,ProgressBar,CountDisplay,VideoPlayer,Button}.tsx
│       └── types.ts                  # 백엔드 schemas.py 와 미러링
└── docs/                             # (이 디렉터리)
```

---

## 3. 백엔드 — 모듈 책임

### 3.1 `app/main.py` — FastAPI 부트스트랩
- `lifespan` 컨텍스트에서 **YOLO 모델을 단 한 번 로드**하고 더미 프레임으로 워밍업.
- `app.state.detector`, `app.state.store` 에 싱글톤 인스턴스 게시.
- CORS 허용(dev: Vite `:5173`), `jobs` REST + WS 라우터 마운트.

### 3.2 `app/settings.py` — 환경 변수 설정
- `PC_STORAGE_DIR`, `PC_MAX_UPLOAD_MB`, `PC_TRANSCODE_H264`, `PC_CORS_ORIGINS`, `PC_PROGRESS_HZ`, `PC_MODEL_PATH` 등을 동결된 dataclass로 노출.

### 3.3 `app/jobs.py` — Job 상태 머신
- `Job` dataclass — id/디렉터리/상태/누적 카운트/취소 이벤트 보유.
- `SingleJobStore` — **활성 Job 1개만** 허용 (충돌 시 `ConflictError`/HTTP 409).
  - `create()` 호출 시 이전 storage 디렉터리 자동 정리.
  - `subscribe()/publish()/unsubscribe()` 로 진행 이벤트 pub/sub (`asyncio.Queue`, maxsize=64, 가득 차면 oldest drop).
  - `cancel()` 은 `threading.Event` 를 set — 파이프라인이 다음 프레임에서 협조적으로 종료.

### 3.4 `app/pipeline.py` — 공용 처리 파이프라인
- CLI 와 웹 서버가 **동일한 `run_pipeline()`** 을 호출.
- 책임:
  1. `cv2.VideoCapture` / `cv2.VideoWriter` 생성.
  2. 영상 해상도에 맞춰 정규화된 카운팅 라인을 픽셀 좌표로 변환.
  3. 프레임 루프: `detector.detect` → `counter.update` → `visualizer.draw_*` → `writer.write`.
  4. 매 프레임 `on_progress(ProgressEvent)` 콜백 (스로틀은 호출자가 관리).
  5. `cancel_event.is_set()` 또는 (`display=True` 시) `q` 키로 협조적 종료.

### 3.5 `app/runner.py` — 워커 + 스로틀 + 트랜스코딩
- `ThreadPoolExecutor(max_workers=1)` — YOLO 모델 GPU 직렬화 보장.
- 진행 콜백은 `progress_throttle_hz` 기반 시간 throttle (기본 10 Hz).
- 정상 완료 시 ffmpeg 로 H.264 + faststart 트랜스코딩(Safari 호환).
- 실패/취소 시 적절한 종료 메시지 publish.

### 3.6 `app/api/jobs.py` — REST 라우터
| 메서드 | 경로 | 설명 |
|---|---|---|
| GET | `/api/health` | 헬스 체크 |
| GET | `/api/jobs/active` | 현재 활성 Job ID |
| POST | `/api/jobs` | 멀티파트 업로드 → Job 생성 (409 if busy, 413 if oversized, 415 if unsupported) |
| GET | `/api/jobs/{id}` | Job 상태 스냅샷 |
| DELETE | `/api/jobs/{id}` | 취소 요청 |
| GET | `/api/jobs/{id}/result` | 카운트 결과 JSON (완료 시) |
| GET | `/api/jobs/{id}/video` | 결과 영상 + **HTTP Range** 스트리밍 |

업로드 시 1 MB 청크 + 누적 사이즈 검증, `cv2.VideoCapture.isOpened()` 로 컨테이너 유효성 1차 확인.

### 3.7 `app/api/ws.py` — WebSocket 진행 채널
- 연결 시 현재 상태를 한 번 송신(늦은 구독자 대비).
- `store.subscribe()` 큐에서 메시지를 받아 그대로 forward.
- `done`/`error` 메시지를 만나면 정상 종료.

### 3.8 `detector.py` — YOLO 래퍼
- `ultralytics.YOLO` 로드 후 `cuda` 가용 시 자동 디바이스 선택.
- `target_class` (기본 `"person"`) 의 클래스 인덱스를 미리 계산 — 모델 단계에서 필터링해 후처리 최소화.
- 반환 형식: `(시각화용 박스 리스트, SORT용 [N,5] 검출 배열)`.

### 3.9 `counter.py` — 사람 카운팅
- SORT 트래커 (`sort.Sort`) 를 보유, ID별 직전 중심점 캐시 유지.
- **선분 교차 + 이동 방향(dy 부호)** 두 조건이 동시에 성립할 때만 카운트.
- 동일 ID는 라인당 1회만 집계 (`counted_up`/`counted_down` set).
- 사라진 ID의 히스토리는 매 프레임 정리.

### 3.10 `visualizer.py` — 시각화
- 감지 박스, 추적 ID, 카운팅 라인(활성화 시 색 변경), 누적 카운트 텍스트를 그림 위에 합성.

### 3.11 `config.py` — 상수와 정규화 좌표
- 카운팅 라인을 **0.0~1.0 정규화** 로 저장 → `denormalize_line(width, height)` 로 어떤 해상도에도 비례 적용.

---

## 4. 프론트엔드 — 모듈 책임

### 4.1 라우팅 (`App.tsx`)
- `/` → `Home` : 활성 Job 표시 + 드롭존 업로드.
- `/jobs/:jobId` → `JobView` : 진행률, 카운트, 결과 영상, 다운로드(MP4/CSV/JSON).

### 4.2 API 클라이언트 (`api/client.ts`)
- `fetch` 래퍼 + `ApiError(status, message, detail)`.
- 모든 호출은 동일 origin으로 — Vite dev 서버가 `/api` 와 WS 를 `127.0.0.1:8000` 으로 프록시.

### 4.3 진행 채널 훅 (`hooks/useProgress.ts`)
- WebSocket(`/api/jobs/{id}/progress`) 우선 구독.
- `onerror` / 비정상 `onclose` 시 **1초 폴링 자동 폴백** (`/api/jobs/{id}`).
- 메시지를 `JobView` 형태로 머지(`fromMessage`) — UI 컴포넌트는 transport 차이를 모름.

### 4.4 페이지
- `Home` — 활성 Job 배지, Dropzone, 409 처리 분기.
- `JobView` — 상태 배지, `ProgressBar`, `CountDisplay`, 취소/새 작업 버튼, `VideoPlayer`(`<video controls>` + Range로 부분 로딩).

---

## 5. 핵심 시나리오 (요청 흐름)

### 5.1 새 비디오 처리

1. 사용자가 Dropzone에 파일 드롭 → `POST /api/jobs` (multipart).
2. 서버: 확장자/사이즈/컨테이너 검증 → `SingleJobStore.create()` → 입력 저장 → `asyncio.create_task(run_job)`.
3. 응답 즉시 반환(`job_id`). 클라이언트가 `/jobs/:jobId` 로 이동.
4. 클라이언트가 WS 연결 (`/api/jobs/{id}/progress`).
5. 워커 스레드에서 `run_pipeline()` 이 프레임마다 `on_progress(ProgressEvent)` 호출.
6. `runner` 가 throttle 후 `ProgressMessage` 를 `store.publish` → 모든 WS 구독자에게 broadcast.
7. 종료 시: 성공이면 H.264 트랜스코딩 → `done` 메시지 → WS 종료 → 클라이언트가 `/api/jobs/{id}/video` 재생.

### 5.2 취소

1. 사용자가 취소 클릭 → `DELETE /api/jobs/{id}`.
2. 서버는 `job.cancel_event.set()`.
3. `run_pipeline` 이 다음 루프 진입에서 `interrupted=True` 로 종료 → `cancelled` 상태로 마무리, 영상은 부분 저장(트랜스코딩 생략).

### 5.3 단일 활성 보장 / 충돌

- `SingleJobStore.create()` 가 `queued|running` 상태의 다른 Job 존재 시 `ConflictError` → `409`.
- 클라이언트는 `/api/jobs/active` 로 활성 Job ID를 조회해 사용자를 그 페이지로 안내.

### 5.4 CLI 단독 실행

- `python backend/main.py --input ... --output ... [--no-display] [--results out.json]`.
- 동일한 `run_pipeline` 을 호출하므로 카운팅 로직과 결과는 서버 경로와 동일.

---

## 6. 동시성 모델

- **이벤트 루프 (asyncio):** REST/WS 핸들러, 클라이언트 큐 broadcast.
- **워커 스레드 (ThreadPoolExecutor, max_workers=1):** 무거운 CV 파이프라인. 모델 1개 → GPU 직렬화.
- **취소:** `threading.Event` — 스레드/이벤트 루프 간 안전한 신호 전달.
- **Pub/Sub:** `asyncio.Queue` per 구독자, 워커 스레드에서는 `put_nowait` 만 사용 (느린 구독자는 oldest drop).
- **진행 throttle:** 시간 기반(`PC_PROGRESS_HZ` 기본 10 Hz) → 30+ FPS 처리 시에도 네트워크/UI 부하 일정.

---

## 7. 영속화 & 산출물

- 모든 산출물은 `backend/storage/{job_id}/` 아래:
  - `input.mp4` — 업로드된 원본
  - `output_raw.mp4` — mp4v 임시 결과(트랜스코딩 후 삭제)
  - `output.mp4` — 최종 H.264 결과 (브라우저 호환)
- 새 Job 시작 시 이전 디렉터리들은 일괄 정리 → 디스크 누적 방지.
- DB 없음. 모든 Job 상태는 인메모리(`SingleJobStore._jobs`) — 서버 재시작 시 초기화.

---

## 8. 보안 & 견고성 노트

- 확장자 화이트리스트 + 업로드 청크 누적 사이즈 한도(`PC_MAX_UPLOAD_MB`, 기본 200MB).
- `cv2.VideoCapture` 1차 검증 — 헤더만 위조된 파일은 415로 차단.
- 비디오 스트리밍은 RFC 7233 Range 응답 — 큰 파일도 메모리 누적 없이 부분 로드.
- CORS 는 환경 변수로 화이트리스트.
- WebSocket 끊김 감지를 위해 reader 태스크가 클라이언트 메시지를 단순 소비.

---

## 9. 외부 의존성

- **YOLOv8 / Ultralytics** — 객체 검출.
- **SORT (filterpy)** — Kalman + Hungarian 기반 추적.
- **OpenCV** — 비디오 I/O, 시각화, 라인/박스 드로잉.
- **PyTorch (선택적 CUDA)** — YOLO 추론 백엔드.
- **FastAPI + Uvicorn + python-multipart + Pydantic + websockets** — 웹 레이어.
- **ffmpeg** (시스템 실행 파일) — H.264 트랜스코딩(선택). 미설치 시 mp4v 원본 사용.
- **React 18 + react-router-dom + Vite + Tailwind** — 프론트엔드.

---

## 10. 확장 가능성 / 한계

- **단일 사용자 가정**: `SingleJobStore` 가 활성 Job 1개로 제한 → 멀티 테넌시 적용 시 `JobStore` 추상화 + 외부 큐(Redis/Celery) 필요.
- **상태 휘발성**: 재시작 시 진행 중 Job 손실. 영속 DB(SQLite/Postgres)와 산출물 메타데이터 분리 시 회복 가능.
- **모델 1개 GPU 직렬화**: 멀티 GPU 또는 배치 추론으로 throughput 확장 가능.
- **카운팅 라인 정규화**: 다중 라인/ROI/지오메트리 인터랙티브 편집은 미지원 (config.py 정규화 좌표 수동 편집).
