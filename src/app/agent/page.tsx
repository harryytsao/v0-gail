import { createClient } from "@/lib/supabase/server";
import { AgentChat } from "@/components/agent-chat";

export default async function AgentPage({
  searchParams,
}: {
  searchParams: Promise<{ userId?: string }>;
}) {
  const { userId } = await searchParams;
  const supabase = await createClient();

  // Fetch all profiled users for the selector
  const { data: profiles } = await supabase
    .from("user_profiles")
    .select("user_id, total_conversations, profile_generated")
    .eq("profile_generated", true)
    .order("total_conversations", { ascending: false })
    .limit(100);

  // If a userId is specified, fetch their scores
  let activeScores: { dimension: string; score: number }[] | null = null;
  if (userId) {
    const { data } = await supabase
      .from("behavioral_scores")
      .select("dimension, score")
      .eq("user_id", userId);
    activeScores = data;
  }

  return (
    <div className="flex h-screen flex-col">
      <AgentChat
        userId={userId ?? null}
        profiles={profiles ?? []}
        activeScores={activeScores}
      />
    </div>
  );
}
