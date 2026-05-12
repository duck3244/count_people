import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { ApiError, api } from '@/api/client';
import { Button } from '@/components/Button';
import { Dropzone } from '@/components/Dropzone';

export function Home() {
  const navigate = useNavigate();
  const [activeId, setActiveId] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api.active().then((a) => setActiveId(a.job_id)).catch(() => {});
  }, []);

  async function upload(file: File) {
    setError(null);
    setBusy(true);
    try {
      const { job_id } = await api.uploadJob(file);
      navigate(`/jobs/${job_id}`);
    } catch (e) {
      if (e instanceof ApiError && e.status === 409) {
        const a = await api.active().catch(() => null);
        setActiveId(a?.job_id ?? null);
        setError(e.message);
      } else {
        setError(e instanceof Error ? e.message : String(e));
      }
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="mx-auto max-w-2xl space-y-6 p-8">
      <header className="space-y-1">
        <h1 className="text-2xl font-bold">People Counter</h1>
        <p className="text-sm text-slate-400">
          비디오를 업로드하면 YOLOv8 + SORT로 사람 수를 세어 결과 영상과 함께 보여줍니다.
        </p>
      </header>

      {activeId && (
        <div className="flex items-center justify-between rounded-xl bg-amber-900/30 p-4 text-sm ring-1 ring-amber-700/40">
          <span>처리 중인 작업이 있습니다.</span>
          <Button variant="ghost" onClick={() => navigate(`/jobs/${activeId}`)}>
            보러가기
          </Button>
        </div>
      )}

      <Dropzone onFile={upload} disabled={busy || !!activeId} />

      {error && (
        <div className="rounded-lg bg-rose-900/40 p-3 text-sm text-rose-200 ring-1 ring-rose-700/40">
          {error}
        </div>
      )}

      <p className="text-xs text-slate-500">
        지원: mp4 / mov / m4v / avi / mkv / webm · 최대 200MB · 한 번에 1개 작업.
      </p>
    </div>
  );
}
