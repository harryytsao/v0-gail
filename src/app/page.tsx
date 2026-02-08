"use client";

import { useEffect, useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { getDashboardStats, type DashboardStats } from "@/lib/api";

export default function DashboardPage() {
  const [stats, setStats] = useState<DashboardStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    getDashboardStats()
      .then(setStats)
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, []);

  const cards = [
    {
      title: "Total Users",
      value: stats?.total_users,
      description: "Users in database",
    },
    {
      title: "Conversations",
      value: stats?.total_conversations,
      description: "Total conversations ingested",
    },
    {
      title: "Profiled Users",
      value: stats?.profiled_users,
      description: "Users with behavioral profiles",
    },
    {
      title: "Scored Users",
      value: stats?.scored_users,
      description: "Users with fit scores",
    },
    {
      title: "Signals Extracted",
      value: stats?.total_signals,
      description: "Behavioral signals in database",
    },
  ];

  return (
    <div className="flex flex-col gap-6 p-6">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">Dashboard</h1>
        <p className="text-sm text-muted-foreground mt-1">
          Overview of the Gail behavioral profiling system.
        </p>
      </div>

      {error && (
        <div className="rounded-lg border border-destructive/50 bg-destructive/10 p-4 text-sm text-destructive">
          Failed to load stats: {error}
        </div>
      )}

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-5">
        {cards.map((card) => (
          <Card key={card.title}>
            <CardHeader className="pb-2">
              <CardTitle className="text-xs font-medium uppercase tracking-wider text-muted-foreground">
                {card.title}
              </CardTitle>
            </CardHeader>
            <CardContent>
              {loading ? (
                <Skeleton className="h-8 w-20" />
              ) : (
                <div className="text-2xl font-bold tabular-nums">
                  {card.value?.toLocaleString() ?? "—"}
                </div>
              )}
              <p className="text-xs text-muted-foreground mt-1">
                {card.description}
              </p>
            </CardContent>
          </Card>
        ))}
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="text-sm font-medium">Quick Actions</CardTitle>
        </CardHeader>
        <CardContent className="flex flex-wrap gap-3">
          <a
            href="/users?has_profile=true"
            className="inline-flex items-center rounded-md border border-border bg-secondary px-3 py-1.5 text-xs font-medium transition-colors hover:bg-accent"
          >
            View Profiled Users
          </a>
          <a
            href="/chat"
            className="inline-flex items-center rounded-md border border-border bg-secondary px-3 py-1.5 text-xs font-medium transition-colors hover:bg-accent"
          >
            Open Chat Agent
          </a>
          <a
            href="http://localhost:8000/docs"
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex items-center gap-1.5 rounded-md border border-border bg-secondary px-3 py-1.5 text-xs font-medium transition-colors hover:bg-accent"
          >
            API Docs
            <svg
              width="12"
              height="12"
              viewBox="0 0 12 12"
              fill="none"
              stroke="currentColor"
              strokeWidth="1.5"
            >
              <path d="M3.5 8.5l5-5M3.5 3.5h5v5" />
            </svg>
          </a>
        </CardContent>
      </Card>
    </div>
  );
}
