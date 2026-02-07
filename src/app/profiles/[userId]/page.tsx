import { createClient } from "@/lib/supabase/server";
import { notFound } from "next/navigation";
import { StatCard } from "@/components/stat-card";
import { RadarChart } from "@/components/radar-chart";
import { ProfileActions } from "@/components/profile-actions";
import Link from "next/link";

export default async function ProfileDetailPage({
  params,
}: {
  params: Promise<{ userId: string }>;
}) {
  const { userId } = await params;
  const decodedUserId = decodeURIComponent(userId);
  const supabase = await createClient();

  const { data: profile } = await supabase
    .from("user_profiles")
    .select("*")
    .eq("user_id", decodedUserId)
    .single();

  if (!profile) notFound();

  const { data: scores } = await supabase
    .from("behavioral_scores")
    .select("*")
    .eq("user_id", decodedUserId)
    .order("dimension");

  const { data: conversations } = await supabase
    .from("conversations")
    .select("conversation_id, model, language, turn_count, message_count")
    .eq("user_id", decodedUserId)
    .order("created_at", { ascending: false })
    .limit(20);

  // Sample messages for preview
  const { data: recentMessages } = await supabase
    .from("messages")
    .select("role, content, conversation_turn")
    .eq("user_id", decodedUserId)
    .order("created_at", { ascending: false })
    .limit(10);

  return (
    <div className="p-8">
      {/* Header */}
      <div className="mb-8">
        <Link
          href="/profiles"
          className="mb-3 inline-flex items-center gap-1 text-xs text-muted-foreground hover:text-foreground transition-colors"
        >
          <svg
            className="h-3 w-3"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M15 19l-7-7 7-7"
            />
          </svg>
          Back to profiles
        </Link>
        <div className="flex items-start justify-between">
          <div>
            <h1 className="text-2xl font-semibold text-foreground font-mono">
              {decodedUserId}
            </h1>
            <div className="mt-1 flex items-center gap-3 text-sm text-muted-foreground">
              <span>
                {profile.total_conversations} conversations
              </span>
              <span className="text-border">|</span>
              <span>
                {profile.total_messages} messages
              </span>
              {profile.languages?.length > 0 && (
                <>
                  <span className="text-border">|</span>
                  <span>{profile.languages.join(", ")}</span>
                </>
              )}
            </div>
          </div>
          <ProfileActions userId={decodedUserId} hasScores={(scores ?? []).length > 0} />
        </div>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
        <StatCard
          label="Conversations"
          value={profile.total_conversations}
        />
        <StatCard label="Messages" value={profile.total_messages} />
        <StatCard
          label="Avg Turns"
          value={profile.avg_turns_per_conversation}
        />
        <StatCard
          label="Avg Msgs/Conv"
          value={profile.avg_messages_per_conversation}
        />
      </div>

      <div className="mt-8 grid grid-cols-1 gap-6 lg:grid-cols-2">
        {/* Behavioral Scores */}
        <div className="rounded-lg border border-border bg-card p-5">
          <h3 className="text-sm font-medium text-foreground mb-4">
            Behavioral Profile
          </h3>
          {scores && scores.length > 0 ? (
            <div className="flex flex-col items-center">
              <RadarChart
                data={scores.map(
                  (s: {
                    dimension: string;
                    score: number;
                    confidence: number;
                  }) => ({
                    dimension: s.dimension,
                    score: s.score,
                    confidence: s.confidence,
                  })
                )}
              />
              <div className="mt-4 w-full flex flex-col gap-2">
                {scores.map(
                  (s: {
                    dimension: string;
                    score: number;
                    confidence: number;
                    evidence_summary: string | null;
                  }) => (
                    <div
                      key={s.dimension}
                      className="flex items-center justify-between rounded-md bg-muted/50 px-3 py-2"
                    >
                      <div className="min-w-0 flex-1">
                        <div className="flex items-center gap-2">
                          <span className="text-sm text-foreground font-medium">
                            {s.dimension}
                          </span>
                          <span className="text-xs text-muted-foreground font-mono">
                            {(s.confidence * 100).toFixed(0)}% conf
                          </span>
                        </div>
                        {s.evidence_summary && (
                          <p className="mt-0.5 text-xs text-muted-foreground truncate max-w-[300px]">
                            {s.evidence_summary}
                          </p>
                        )}
                      </div>
                      <span className="text-lg font-mono font-semibold text-primary ml-3">
                        {s.score.toFixed(1)}
                      </span>
                    </div>
                  )
                )}
              </div>
            </div>
          ) : (
            <div className="flex flex-col items-center py-8 text-center">
              <p className="text-sm text-muted-foreground">
                No behavioral scores generated yet
              </p>
              <p className="mt-1 text-xs text-muted-foreground">
                Click &quot;Generate Profile&quot; to analyze this user
              </p>
            </div>
          )}
        </div>

        {/* Conversations */}
        <div className="rounded-lg border border-border bg-card p-5">
          <h3 className="text-sm font-medium text-foreground mb-4">
            Conversations ({conversations?.length ?? 0})
          </h3>
          <div className="flex flex-col gap-2 max-h-[400px] overflow-y-auto">
            {conversations?.map(
              (conv: {
                conversation_id: string;
                model: string | null;
                language: string | null;
                turn_count: number;
                message_count: number;
              }) => (
                <div
                  key={conv.conversation_id}
                  className="rounded-md bg-muted/50 px-3 py-2"
                >
                  <p className="text-xs font-mono text-foreground truncate">
                    {conv.conversation_id}
                  </p>
                  <div className="mt-1 flex items-center gap-3 text-xs text-muted-foreground">
                    {conv.model && <span>{conv.model}</span>}
                    {conv.language && <span>{conv.language}</span>}
                    <span>{conv.message_count} msgs</span>
                    <span>{conv.turn_count} turns</span>
                  </div>
                </div>
              )
            )}
          </div>
        </div>
      </div>

      {/* Recent Messages Sample */}
      {recentMessages && recentMessages.length > 0 && (
        <div className="mt-6 rounded-lg border border-border bg-card p-5">
          <h3 className="text-sm font-medium text-foreground mb-4">
            Recent Messages (sample)
          </h3>
          <div className="flex flex-col gap-2 max-h-[300px] overflow-y-auto">
            {recentMessages.map(
              (
                msg: {
                  role: string;
                  content: string;
                  conversation_turn: number | null;
                },
                i: number
              ) => (
                <div
                  key={i}
                  className={`rounded-md px-3 py-2 ${
                    msg.role === "user"
                      ? "bg-primary/5 border-l-2 border-primary"
                      : "bg-muted/50 border-l-2 border-muted"
                  }`}
                >
                  <span className="text-xs font-medium text-muted-foreground uppercase">
                    {msg.role}
                  </span>
                  <p className="mt-0.5 text-sm text-foreground line-clamp-3 leading-relaxed">
                    {msg.content}
                  </p>
                </div>
              )
            )}
          </div>
        </div>
      )}
    </div>
  );
}
