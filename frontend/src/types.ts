export type JobStatus =
  | 'queued'
  | 'running'
  | 'completed'
  | 'failed'
  | 'cancelled';

export interface JobView {
  id: string;
  status: JobStatus;
  progress: number; // 0..1, -1: 알 수 없음
  frame: number;
  total_frames: number | null;
  count_up: number;
  count_down: number;
  fps: number;
  elapsed_sec: number;
  error: string | null;
  created_at: number;
  finished_at: number | null;
  has_video: boolean;
}

export interface ActiveJobView {
  job_id: string | null;
}

export type ProgressMessage = {
  type: 'progress' | 'status' | 'done' | 'error';
  job_id: string;
  status: JobStatus;
  frame: number;
  total_frames: number | null;
  count_up: number;
  count_down: number;
  fps: number;
  elapsed_sec: number;
  error: string | null;
};
