import type { ButtonHTMLAttributes } from 'react';

type Variant = 'primary' | 'ghost' | 'danger';

interface Props extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: Variant;
}

const styles: Record<Variant, string> = {
  primary:
    'bg-accent text-slate-900 hover:bg-cyan-300 disabled:bg-slate-700 disabled:text-slate-500',
  ghost:
    'bg-slate-800 text-slate-100 hover:bg-slate-700 disabled:bg-slate-900 disabled:text-slate-600',
  danger:
    'bg-rose-700 text-white hover:bg-rose-600 disabled:bg-slate-700 disabled:text-slate-500',
};

export function Button({ variant = 'primary', className, ...rest }: Props) {
  return (
    <button
      {...rest}
      className={[
        'rounded-lg px-4 py-2 text-sm font-medium transition disabled:cursor-not-allowed',
        styles[variant],
        className ?? '',
      ].join(' ')}
    />
  );
}
