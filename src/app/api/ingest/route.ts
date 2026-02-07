import { createClient } from "@/lib/supabase/server";
import { NextRequest, NextResponse } from "next/server";

export const maxDuration = 60;

interface ConversationRecord {
  user_id: string;
  conversation_id: string;
  model?: string;
  language?: string;
  conversation_turn?: number;
  message_index: number;
  role: string;
  content: string;
  redacted?: boolean;
}

export async function POST(req: NextRequest) {
  try {
    const { records, jobId, filename } = (await req.json()) as {
      records: ConversationRecord[];
      jobId: string;
      filename: string;
    };

    if (!records || !Array.isArray(records) || records.length === 0) {
      return NextResponse.json(
        { error: "No records provided" },
        { status: 400 }
      );
    }

    const supabase = await createClient();

    // Group records by conversation_id
    const convMap = new Map<
      string,
      {
        userId: string;
        model?: string;
        language?: string;
        messages: ConversationRecord[];
      }
    >();

    for (const record of records) {
      const key = record.conversation_id;
      if (!convMap.has(key)) {
        convMap.set(key, {
          userId: record.user_id,
          model: record.model,
          language: record.language,
          messages: [],
        });
      }
      convMap.get(key)!.messages.push(record);
    }

    // Upsert conversations
    const convRows = Array.from(convMap.entries()).map(([convId, data]) => ({
      conversation_id: convId,
      user_id: data.userId,
      model: data.model || null,
      language: data.language || null,
      turn_count: Math.max(...data.messages.map((m) => m.conversation_turn ?? 0)),
      message_count: data.messages.length,
    }));

    const { error: convError } = await supabase
      .from("conversations")
      .upsert(convRows, { onConflict: "conversation_id" });

    if (convError) {
      console.error("Conversation upsert error:", convError);
      return NextResponse.json(
        { error: `Conversation insert failed: ${convError.message}` },
        { status: 500 }
      );
    }

    // Insert messages
    const msgRows = records.map((r) => ({
      conversation_id: r.conversation_id,
      user_id: r.user_id,
      role: r.role,
      content: r.content,
      message_index: r.message_index,
      conversation_turn: r.conversation_turn ?? null,
      redacted: r.redacted ?? false,
    }));

    const { error: msgError } = await supabase.from("messages").insert(msgRows);

    if (msgError) {
      console.error("Message insert error:", msgError);
      return NextResponse.json(
        { error: `Message insert failed: ${msgError.message}` },
        { status: 500 }
      );
    }

    // Upsert user profiles (aggregate stats)
    const userMap = new Map<
      string,
      {
        conversations: Set<string>;
        messageCount: number;
        languages: Set<string>;
        models: Set<string>;
        turnCounts: number[];
      }
    >();

    for (const record of records) {
      if (!userMap.has(record.user_id)) {
        userMap.set(record.user_id, {
          conversations: new Set(),
          messageCount: 0,
          languages: new Set(),
          models: new Set(),
          turnCounts: [],
        });
      }
      const u = userMap.get(record.user_id)!;
      u.conversations.add(record.conversation_id);
      u.messageCount += 1;
      if (record.language) u.languages.add(record.language);
      if (record.model) u.models.add(record.model);
      if (record.conversation_turn) u.turnCounts.push(record.conversation_turn);
    }

    const profileRows = Array.from(userMap.entries()).map(([userId, data]) => {
      const avgTurns =
        data.turnCounts.length > 0
          ? data.turnCounts.reduce((a, b) => a + b, 0) / data.turnCounts.length
          : 0;
      return {
        user_id: userId,
        total_conversations: data.conversations.size,
        total_messages: data.messageCount,
        languages: Array.from(data.languages),
        models_used: Array.from(data.models),
        avg_turns_per_conversation: Math.round(avgTurns * 100) / 100,
        avg_messages_per_conversation:
          Math.round((data.messageCount / data.conversations.size) * 100) / 100,
        first_seen: new Date().toISOString(),
        last_seen: new Date().toISOString(),
        updated_at: new Date().toISOString(),
      };
    });

    const { error: profileError } = await supabase
      .from("user_profiles")
      .upsert(profileRows, { onConflict: "user_id" });

    if (profileError) {
      console.error("Profile upsert error:", profileError);
    }

    // Update job progress
    await supabase
      .from("ingestion_jobs")
      .update({
        processed_records:
          records.length,
        updated_at: new Date().toISOString(),
      })
      .eq("id", jobId);

    return NextResponse.json({
      success: true,
      processed: records.length,
      conversations: convMap.size,
      users: userMap.size,
    });
  } catch (error) {
    console.error("Ingest error:", error);
    return NextResponse.json(
      { error: "Internal server error" },
      { status: 500 }
    );
  }
}
