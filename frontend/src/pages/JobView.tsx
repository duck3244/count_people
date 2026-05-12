import { useMemo } from 'react';
import { Link, useNavigate, useParams } from 'react-router-dom';
import { api } from '@/api/client';
import { Button } from '@/components/Button';
import { CountDisplay } from '@/components/CountDisplay';
import { ProgressBar } from '@/components/ProgressBar';
import { VideoPlayer } from '@/components/VideoPlayer';
import { useProgress } from '@/hooks/useProgress';

export function JobView() {
  const { jobId } = useParams<{ jobId: string }>();
  const navigate = useNavigate();
  const { view, transport, error } = useProgress(jobId ?? null);

  const isActive = view?.status === 'running' || view?.status === 'queued';
  const isDone = view?.status === 'completed';
  const videoSrc = useMemo(
    () => (view?.has_video && jobId ? api.videoUrl(jobId) : null),
    [view?.has_video, jobId],
  );

  if (!jobId) return <div className="p-8">잘못된 경로입니다.</div>;

  async function cancel() {
    if (!jobId) return;
    if (!confirm('정말 취소하시겠습니까?')) return;
    await api.cancelJob(jobId).catch(() => {});
  }

  function downloadCsv() {
    if (!view) return;
    const rows = [
      ['count_up', 'count_down', 'frames', 'fps', 'elapsed_sec'],
      [view.count_up, view.count_down, view.frame, view.fps.toFixed(2), view.elapsed_sec.toFixed(3)],
    ];
    const csv = rows.map((r) => r.join(',')).join('\n');
    const url = URL.createObjectURL(new Blob([csv], { type: 'text/csv' }));
    const a = document.createElement('a');
    a.href = url;
    a.download = `people_count_${jobId}.csv`;
    a.click();
    URL.revokeObjectURL(url);
  }

  return (
    <div className="mx-auto max-w-3xl space-y-6 p-8">
      <header className="flex items-center justify-between">
        <div className="space-y-1">
          <Link to="/" className="text-xs text-slate-400 hover:text-slate-200">
            ← 새 작업
          </Link>
          <h1 className="text-xl font-bold">작업 {jobId}</h1>
        </div>
        <div className="text-right text-xs text-slate-500">
          채널: {transport}
        </div>
      </header>

      {error && (
        <div className="rounded-lg bg-rose-900/40 p-3 text-sm text-rose-200 ring-1 ring-rose-700/40">
          {error}
        </div>
      )}

      {!view ? (
        <div className="text-slate-400">연결 중...</div>
      ) : (
        <div className="space-y-4">
          <div className="flex items-center gap-2 text-sm">
            <span
              className={[
                'rounded-full px-2 py-0.5 text-xs font-medium',
                view.status === 'completed' && 'bg-emerald-900/50 text-emerald-200',
                view.status === 'running' && 'bg-cyan-900/50 text-cyan-200',
                view.status === 'queued' && 'bg-slate-800 text-slate-300',
                view.status === 'failed' && 'bg-rose-900/50 text-rose-200',
                view.status === 'cancelled' && 'bg-amber-900/50 text-amber-200',
              ]
                .filter(Boolean)
                .join(' ')}
            >
              {view.status}
            </span>
            <span className="text-slate-400">
              {view.frame}{view.total_frames ? ` / ${view.total_frames}` : ''} 프레임 ·
              {' '}{view.fps.toFixed(1)} FPS · {view.elapsed_sec.toFixed(1)}s
            </span>
          </div>

          <ProgressBar progress={view.progress} />
          <CountDisplay up={view.count_up} down={view.count_down} />

          <div className="flex gap-2">
            {isActive && (
              <Button variant="danger" onClick={cancel}>
                취소
              </Button>
            )}
            {(view.status === 'completed' ||
              view.status === 'failed' ||
              view.status === 'cancelled') && (
              <Button onClick={() => navigate('/')}>새 영상 처리</Button>
            )}
            {isDone && (
              <>
                <Button variant="ghost" onClick={downloadCsv}>
                  CSV 다운로드
                </Button>
                <a
                  className="rounded-lg bg-slate-800 px-4 py-2 text-sm font-medium hover:bg-slate-700"
                  href={api.resultJsonUrl(jobId)}
                  download={`people_count_${jobId}.json`}
                >
                  JSON 다운로드
                </a>
                {videoSrc && (
                  <a
                    className="rounded-lg bg-slate-800 px-4 py-2 text-sm font-medium hover:bg-slate-700"
                    href={videoSrc}
                    download={`people_count_${jobId}.mp4`}
                  >
                    MP4 다운로드
                  </a>
                )}
              </>
            )}
          </div>

          {videoSrc && (
            <div className="pt-4">
              <VideoPlayer src={videoSrc} />
            </div>
          )}
        </div>
      )}
    </div>
  );
}
