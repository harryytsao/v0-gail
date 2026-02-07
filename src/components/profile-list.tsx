"use client";

import { useState } from "react";
import Link from "next/link";

interface BehavioralScore {
  dimension: string;
  score: number;
  confidence: number;
}

interface UserProfile {
  user_id: string;
  total_conversations: number;
  total_messages: number;
  languages: string[];
  models_used: string[];
  avg_turns_per_conversation: number;
  profile_generated: boolean;
  behavioral_scores: BehavioralScore[];
}

function ScoreBar({ score, label }: { score: number; label: string }) {
  return (
    <div className="flex items-center gap-2">
      <span className="w-10 text-xs text-muted-foreground font-mono truncate">
        {label.slice(0, 4)}
      </span>
      <div className="flex-1 h-1.5 rounded-full bg-muted overflow-hidden">
        <div
          className="h-full rounded-full bg-primary transition-all"
          style={{ width: `${score * 10}%` }}
        />
      </div>
      <span className="w-6 text-right text-xs font-mono text-muted-foreground">
        {score.toFixed(1)}
      </span>
    </div>
  );
}

export function ProfileList({
  initialProfiles,
  totalCount,
}: {
  initialProfiles: UserProfile[];
  totalCount: number;
}) {
  const [search, setSearch] = useState("");
  const [filter, setFilter] = useState<"all" | "scored" | "unscored">("all");

  const filtered = initialProfiles.filter((p) => {
    const matchesSearch =
      search === "" ||
      p.user_id.toLowerCase().includes(search.toLowerCase());
    const matchesFilter =
      filter === "all" ||
      (filter === "scored" && p.profile_generated) ||
      (filter === "unscored" && !p.profile_generated);
    return matchesSearch && matchesFilter;
  });

  return (
    <div>
      {/* Controls */}
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center mb-6">
        <div className="relative flex-1">
          <svg
            className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={1.5}
              d="M21 21l-5.197-5.197m0 0A7.5 7.5 0 105.196 5.196a7.5 7.5 0 0010.607 10.607z"
            />
          </svg>
          <input
            type="text"
            placeholder="Search by user ID..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="h-9 w-full rounded-md border border-border bg-card pl-9 pr-3 text-sm text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-1 focus:ring-ring"
          />
        </div>
        <div className="flex gap-1 rounded-md border border-border bg-card p-0.5">
          {(["all", "scored", "unscored"] as const).map((f) => (
            <button
              key={f}
              onClick={() => setFilter(f)}
              className={`rounded px-3 py-1 text-xs font-medium transition-colors ${
                filter === f
                  ? "bg-primary text-primary-foreground"
                  : "text-muted-foreground hover:text-foreground"
              }`}
            >
              {f === "all"
                ? `All (${totalCount})`
                : f === "scored"
                  ? "Scored"
                  : "Unscored"}
            </button>
          ))}
        </div>
      </div>

      {/* Profile Grid */}
      <div className="grid grid-cols-1 gap-3 lg:grid-cols-2 xl:grid-cols-3">
        {filtered.map((profile) => (
          <Link
            key={profile.user_id}
            href={`/profiles/${encodeURIComponent(profile.user_id)}`}
            className="group rounded-lg border border-border bg-card p-4 transition-colors hover:border-primary/30"
          >
            <div className="flex items-start justify-between">
              <div className="min-w-0">
                <p className="text-sm font-mono font-medium text-foreground truncate">
                  {profile.user_id}
                </p>
                <div className="mt-1 flex items-center gap-3 text-xs text-muted-foreground">
                  <span>
                    {profile.total_conversations} conv
                  </span>
                  <span>
                    {profile.total_messages} msgs
                  </span>
                </div>
              </div>
              {profile.profile_generated ? (
                <span className="rounded-full bg-primary/10 px-2 py-0.5 text-xs font-medium text-primary">
                  scored
                </span>
              ) : (
                <span className="rounded-full bg-muted px-2 py-0.5 text-xs font-medium text-muted-foreground">
                  pending
                </span>
              )}
            </div>

            {/* Mini score bars */}
            {profile.behavioral_scores &&
              profile.behavioral_scores.length > 0 && (
                <div className="mt-3 flex flex-col gap-1.5">
                  {profile.behavioral_scores
                    .slice(0, 3)
                    .map((s: BehavioralScore) => (
                      <ScoreBar
                        key={s.dimension}
                        label={s.dimension}
                        score={s.score}
                      />
                    ))}
                </div>
              )}

            {/* Languages */}
            {profile.languages && profile.languages.length > 0 && (
              <div className="mt-3 flex flex-wrap gap-1">
                {profile.languages.slice(0, 3).map((lang: string) => (
                  <span
                    key={lang}
                    className="rounded bg-muted px-1.5 py-0.5 text-xs font-mono text-muted-foreground"
                  >
                    {lang}
                  </span>
                ))}
                {profile.languages.length > 3 && (
                  <span className="text-xs text-muted-foreground">
                    +{profile.languages.length - 3}
                  </span>
                )}
              </div>
            )}
          </Link>
        ))}
      </div>

      {filtered.length === 0 && (
        <div className="py-12 text-center">
          <p className="text-sm text-muted-foreground">
            No profiles match your search
          </p>
        </div>
      )}
    </div>
  );
}
