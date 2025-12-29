import { Badge } from "./Badge";

export function StatCard({
  title,
  value,
  subvalue,
  badge,
}: {
  title: string;
  value: React.ReactNode;
  subvalue?: React.ReactNode;
  badge?: { text: string; tone?: "neutral" | "good" | "bad" | "warn" };
}) {
  return (
    <div className="rounded-2xl border border-border bg-card p-5">
      <div className="flex items-start justify-between gap-3">
        <div className="text-sm font-medium text-muted-foreground">{title}</div>
        {badge ? <Badge tone={badge.tone}>{badge.text}</Badge> : null}
      </div>
      <div className="mt-2 text-2xl font-semibold tracking-tight">{value}</div>
      {subvalue ? (
        <div className="mt-1 text-sm text-muted-foreground">{subvalue}</div>
      ) : null}
    </div>
  );
}
