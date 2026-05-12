import type { ActiveJobView, JobView } from '@/types';

export class ApiError extends Error {
  constructor(
    public status: number,
    message: string,
    public detail?: unknown,
  ) {
    super(message);
  }
}

async function asJson<T>(res: Response): Promise<T> {
  const text = await res.text();
  const data = text ? (JSON.parse(text) as unknown) : undefined;
  if (!res.ok) {
    const detail =
      (data as { detail?: unknown })?.detail ?? res.statusText;
    throw new ApiError(
      res.status,
      typeof detail === 'string' ? detail : res.statusText,
      detail,
    );
  }
  return data as T;
}

export const api = {
  health: () => fetch('/api/health').then(asJson<{ ok: boolean }>),

  active: () => fetch('/api/jobs/active').then(asJson<ActiveJobView>),

  uploadJob: async (file: File, signal?: AbortSignal) => {
    const fd = new FormData();
    fd.append('file', file);
    const res = await fetch('/api/jobs', {
      method: 'POST',
      body: fd,
      signal,
    });
    return asJson<{ job_id: string }>(res);
  },

  getJob: (jobId: string) =>
    fetch(`/api/jobs/${jobId}`).then(asJson<JobView>),

  cancelJob: (jobId: string) =>
    fetch(`/api/jobs/${jobId}`, { method: 'DELETE' }).then(
      asJson<{ job_id: string; cancelled: boolean }>,
    ),

  getResult: (jobId: string) =>
    fetch(`/api/jobs/${jobId}/result`).then(
      asJson<{
        job_id: string;
        frames: number;
        count_up: number;
        count_down: number;
        fps: number;
        elapsed_sec: number;
      }>,
    ),

  videoUrl: (jobId: string) => `/api/jobs/${jobId}/video`,

  resultJsonUrl: (jobId: string) => `/api/jobs/${jobId}/result`,
};
