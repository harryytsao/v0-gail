import { createClient } from "@/lib/supabase/server";
import { NextRequest, NextResponse } from "next/server";

export async function POST(req: NextRequest) {
  const { filename, totalRecords } = await req.json();
  const supabase = await createClient();

  const { data, error } = await supabase
    .from("ingestion_jobs")
    .insert({
      filename,
      status: "processing",
      total_records: totalRecords,
      processed_records: 0,
    })
    .select()
    .single();

  if (error) {
    return NextResponse.json({ error: error.message }, { status: 500 });
  }

  return NextResponse.json({ job: data });
}

export async function PATCH(req: NextRequest) {
  const { jobId, status, processedRecords, errorMessage } = await req.json();
  const supabase = await createClient();

  const update: Record<string, unknown> = {
    status,
    updated_at: new Date().toISOString(),
  };
  if (processedRecords !== undefined) update.processed_records = processedRecords;
  if (errorMessage) update.error_message = errorMessage;

  const { error } = await supabase
    .from("ingestion_jobs")
    .update(update)
    .eq("id", jobId);

  if (error) {
    return NextResponse.json({ error: error.message }, { status: 500 });
  }

  return NextResponse.json({ success: true });
}
