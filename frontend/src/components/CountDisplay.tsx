interface Props {
  up: number;
  down: number;
}

export function CountDisplay({ up, down }: Props) {
  return (
    <div className="grid grid-cols-2 gap-3">
      <div className="rounded-xl bg-emerald-900/30 p-4 text-center ring-1 ring-emerald-700/40">
        <div className="text-xs uppercase tracking-wider text-emerald-300">Up</div>
        <div className="mt-1 text-3xl font-bold text-emerald-200 tabular-nums">{up}</div>
      </div>
      <div className="rounded-xl bg-rose-900/30 p-4 text-center ring-1 ring-rose-700/40">
        <div className="text-xs uppercase tracking-wider text-rose-300">Down</div>
        <div className="mt-1 text-3xl font-bold text-rose-200 tabular-nums">{down}</div>
      </div>
    </div>
  );
}
