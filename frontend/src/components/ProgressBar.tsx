interface Props {
  progress: number; // 0..1, -1 알 수 없음
  label?: string;
}

export function ProgressBar({ progress, label }: Props) {
  const pct = progress >= 0 ? Math.round(progress * 100) : null;
  return (
    <div className="space-y-1">
      <div className="flex justify-between text-xs text-slate-400">
        <span>{label ?? '진행률'}</span>
        <span>{pct === null ? '...' : `${pct}%`}</span>
      </div>
      <div className="h-2 w-full overflow-hidden rounded-full bg-slate-800">
        {pct === null ? (
          <div className="h-full w-1/3 animate-pulse bg-accent/60" />
        ) : (
          <div
            className="h-full bg-accent transition-[width]"
            style={{ width: `${pct}%` }}
          />
        )}
      </div>
    </div>
  );
}
