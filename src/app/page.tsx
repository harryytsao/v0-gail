import { createClient } from "@/lib/supabase/server";
import { StatCard } from "@/components/stat-card";
import Link from "next/link";

export default async function DashboardPage() {
  let conversationCount = 0;
  let messageCount = 0;
  let profileCount = 0;
  let scoredCount = 0;
  let recentJobs: { id: string; filename: string; status: string; processed_records: number; total_records: number }[] = [];
  let topLanguages: { language: string | null }[] = [];

  try {
    const supabase = await createClient();

    const results = await Promise.all([
      supabase
        .from("conversations")
        .select("*", { count: "exact", head: true }),
      supabase.from("messages").select("*", { count: "exact", head: true }),
      supabase
        .from("user_profiles")
        .select("*", { count: "exact", head: true }),
      supabase
        .from("user_profiles")
        .select("*", { count: "exact", head: true })
        .eq("profile_generated", true),
      supabase
        .from("ingestion_jobs")
        .select("*")
        .order("created_at", { ascending: false })
        .limit(5),
      supabase
        .from("conversations")
        .select("language")
        .not("language", "is", null)
        .limit(1000),
    ]);

    conversationCount = results[0].count ?? 0;
    messageCount = results[1].count ?? 0;
    profileCount = results[2].count ?? 0;
    scoredCount = results[3].count ?? 0;
    recentJobs = (results[4].data as typeof recentJobs) ?? [];
    topLanguages = (results[5].data as typeof topLanguages) ?? [];
  } catch (e) {
    console.error("[v0] Dashboard query error:", e);
  }

  // Aggregate language counts client-side from sample
  const langCounts: Record<string, number> = {};
  topLanguages?.forEach((row: { language: string | null }) => {
    if (row.language) {
      langCounts[row.language] = (langCounts[row.language] || 0) + 1;
    }
  });
  const sortedLangs = Object.entries(langCounts)
    .sort(([, a], [, b]) => b - a)
    .slice(0, 8);

  const hasData = conversationCount > 0;

  return (
    <div className="p-8">
      <div className="mb-8">
        <h1 className="text-2xl font-semibold text-foreground text-balance">
          Dashboard
        </h1>
        <p className="mt-1 text-sm text-muted-foreground">
          Behavioral profiling system overview
        </p>
      </div>

      {/* Stats Grid */}
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <StatCard
          label="Conversations"
          value={conversationCount}
          detail="Total ingested conversations"
        />
        <StatCard
          label="Messages"
          value={messageCount}
          detail="Total message records"
        />
        <StatCard
          label="Unique Users"
          value={profileCount}
          detail="Distinct user profiles"
        />
        <StatCard
          label="Profiled"
          value={scoredCount}
          detail="Users with behavioral scores"
        />
      </div>

      {/* Empty state */}
      {!hasData && (
        <div className="mt-12 flex flex-col items-center justify-center rounded-lg border border-dashed border-border p-12 text-center">
          <svg
            className="h-12 w-12 text-muted-foreground"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={1}
              d="M20.25 6.375c0 2.278-3.694 4.125-8.25 4.125S3.75 8.653 3.75 6.375m16.5 0c0-2.278-3.694-4.125-8.25-4.125S3.75 4.097 3.75 6.375m16.5 0v11.25c0 2.278-3.694 4.125-8.25 4.125s-8.25-1.847-8.25-4.125V6.375m16.5 0v3.75m-16.5-3.75v3.75m16.5 0v3.75C20.25 16.153 16.556 18 12 18s-8.25-1.847-8.25-4.125v-3.75m16.5 0c0 2.278-3.694 4.125-8.25 4.125s-8.25-1.847-8.25-4.125"
            />
          </svg>
          <h2 className="mt-4 text-lg font-medium text-foreground">
            No data ingested yet
          </h2>
          <p className="mt-2 max-w-sm text-sm text-muted-foreground">
            Upload your conversation JSONL file to begin building behavioral
            profiles. The system will extract user signals and score them across
            6 dimensions.
          </p>
          <Link
            href="/ingest"
            className="mt-6 inline-flex items-center gap-2 rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground transition-colors hover:bg-primary/90"
          >
            <svg
              className="h-4 w-4"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M3 16.5v2.25A2.25 2.25 0 005.25 21h13.5A2.25 2.25 0 0021 18.75V16.5m-13.5-9L12 3m0 0l4.5 4.5M12 3v13.5"
              />
            </svg>
            Ingest Data
          </Link>
        </div>
      )}

      {/* Content when data exists */}
      {hasData && (
        <div className="mt-8 grid grid-cols-1 gap-6 lg:grid-cols-2">
          {/* Languages */}
          <div className="rounded-lg border border-border bg-card p-5">
            <h3 className="text-sm font-medium text-foreground">
              Top Languages
            </h3>
            <div className="mt-4 flex flex-col gap-2">
              {sortedLangs.map(([lang, count]) => {
                const maxCount = sortedLangs[0]?.[1] ?? 1;
                const pct = (count / maxCount) * 100;
                return (
                  <div key={lang} className="flex items-center gap-3">
                    <span className="w-16 text-xs font-mono text-muted-foreground truncate">
                      {lang}
                    </span>
                    <div className="flex-1 h-2 rounded-full bg-muted overflow-hidden">
                      <div
                        className="h-full rounded-full bg-primary transition-all"
                        style={{ width: `${pct}%` }}
                      />
                    </div>
                    <span className="w-10 text-right text-xs font-mono text-muted-foreground">
                      {count}
                    </span>
                  </div>
                );
              })}
              {sortedLangs.length === 0 && (
                <p className="text-xs text-muted-foreground">
                  No language data
                </p>
              )}
            </div>
          </div>

          {/* Recent Jobs */}
          <div className="rounded-lg border border-border bg-card p-5">
            <h3 className="text-sm font-medium text-foreground">
              Recent Ingestion Jobs
            </h3>
            <div className="mt-4 flex flex-col gap-2">
              {recentJobs.length > 0 ? (
                recentJobs.map((job) => (
                    <div
                      key={job.id}
                      className="flex items-center justify-between rounded-md bg-muted/50 px-3 py-2"
                    >
                      <div>
                        <p className="text-sm font-mono text-foreground truncate max-w-[200px]">
                          {job.filename}
                        </p>
                        <p className="text-xs text-muted-foreground">
                          {job.processed_records.toLocaleString()} /{" "}
                          {job.total_records.toLocaleString()} records
                        </p>
                      </div>
                      <span
                        className={`rounded-full px-2 py-0.5 text-xs font-medium ${
                          job.status === "completed"
                            ? "bg-emerald-500/10 text-emerald-400"
                            : job.status === "processing"
                              ? "bg-primary/10 text-primary"
                              : job.status === "failed"
                                ? "bg-destructive/10 text-destructive"
                                : "bg-muted text-muted-foreground"
                        }`}
                      >
                        {job.status}
                      </span>
                    </div>
                  )
                )
              ) : (
                <p className="text-xs text-muted-foreground">No jobs yet</p>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
