import { createClient } from "@/lib/supabase/server";
import { generateText, Output } from "ai";
import { NextRequest, NextResponse } from "next/server";
import { z } from "zod";

export const maxDuration = 60;

const DIMENSIONS = [
  "Patience",
  "Technical Depth",
  "Frustration Tolerance",
  "Verbosity",
  "Politeness",
  "Engagement Level",
];

const BehavioralProfileSchema = z.object({
  scores: z.array(
    z.object({
      dimension: z.string(),
      score: z.number(),
      confidence: z.number(),
      evidence_summary: z.string(),
    })
  ),
});

export async function POST(req: NextRequest) {
  try {
    const { userId } = await req.json();
    if (!userId) {
      return NextResponse.json(
        { error: "userId is required" },
        { status: 400 }
      );
    }

    const supabase = await createClient();

    // Fetch user's messages (sample up to 200 for analysis)
    const { data: messages } = await supabase
      .from("messages")
      .select("role, content, conversation_turn, message_index")
      .eq("user_id", userId)
      .order("message_index", { ascending: true })
      .limit(200);

    if (!messages || messages.length === 0) {
      return NextResponse.json(
        { error: "No messages found for this user" },
        { status: 404 }
      );
    }

    // Build conversation context
    const conversationText = messages
      .map(
        (m: { role: string; content: string }) =>
          `[${m.role.toUpperCase()}]: ${m.content.slice(0, 500)}`
      )
      .join("\n");

    const result = await generateText({
      model: "anthropic/claude-sonnet-4-20250514",
      output: Output.object({ schema: BehavioralProfileSchema }),
      prompt: `You are an expert behavioral analyst. Analyze the following conversation history from a single user and score them on these behavioral dimensions (1-10 scale). Also provide a confidence score (0-1) based on how much evidence you have.

Dimensions:
${DIMENSIONS.map((d) => `- ${d}`).join("\n")}

Score guidelines:
- Patience (1=very impatient, 10=extremely patient): Look for signs of frustration, repeated requests, tolerance for delays
- Technical Depth (1=non-technical, 10=expert): Vocabulary complexity, use of technical terms, specificity of questions  
- Frustration Tolerance (1=easily frustrated, 10=very tolerant): Response to errors, repeated attempts, emotional language
- Verbosity (1=very terse, 10=very verbose): Average message length, detail level, explanatory text
- Politeness (1=curt/rude, 10=very polite): Use of please/thanks, tone, respectful language
- Engagement Level (1=minimal, 10=highly engaged): Follow-up questions, depth of interaction, persistence

Conversation history (${messages.length} messages):
${conversationText}

Respond with scores for each dimension.`,
    });

    if (!result.output) {
      return NextResponse.json(
        { error: "Failed to generate profile" },
        { status: 500 }
      );
    }

    const { scores } = result.output;

    // Upsert behavioral scores
    for (const score of scores) {
      await supabase.from("behavioral_scores").upsert(
        {
          user_id: userId,
          dimension: score.dimension,
          score: score.score,
          confidence: score.confidence,
          evidence_summary: score.evidence_summary,
          updated_at: new Date().toISOString(),
        },
        { onConflict: "user_id,dimension" }
      );
    }

    // Mark profile as generated
    await supabase
      .from("user_profiles")
      .update({
        profile_generated: true,
        updated_at: new Date().toISOString(),
      })
      .eq("user_id", userId);

    return NextResponse.json({ success: true, scores });
  } catch (error) {
    console.error("Profile generation error:", error);
    return NextResponse.json(
      { error: "Failed to generate profile" },
      { status: 500 }
    );
  }
}
