interface Props {
  src: string;
}

export function VideoPlayer({ src }: Props) {
  return (
    <video
      src={src}
      controls
      playsInline
      className="aspect-video w-full rounded-xl bg-black ring-1 ring-slate-700"
    />
  );
}
