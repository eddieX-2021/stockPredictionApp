import Link from "next/link";

import { Badge } from "../components/ui/Badge";
import { ThemeToggle } from "../components/ui/ThemeToggle";

export const metadata = {
  title: "ChatGPT App - Under development",
  description: "Future ChatGPT App concept for the stock research dashboard.",
};

export default function ChatGptAppPage() {
  return (
    <main className="min-h-screen bg-bg">
      <div className="mx-auto max-w-5xl px-6 py-8">
        <div className="flex items-center justify-between gap-4">
          <Link href="/" className="text-sm text-muted-foreground hover:text-foreground">
            Back to dashboard
          </Link>
          <ThemeToggle />
        </div>

        <section className="mt-8 rounded-lg border border-border bg-card p-6 sm:p-8">
          <div className="flex flex-wrap items-center gap-3">
            <h1 className="text-3xl font-semibold tracking-tight">ChatGPT App</h1>
            <Badge tone="warn">Under development</Badge>
          </div>
          <p className="mt-4 max-w-3xl leading-relaxed text-muted-foreground">
            A separate ChatGPT App is planned for this project. It will use the OpenAI Apps SDK and a remote MCP server to retrieve structured research snapshots from this dashboard backend, then explain the data inside ChatGPT.
          </p>
          <p className="mt-3 max-w-3xl leading-relaxed text-muted-foreground">
            This website remains focused on Phase 1: collecting free market and company data, calculating metrics, organizing the dashboard, and preserving the existing experimental prediction signals. The ChatGPT App is not available yet and is not implemented in this repository.
          </p>
        </section>

        <section className="mt-6 rounded-lg border border-border bg-card p-6">
          <div className="text-lg font-semibold">Planned workflow</div>
          <div className="mt-5 grid gap-4 md:grid-cols-3">
            <div className="rounded-md border border-border bg-subtle p-4">
              <div className="text-sm font-semibold">1. Ask ChatGPT</div>
              <p className="mt-2 text-sm text-muted-foreground">The user asks ChatGPT to research a stock or compare company signals.</p>
            </div>
            <div className="rounded-md border border-border bg-subtle p-4">
              <div className="text-sm font-semibold">2. Retrieve snapshot</div>
              <p className="mt-2 text-sm text-muted-foreground">The future app calls this project's structured research snapshot endpoint for current dashboard data.</p>
            </div>
            <div className="rounded-md border border-border bg-subtle p-4">
              <div className="text-sm font-semibold">3. Explain in ChatGPT</div>
              <p className="mt-2 text-sm text-muted-foreground">ChatGPT explains financials, trend, valuation, risks, earnings, conflicting signals, and scenarios.</p>
            </div>
          </div>
        </section>

        <div className="mt-6 flex flex-wrap gap-3">
          <Link href="/" className="rounded-md border border-border bg-subtle px-4 py-2 text-sm font-medium text-foreground hover:bg-surface">
            Return to dashboard
          </Link>
        </div>
      </div>
    </main>
  );
}