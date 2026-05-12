import { useCallback, useRef, useState } from 'react';

interface Props {
  onFile: (file: File) => void;
  accept?: string;
  disabled?: boolean;
}

export function Dropzone({ onFile, accept = 'video/*', disabled }: Props) {
  const [hover, setHover] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  const handle = useCallback(
    (file: File | null | undefined) => {
      if (!file) return;
      onFile(file);
    },
    [onFile],
  );

  return (
    <div
      onDragOver={(e) => {
        e.preventDefault();
        if (!disabled) setHover(true);
      }}
      onDragLeave={() => setHover(false)}
      onDrop={(e) => {
        e.preventDefault();
        setHover(false);
        if (disabled) return;
        handle(e.dataTransfer.files?.[0]);
      }}
      onClick={() => !disabled && inputRef.current?.click()}
      className={[
        'rounded-2xl border-2 border-dashed p-12 text-center transition select-none',
        disabled
          ? 'border-slate-700 bg-slate-900/40 text-slate-500 cursor-not-allowed'
          : hover
            ? 'border-accent bg-slate-900 text-slate-100 cursor-pointer'
            : 'border-slate-700 bg-slate-900/60 text-slate-300 hover:border-slate-500 cursor-pointer',
      ].join(' ')}
    >
      <div className="text-lg font-semibold">비디오 파일을 끌어다 놓으세요</div>
      <div className="mt-1 text-sm text-slate-400">또는 클릭해서 선택</div>
      <input
        ref={inputRef}
        type="file"
        accept={accept}
        className="hidden"
        onChange={(e) => handle(e.target.files?.[0])}
      />
    </div>
  );
}
