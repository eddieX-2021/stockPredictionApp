export function Badge({
  children,
  tone = "neutral",
}: {
  children: React.ReactNode;
  tone?: "neutral" | "good" | "bad" | "warn";
}) {
  const toneClass =
    tone === "good"
      ? "bg-emerald-500/10 text-emerald-700 border-emerald-200"
      : tone === "bad"
      ? "bg-rose-500/10 text-rose-700 border-rose-200"
      : tone === "warn"
      ? "bg-amber-500/10 text-amber-800 border-amber-200"
      : "bg-black/5 text-foreground border-border";

  return (
    <span className={`inline-flex items-center rounded-full border px-2.5 py-1 text-xs font-medium ${toneClass}`}>
      {children}
    </span>
  );
}
