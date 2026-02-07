import { createClient } from "@/lib/supabase/server";
import {
  consumeStream,
  convertToModelMessages,
  streamText,
  UIMessage,
} from "ai";

export const maxDuration = 60;

function buildAdaptiveSystemPrompt(
  scores: { dimension: string; score: number; evidence_summary: string | null }[],
  profile: {
    user_id: string;
    total_conversations: number;
    languages: string[];
  } | null
): string {
  const basePrompt = `You are Gail, an adaptive conversational AI. You adjust your communication style based on the behavioral profile of the user you're speaking with.`;

  if (!scores || scores.length === 0) {
    return `${basePrompt}\n\nNo behavioral profile is available for this user. Use a balanced, neutral communication style. Be helpful and attentive.`;
  }

  const scoreMap = Object.fromEntries(
    scores.map((s) => [s.dimension, s])
  );

  const adaptations: string[] = [];

  // Patience
  const patience = scoreMap["Patience"];
  if (patience) {
    if (patience.score <= 3)
      adaptations.push(
        "This user is IMPATIENT. Get to the point quickly. Use short, direct sentences. Skip preambles."
      );
    else if (patience.score >= 7)
      adaptations.push(
        "This user is patient. You can take time to explain thoroughly and provide context."
      );
  }

  // Technical Depth
  const techDepth = scoreMap["Technical Depth"];
  if (techDepth) {
    if (techDepth.score <= 3)
      adaptations.push(
        "This user is NON-TECHNICAL. Avoid jargon. Use simple analogies. Explain concepts in plain language."
      );
    else if (techDepth.score >= 7)
      adaptations.push(
        "This user is HIGHLY TECHNICAL. Use precise terminology. Skip basic explanations. Engage at expert level."
      );
  }

  // Frustration Tolerance
  const frustration = scoreMap["Frustration Tolerance"];
  if (frustration) {
    if (frustration.score <= 3)
      adaptations.push(
        "This user has LOW frustration tolerance. Be extra careful with errors. Acknowledge mistakes quickly. Stay calm and reassuring."
      );
    else if (frustration.score >= 7)
      adaptations.push(
        "This user handles frustration well. You can be more direct about limitations without excessive hedging."
      );
  }

  // Verbosity
  const verbosity = scoreMap["Verbosity"];
  if (verbosity) {
    if (verbosity.score <= 3)
      adaptations.push(
        "This user prefers BREVITY. Keep responses short and concise. Use bullet points. Minimize filler text."
      );
    else if (verbosity.score >= 7)
      adaptations.push(
        "This user appreciates DETAILED responses. Provide thorough explanations, examples, and context."
      );
  }

  // Politeness
  const politeness = scoreMap["Politeness"];
  if (politeness) {
    if (politeness.score <= 3)
      adaptations.push(
        "This user is direct/informal. Match their tone. Skip excessive pleasantries. Be straightforward."
      );
    else if (politeness.score >= 7)
      adaptations.push(
        "This user values politeness. Use warm, courteous language. Include greetings and acknowledgments."
      );
  }

  // Engagement
  const engagement = scoreMap["Engagement Level"];
  if (engagement) {
    if (engagement.score <= 3)
      adaptations.push(
        "This user has LOW engagement. Keep it simple, answer directly, don't push for deeper conversation."
      );
    else if (engagement.score >= 7)
      adaptations.push(
        "This user is HIGHLY ENGAGED. Ask follow-up questions. Explore topics deeper. Encourage dialogue."
      );
  }

  const profileSummary = profile
    ? `\nUser context: ${profile.total_conversations} past conversations, languages: ${profile.languages?.join(", ") || "unknown"}`
    : "";

  const scoresSummary = scores
    .map(
      (s) =>
        `  ${s.dimension}: ${s.score}/10${s.evidence_summary ? ` (${s.evidence_summary})` : ""}`
    )
    .join("\n");

  return `${basePrompt}
${profileSummary}

Behavioral scores:
${scoresSummary}

Adaptation instructions:
${adaptations.length > 0 ? adaptations.join("\n") : "Use a balanced communication style."}

IMPORTANT: Adapt your style naturally. Do NOT mention that you have a behavioral profile or scores. Do NOT reference the scoring system. Just naturally adjust how you communicate.`;
}

export async function POST(req: Request) {
  const { messages, userId }: { messages: UIMessage[]; userId?: string } =
    await req.json();

  let systemPrompt =
    "You are Gail, a helpful conversational AI assistant.";

  if (userId) {
    const supabase = await createClient();

    const [{ data: profile }, { data: scores }] = await Promise.all([
      supabase
        .from("user_profiles")
        .select("user_id, total_conversations, languages")
        .eq("user_id", userId)
        .single(),
      supabase
        .from("behavioral_scores")
        .select("dimension, score, evidence_summary")
        .eq("user_id", userId),
    ]);

    systemPrompt = buildAdaptiveSystemPrompt(scores ?? [], profile);
  }

  const result = streamText({
    model: "anthropic/claude-sonnet-4-20250514",
    system: systemPrompt,
    messages: await convertToModelMessages(messages),
    abortSignal: req.signal,
  });

  return result.toUIMessageStreamResponse({
    originalMessages: messages,
    onFinish: async ({ isAborted }) => {
      if (isAborted) return;
    },
    consumeSseStream: consumeStream,
  });
}
