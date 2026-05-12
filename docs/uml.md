# UML Diagrams

People Counter 시스템의 주요 UML 다이어그램입니다. 모두 [Mermaid](https://mermaid.js.org/) 문법으로 작성되어 GitHub/GitLab/대부분의 마크다운 렌더러에서 그대로 렌더링됩니다.

---

## 1. Use Case Diagram

사용자가 시스템과 상호작용하는 주요 유스케이스입니다.

```mermaid
flowchart LR
    user(("User<br/>(brower)"))
    cli(("CLI Operator"))

    subgraph Web ["Web Application"]
        UC1["비디오 업로드"]
        UC2["진행률 / 카운트 실시간 보기"]
        UC3["처리 작업 취소"]
        UC4["결과 영상 재생 / 다운로드"]
        UC5["결과 카운트 다운로드<br/>(CSV / JSON)"]
        UC6["활성 작업 확인"]
    end

    subgraph CLIScope ["CLI"]
        UC7["로컬 비디오 처리"]
        UC8["결과 JSON / CSV 저장"]
    end

    user --> UC1
    user --> UC2
    user --> UC3
    user --> UC4
    user --> UC5
    user --> UC6
    cli --> UC7
    cli --> UC8

    UC1 -. include .-> UC6
    UC2 -. extend .-> UC3
    UC4 -. include .-> UC5
```

---

## 2. Component Diagram

배포/실행 단위 컴포넌트 관점입니다.

```mermaid
flowchart TB
    subgraph Browser ["Browser (Frontend)"]
        FE_Pages["pages<br/>(Home, JobView)"]
        FE_Hook["useProgress<br/>(WS + polling fallback)"]
        FE_API["api/client<br/>(fetch wrapper)"]
        FE_Comp["components<br/>(Dropzone, ProgressBar,<br/>CountDisplay, VideoPlayer)"]
    end

    subgraph Server ["Backend (FastAPI + Uvicorn)"]
        API_REST["REST Router<br/>/api/jobs"]
        API_WS["WebSocket Router<br/>/api/jobs/{id}/progress"]
        Store["SingleJobStore<br/>(in-memory + pub/sub)"]
        Runner["Job Runner<br/>(ThreadPoolExecutor,<br/>max_workers=1)"]
        Pipeline["run_pipeline()<br/>frame loop"]
        Detector["ObjectDetector<br/>(YOLOv8)"]
        Counter["PeopleCounter<br/>(SORT + line cross)"]
        Visualizer["Visualizer"]
        Transcode["transcode_to_h264<br/>(ffmpeg subprocess)"]
    end

    subgraph External ["External / System"]
        Disk[("storage/<job_id>/")]
        FFmpeg[["ffmpeg binary"]]
        YOLOWeights[("yolov8n.pt")]
        GPU[["CUDA / CPU"]]
    end

    FE_Pages --> FE_Hook
    FE_Pages --> FE_API
    FE_Pages --> FE_Comp
    FE_Hook -- "WS" --> API_WS
    FE_Hook -- "GET /jobs/{id}" --> API_REST
    FE_API -- "POST /jobs, GET, DELETE" --> API_REST

    API_REST --> Store
    API_REST --> Runner
    API_WS --> Store
    Runner --> Pipeline
    Runner --> Transcode
    Pipeline --> Detector
    Pipeline --> Counter
    Pipeline --> Visualizer
    Pipeline --> Disk
    Transcode --> FFmpeg
    Detector --> YOLOWeights
    Detector --> GPU
    Store -. publish .-> API_WS
```

---

## 3. Class Diagram — 백엔드 도메인 / 애플리케이션

```mermaid
classDiagram
    direction LR

    class Settings {
        +Path storage_dir
        +int max_upload_bytes
        +tuple allowed_extensions
        +bool transcode_to_h264
        +tuple cors_origins
        +float progress_throttle_hz
        +str model_path
        +load() Settings
    }

    class Job {
        +str id
        +Path dir
        +Path input_path
        +Path output_path
        +Path raw_output_path
        +JobStatus status
        +int frame
        +int total_frames
        +int count_up
        +int count_down
        +float fps
        +float elapsed_sec
        +str error
        +float created_at
        +float finished_at
        +Event cancel_event
        +PipelineResult result
        +progress() float
        +to_view() JobView
        +update_from_event(ev) void
    }

    class SingleJobStore {
        -Dict _jobs
        -str _active_id
        -Lock _lock
        -Dict _subscribers
        +Path storage_dir
        +create() Job
        +get(id) Job
        +active() Job
        +mark_running(id) void
        +mark_completed(id, result) void
        +mark_failed(id, err) void
        +cancel(id) void
        +subscribe(id) Queue
        +unsubscribe(id, q) void
        +publish(id, msg) void
    }

    class ConflictError {
    }
    class JobNotFound {
    }

    class ProgressEvent {
        +int frame
        +int total_frames
        +int count_up
        +int count_down
        +float fps
        +float elapsed_sec
        +to_dict() dict
    }

    class PipelineResult {
        +int frames
        +int count_up
        +int count_down
        +float fps
        +float elapsed_sec
        +bool interrupted
        +int width
        +int height
        +float src_fps
        +str output_path
    }

    class run_pipeline {
        <<function>>
        +run_pipeline(args) PipelineResult
    }

    class run_job {
        <<async>>
        +run_job(job, store, detector) Coroutine
    }

    class ObjectDetector {
        +YOLO model
        +str device
        +float confidence_threshold
        +str target_class
        +int target_class_idx
        +detect(frame) tuple
    }

    class PeopleCounter {
        +Sort tracker
        +set counted_up
        +set counted_down
        -dict _prev_centers
        +Line limits_up
        +Line limits_down
        +update(detections) tuple
        +get_counts() tuple
        +reset_counts() void
        -segment_crosses(p1, p2, line) bool
        -segments_intersect(a, b, c, d) bool
    }

    class Visualizer {
        +tuple limits_up
        +tuple limits_down
        +draw_detection_boxes(frame, boxes) frame
        +draw_tracking_boxes(frame, tracks) frame
        +draw_counting_lines(frame, activated) frame
        +draw_count_info(frame, up, down) frame
    }

    class Sort {
        <<external>>
        +update(detections) ndarray
    }

    class FastAPI {
        <<framework>>
    }

    class jobs_router {
        <<router>>
        +create_job(file) JobCreated
        +get_active() ActiveJobView
        +get_job(id) JobView
        +cancel_job(id) dict
        +get_result(id) dict
        +get_video(id) Response
    }

    class ws_router {
        <<router>>
        +progress_ws(id) void
    }

    FastAPI --> jobs_router : include_router
    FastAPI --> ws_router : include_router
    FastAPI --> ObjectDetector : app_state_detector
    FastAPI --> SingleJobStore : app_state_store

    SingleJobStore o-- Job : owns
    Job ..> PipelineResult : holds_optional
    jobs_router ..> SingleJobStore
    jobs_router ..> run_job : create_task
    ws_router ..> SingleJobStore : subscribe_publish
    run_job ..> run_pipeline
    run_job ..> SingleJobStore
    run_job ..> ObjectDetector
    run_pipeline ..> ObjectDetector
    run_pipeline ..> PeopleCounter
    run_pipeline ..> Visualizer
    run_pipeline ..> ProgressEvent : emits
    run_pipeline ..> PipelineResult : returns
    PeopleCounter --> Sort
    Settings <.. FastAPI : reads
    SingleJobStore ..> ConflictError
    SingleJobStore ..> JobNotFound
```

---

## 4. Class Diagram — 프론트엔드

```mermaid
classDiagram
    direction LR

    class App {
        <<component>>
        +routes() void
    }

    class Home {
        <<page>>
        -str activeId
        -bool busy
        -str error
        +upload(file) Promise
    }

    class JobView {
        <<page>>
        -str jobId
        +cancel() Promise
        +downloadCsv() void
    }

    class useProgress {
        <<hook>>
        -State state
        +useProgress(jobId) State
    }

    class api {
        <<module>>
        +health() Promise
        +active() Promise
        +uploadJob(file) Promise
        +getJob(id) Promise
        +cancelJob(id) Promise
        +getResult(id) Promise
        +videoUrl(id) str
        +resultJsonUrl(id) str
    }

    class ApiError {
        +int status
        +any detail
    }

    class Dropzone {
        <<component>>
        +onFile callback
    }
    class ProgressBar {
        <<component>>
        +float progress
    }
    class CountDisplay {
        <<component>>
        +int up
        +int down
    }
    class VideoPlayer {
        <<component>>
        +str src
    }
    class Button {
        <<component>>
        +str variant
    }

    class JobView_DTO {
        <<type>>
        +str id
        +str status
        +float progress
        +int frame
        +int total_frames
        +int count_up
        +int count_down
        +float fps
        +float elapsed_sec
        +str error
        +float created_at
        +float finished_at
        +bool has_video
    }

    class ProgressMessage {
        <<type>>
        +str type
        +str job_id
        +str status
        +int frame
        +int total_frames
        +int count_up
        +int count_down
        +float fps
        +float elapsed_sec
        +str error
    }

    App --> Home
    App --> JobView
    Home --> Dropzone
    Home --> Button
    Home --> api
    JobView --> useProgress
    JobView --> ProgressBar
    JobView --> CountDisplay
    JobView --> VideoPlayer
    JobView --> Button
    JobView --> api
    useProgress --> api
    api ..> ApiError : throws
    api ..> JobView_DTO
    useProgress ..> ProgressMessage
    useProgress ..> JobView_DTO
```

---

## 5. Sequence Diagram — 비디오 업로드 → 처리 → 결과 수신

```mermaid
sequenceDiagram
    autonumber
    actor U as User
    participant FE as Frontend (Home/JobView)
    participant API as REST /api/jobs
    participant WS as WebSocket /api/jobs/{id}/progress
    participant Store as SingleJobStore
    participant Runner as run_job (asyncio task)
    participant Worker as ThreadPool worker
    participant Pipe as run_pipeline
    participant FF as ffmpeg

    U->>FE: 파일 드롭
    FE->>API: POST /api/jobs (multipart)
    API->>Store: create()
    Store-->>API: Job(id=abc)
    API->>API: chunked write to input.mp4
    API->>API: cv2.VideoCapture.isOpened() 검증
    API->>Runner: asyncio.create_task(run_job(job, store, detector))
    API-->>FE: 201 { job_id: "abc" }

    FE->>FE: navigate(/jobs/abc)
    FE->>WS: WebSocket connect
    WS->>Store: subscribe(abc)
    WS-->>FE: status (queued)

    Runner->>Store: mark_running(abc)
    Runner->>Store: publish(status: running)
    Store-->>WS: enqueue
    WS-->>FE: status (running)

    Runner->>Worker: submit(_do_work)
    Worker->>Pipe: run_pipeline(...)

    loop 매 프레임
        Pipe->>Pipe: detect → counter.update → visualize → writer.write
        Pipe->>Runner: on_progress(ev)
        alt throttle (>= 1/Hz)
            Runner->>Store: publish(progress)
            Store-->>WS: enqueue
            WS-->>FE: progress (frame, count_up, count_down, fps)
        end
        Note over Worker,Pipe: cancel_event.is_set() 면 즉시 break
    end

    Pipe-->>Worker: PipelineResult
    alt 정상 완료 + ffmpeg 사용 가능
        Worker->>FF: transcode raw → output.mp4 (H.264)
        FF-->>Worker: ok
    else
        Worker->>Worker: raw → output.mp4 rename
    end
    Worker-->>Runner: PipelineResult

    Runner->>Store: mark_completed(abc, result)
    Runner->>Store: publish(done)
    Store-->>WS: enqueue
    WS-->>FE: done
    WS->>WS: close

    FE->>API: GET /api/jobs/abc/video (Range)
    API-->>FE: 206 Partial Content (video/mp4)
    FE-->>U: 결과 영상 재생 + 카운트 표시
```

---

## 6. Sequence Diagram — 처리 작업 취소

```mermaid
sequenceDiagram
    autonumber
    actor U as User
    participant FE as JobView
    participant API as REST /api/jobs
    participant Store as SingleJobStore
    participant Pipe as run_pipeline (worker thread)
    participant WS as WebSocket

    U->>FE: "취소" 클릭
    FE->>API: DELETE /api/jobs/abc
    API->>Store: cancel(abc)
    Store->>Store: job.cancel_event.set()
    API-->>FE: 202 { cancelled: true }

    loop 다음 프레임 진입 시
        Pipe->>Pipe: cancel_event.is_set()? → True
        Pipe-->>Pipe: break loop, interrupted=True
    end

    Pipe-->>Store: PipelineResult(interrupted=True)
    Store->>Store: mark_completed → status="cancelled"
    Store-->>WS: publish(done, status="cancelled")
    WS-->>FE: done(cancelled)
```

---

## 7. State Diagram — Job 라이프사이클

```mermaid
stateDiagram-v2
    [*] --> queued : create() (POST /api/jobs)

    queued --> running : runner picks up\nmark_running()
    queued --> failed : upload/validate error

    running --> completed : pipeline finished\n(interrupted=False)
    running --> cancelled : pipeline finished\n(interrupted=True)
    running --> failed : exception in worker

    completed --> [*]
    cancelled --> [*]
    failed --> [*]

    note right of running
      cancel_event.set() 는
      다음 프레임에서 협조적 종료
    end note
    note left of completed
      transcode_to_h264 후
      has_video = True
    end note
```

---

## 8. Activity Diagram — 프레임 처리 루프 (`run_pipeline`)

```mermaid
flowchart TD
    Start([Start]) --> OpenCap["cv2.VideoCapture 열기"]
    OpenCap -->|실패| RaiseErr["RuntimeError"]
    OpenCap --> ReadProps["width / height / fps / total_frames 추출"]
    ReadProps --> MakeWriter["VideoWriter 생성"]
    MakeWriter --> ApplyLines["LIMITS_*_NORM → 픽셀 좌표"]
    ApplyLines --> InitDeps["detector / counter / visualizer 준비"]
    InitDeps --> Loop{"프레임 남음?"}

    Loop -- "아니오 (EOF)" --> Finalize
    Loop -- "예" --> CheckCancel{"cancel_event.is_set() ?"}

    CheckCancel -- "예" --> MarkInterrupted["interrupted = True"] --> Finalize
    CheckCancel -- "아니오" --> Read["cap.read()"]

    Read -->|실패| Finalize
    Read --> Detect["detector.detect(frame)"]
    Detect --> Track["counter.update(detections)"]
    Track --> Counts["count_up, count_down 갱신"]
    Counts --> Draw["visualizer.draw_*"]
    Draw --> Write["writer.write(frame)"]
    Write --> Progress{"on_progress 존재 AND frame mod progress_every == 0 ?"}
    Progress -- "예" --> Emit["on_progress(ProgressEvent)"]
    Progress -- "아니오" --> Display
    Emit --> Display{"display = True ?"}
    Display -- "예 (CLI)" --> Show["cv2.imshow + waitKey"]
    Show -->|"'q'"| MarkInterrupted
    Show --> Loop
    Display -- "아니오" --> Loop

    Finalize["cap.release() / writer.release()"] --> ReturnResult["PipelineResult 반환"]
    ReturnResult --> End([End])
```

---

## 9. Deployment Diagram

```mermaid
flowchart TB
    subgraph Dev["개발자 머신 (예: localhost)"]
        subgraph BrowserNode["Browser (User Agent)"]
            FE["Vite Dev Server :5173<br/>(or built static)"]
        end

        subgraph PythonProc["Python Process (uvicorn)"]
            APP["FastAPI App :8000"]
            EXEC["ThreadPoolExecutor (1)"]
            APP --- EXEC
        end

        subgraph FS["File System"]
            STORE[("backend/storage/<job_id>/")]
            WEIGHTS[("backend/yolov8n.pt")]
        end

        GPU[["NVIDIA GPU (선택)"]]
        FFBIN[["ffmpeg (선택)"]]
    end

    FE -- "HTTP / WS (Vite proxy)" --> APP
    APP -- "I/O" --> STORE
    APP -- "load" --> WEIGHTS
    APP -- "CUDA" --> GPU
    EXEC -- "subprocess" --> FFBIN
```

---

## 10. ER-like Data Diagram (인메모리 모델)

영속 DB가 없기 때문에 ERD 대신 **인메모리 객체 관계** 를 표시합니다.

```mermaid
erDiagram
    SingleJobStore ||--o{ Job : "_jobs (dict)"
    SingleJobStore ||--o{ AsyncQueue : "_subscribers (dict[job_id, set])"
    Job ||--o| PipelineResult : "result (optional)"
    Job ||--o{ ProgressEvent : "emitted-during-run"
    Job ||--|| CancelEvent : "owns"

    SingleJobStore {
        string active_id "nullable"
        path   storage_dir
    }
    Job {
        string id PK
        string status "queued|running|completed|failed|cancelled"
        int    frame
        int    total_frames
        int    count_up
        int    count_down
        float  fps
        float  elapsed_sec
        string error "nullable"
        float  created_at
        float  finished_at "nullable"
    }
    PipelineResult {
        int   frames
        int   count_up
        int   count_down
        float fps
        float elapsed_sec
        bool  interrupted
        int   width
        int   height
        float src_fps
        string output_path
    }
    ProgressEvent {
        int   frame
        int   total_frames
        int   count_up
        int   count_down
        float fps
        float elapsed_sec
    }
    AsyncQueue {
        string job_id FK
        int    maxsize
    }
    CancelEvent {
        bool flag
    }
```

---

## 11. Counting 로직 시각 보조 (라인 교차 + 방향)

`PeopleCounter.update` 내부에서 트랙 ID별 직전 중심점과 현재 중심점을 잇는 선분이 카운팅 라인과 **실제 교차**하고, 이동 방향(dy 부호)이 라인의 의도와 일치할 때만 1회 카운트합니다.

```mermaid
flowchart LR
    A["tid 의 이전 중심점 prev"] -->|"세그먼트"| B["tid 의 현재 중심점 cur"]
    B --> Check{"교차 AND 방향 일치 ?"}
    Check -->|"위쪽 라인 + dy<0"| Up["counted_up += tid<br/>activated += 'up'"]
    Check -->|"아래쪽 라인 + dy>0"| Down["counted_down += tid<br/>activated += 'down'"]
    Check -->|"아니오"| Skip["카운트 없음"]
```

> 같은 ID는 라인당 최대 1회만 카운트되며, 라인 근처에 머무르기만 해서는 카운트되지 않습니다.
