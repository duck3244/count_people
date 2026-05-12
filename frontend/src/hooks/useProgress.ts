import { useEffect, useRef, useState } from 'react';
import { api } from '@/api/client';
import type { JobView, ProgressMessage } from '@/types';

type Status = JobView['status'];

interface State {
  view: JobView | null;
  transport: 'ws' | 'polling' | 'idle';
  error: string | null;
}

const TERMINAL: Status[] = ['completed', 'failed', 'cancelled'];

function wsUrl(jobId: string) {
  const proto = location.protocol === 'https:' ? 'wss:' : 'ws:';
  return `${proto}//${location.host}/api/jobs/${jobId}/progress`;
}

function fromMessage(m: ProgressMessage, prev: JobView | null): JobView {
  return {
    id: m.job_id,
    status: m.status,
    progress:
      m.total_frames && m.total_frames > 0 ? m.frame / m.total_frames : -1,
    frame: m.frame,
    total_frames: m.total_frames,
    count_up: m.count_up,
    count_down: m.count_down,
    fps: m.fps,
    elapsed_sec: m.elapsed_sec,
    error: m.error,
    created_at: prev?.created_at ?? Date.now() / 1000,
    finished_at:
      m.type === 'done' || m.type === 'error'
        ? Date.now() / 1000
        : (prev?.finished_at ?? null),
    has_video: m.status === 'completed',
  };
}

/**
 * WS 우선 + 실패 시 1초 폴링 자동 폴백.
 */
export function useProgress(jobId: string | null) {
  const [state, setState] = useState<State>({
    view: null,
    transport: 'idle',
    error: null,
  });
  const stoppedRef = useRef(false);

  useEffect(() => {
    if (!jobId) return;
    stoppedRef.current = false;
    let ws: WebSocket | null = null;
    let pollTimer: number | null = null;

    const stopAll = () => {
      stoppedRef.current = true;
      if (ws) {
        ws.close();
        ws = null;
      }
      if (pollTimer !== null) {
        window.clearTimeout(pollTimer);
        pollTimer = null;
      }
    };

    const startPolling = () => {
      setState((s) => ({ ...s, transport: 'polling' }));
      const tick = async () => {
        if (stoppedRef.current) return;
        try {
          const view = await api.getJob(jobId);
          setState((s) => ({ ...s, view, error: null }));
          if (TERMINAL.includes(view.status)) return;
        } catch (e) {
          const msg = e instanceof Error ? e.message : String(e);
          setState((s) => ({ ...s, error: msg }));
        }
        pollTimer = window.setTimeout(tick, 1000);
      };
      tick();
    };

    const startWs = () => {
      try {
        ws = new WebSocket(wsUrl(jobId));
      } catch {
        startPolling();
        return;
      }

      ws.onopen = () => {
        setState((s) => ({ ...s, transport: 'ws', error: null }));
      };
      ws.onmessage = (e) => {
        try {
          const msg = JSON.parse(e.data) as ProgressMessage;
          setState((s) => ({
            ...s,
            view: fromMessage(msg, s.view),
            error: msg.error ?? null,
          }));
        } catch {
          /* ignore */
        }
      };
      ws.onerror = () => {
        if (!stoppedRef.current) startPolling();
      };
      ws.onclose = (ev) => {
        if (stoppedRef.current) return;
        // 정상 종료면 종단 메시지를 이미 받은 것으로 간주
        if (state.view && TERMINAL.includes(state.view.status)) return;
        if (ev.code !== 1000) startPolling();
      };
    };

    startWs();
    return stopAll;
    // jobId 변경 시에만 재구독
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [jobId]);

  return state;
}
