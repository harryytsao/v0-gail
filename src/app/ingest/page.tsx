"use client";

import { useState, useCallback, useRef } from "react";

const CHUNK_SIZE = 500;

interface IngestState {
  status: "idle" | "reading" | "uploading" | "completed" | "error";
  totalRecords: number;
  processedRecords: number;
  chunksTotal: number;
  chunksProcessed: number;
  jobId: string | null;
  error: string | null;
  filename: string | null;
  conversationsIngested: number;
  usersIngested: number;
}

export default function IngestPage() {
  const [state, setState] = useState<IngestState>({
    status: "idle",
    totalRecords: 0,
    processedRecords: 0,
    chunksTotal: 0,
    chunksProcessed: 0,
    jobId: null,
    error: null,
    filename: null,
    conversationsIngested: 0,
    usersIngested: 0,
  });
  const fileRef = useRef<HTMLInputElement>(null);

  const handleUpload = useCallback(async (file: File) => {
    setState((s) => ({
      ...s,
      status: "reading",
      filename: file.name,
      error: null,
    }));

    try {
      const text = await file.text();
      const lines = text
        .split("\n")
        .filter((line) => line.trim().length > 0);

      const records = lines.map((line) => JSON.parse(line));
      const totalRecords = records.length;
      const chunks: typeof records[] = [];

      for (let i = 0; i < records.length; i += CHUNK_SIZE) {
        chunks.push(records.slice(i, i + CHUNK_SIZE));
      }

      // Create job
      const jobRes = await fetch("/api/ingest/job", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          filename: file.name,
          totalRecords,
        }),
      });
      const { job } = await jobRes.json();

      setState((s) => ({
        ...s,
        status: "uploading",
        totalRecords,
        chunksTotal: chunks.length,
        jobId: job.id,
      }));

      let totalProcessed = 0;
      let totalConversations = 0;
      let totalUsers = 0;

      for (let i = 0; i < chunks.length; i++) {
        const res = await fetch("/api/ingest", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            records: chunks[i],
            jobId: job.id,
            filename: file.name,
          }),
        });

        const data = await res.json();

        if (!res.ok) {
          throw new Error(data.error || "Chunk upload failed");
        }

        totalProcessed += data.processed;
        totalConversations += data.conversations;
        totalUsers += data.users;

        setState((s) => ({
          ...s,
          processedRecords: totalProcessed,
          chunksProcessed: i + 1,
          conversationsIngested: totalConversations,
          usersIngested: totalUsers,
        }));
      }

      // Mark job completed
      await fetch("/api/ingest/job", {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          jobId: job.id,
          status: "completed",
          processedRecords: totalProcessed,
        }),
      });

      setState((s) => ({ ...s, status: "completed" }));
    } catch (err) {
      const msg = err instanceof Error ? err.message : "Unknown error";
      setState((s) => ({ ...s, status: "error", error: msg }));

      // Mark job as failed if we have a jobId
      if (state.jobId) {
        await fetch("/api/ingest/job", {
          method: "PATCH",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            jobId: state.jobId,
            status: "failed",
            errorMessage: msg,
          }),
        });
      }
    }
  }, [state.jobId]);

  const handleDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      const file = e.dataTransfer.files[0];
      if (file) handleUpload(file);
    },
    [handleUpload]
  );

  const progressPct =
    state.chunksTotal > 0
      ? Math.round((state.chunksProcessed / state.chunksTotal) * 100)
      : 0;

  return (
    <div className="p-8">
      <div className="mb-8">
        <h1 className="text-2xl font-semibold text-foreground text-balance">
          Ingest Data
        </h1>
        <p className="mt-1 text-sm text-muted-foreground">
          Upload JSONL conversation files for behavioral profiling
        </p>
      </div>

      {/* Upload Zone */}
      <div
        onDrop={handleDrop}
        onDragOver={(e) => e.preventDefault()}
        className={`relative flex flex-col items-center justify-center rounded-lg border-2 border-dashed p-12 transition-colors ${
          state.status === "idle"
            ? "border-border hover:border-primary/50 cursor-pointer"
            : state.status === "error"
              ? "border-destructive/50"
              : state.status === "completed"
                ? "border-emerald-500/50"
                : "border-primary/30"
        }`}
        onClick={() =>
          state.status === "idle" && fileRef.current?.click()
        }
        role="button"
        tabIndex={0}
        onKeyDown={(e) => {
          if (e.key === "Enter" && state.status === "idle")
            fileRef.current?.click();
        }}
      >
        <input
          ref={fileRef}
          type="file"
          accept=".jsonl,.json,.ndjson"
          className="sr-only"
          onChange={(e) => {
            const file = e.target.files?.[0];
            if (file) handleUpload(file);
          }}
        />

        {state.status === "idle" && (
          <>
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
                d="M3 16.5v2.25A2.25 2.25 0 005.25 21h13.5A2.25 2.25 0 0021 18.75V16.5m-13.5-9L12 3m0 0l4.5 4.5M12 3v13.5"
              />
            </svg>
            <p className="mt-4 text-sm font-medium text-foreground">
              Drop your JSONL file here, or click to browse
            </p>
            <p className="mt-1 text-xs text-muted-foreground">
              Supports .jsonl, .json, .ndjson files
            </p>
          </>
        )}

        {(state.status === "reading" ||
          state.status === "uploading") && (
          <div className="w-full max-w-md">
            <div className="flex items-center gap-3 mb-4">
              <div className="h-8 w-8 animate-spin rounded-full border-2 border-primary border-t-transparent" />
              <div>
                <p className="text-sm font-medium text-foreground">
                  {state.status === "reading"
                    ? "Reading file..."
                    : "Uploading chunks..."}
                </p>
                <p className="text-xs text-muted-foreground font-mono">
                  {state.filename}
                </p>
              </div>
            </div>

            {state.status === "uploading" && (
              <>
                <div className="h-2 w-full rounded-full bg-muted overflow-hidden">
                  <div
                    className="h-full rounded-full bg-primary transition-all duration-300"
                    style={{ width: `${progressPct}%` }}
                  />
                </div>
                <div className="mt-3 grid grid-cols-3 gap-4 text-center">
                  <div>
                    <p className="text-lg font-mono font-semibold text-foreground">
                      {state.processedRecords.toLocaleString()}
                    </p>
                    <p className="text-xs text-muted-foreground">
                      Records
                    </p>
                  </div>
                  <div>
                    <p className="text-lg font-mono font-semibold text-foreground">
                      {state.chunksProcessed}/{state.chunksTotal}
                    </p>
                    <p className="text-xs text-muted-foreground">
                      Chunks
                    </p>
                  </div>
                  <div>
                    <p className="text-lg font-mono font-semibold text-foreground">
                      {progressPct}%
                    </p>
                    <p className="text-xs text-muted-foreground">
                      Complete
                    </p>
                  </div>
                </div>
              </>
            )}
          </div>
        )}

        {state.status === "completed" && (
          <div className="text-center">
            <svg
              className="mx-auto h-12 w-12 text-emerald-400"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={1.5}
                d="M9 12.75L11.25 15 15 9.75M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
              />
            </svg>
            <p className="mt-3 text-sm font-medium text-foreground">
              Ingestion complete
            </p>
            <div className="mt-3 grid grid-cols-3 gap-6 text-center">
              <div>
                <p className="text-lg font-mono font-semibold text-foreground">
                  {state.processedRecords.toLocaleString()}
                </p>
                <p className="text-xs text-muted-foreground">Records</p>
              </div>
              <div>
                <p className="text-lg font-mono font-semibold text-foreground">
                  {state.conversationsIngested.toLocaleString()}
                </p>
                <p className="text-xs text-muted-foreground">
                  Conversations
                </p>
              </div>
              <div>
                <p className="text-lg font-mono font-semibold text-foreground">
                  {state.usersIngested.toLocaleString()}
                </p>
                <p className="text-xs text-muted-foreground">Users</p>
              </div>
            </div>
            <button
              onClick={() =>
                setState({
                  status: "idle",
                  totalRecords: 0,
                  processedRecords: 0,
                  chunksTotal: 0,
                  chunksProcessed: 0,
                  jobId: null,
                  error: null,
                  filename: null,
                  conversationsIngested: 0,
                  usersIngested: 0,
                })
              }
              className="mt-4 text-sm text-primary hover:text-primary/80 transition-colors"
            >
              Upload another file
            </button>
          </div>
        )}

        {state.status === "error" && (
          <div className="text-center">
            <svg
              className="mx-auto h-12 w-12 text-destructive"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={1.5}
                d="M12 9v3.75m9-.75a9 9 0 11-18 0 9 9 0 0118 0zm-9 3.75h.008v.008H12v-.008z"
              />
            </svg>
            <p className="mt-3 text-sm font-medium text-foreground">
              Ingestion failed
            </p>
            <p className="mt-1 text-xs text-destructive max-w-sm">
              {state.error}
            </p>
            <button
              onClick={() =>
                setState({
                  status: "idle",
                  totalRecords: 0,
                  processedRecords: 0,
                  chunksTotal: 0,
                  chunksProcessed: 0,
                  jobId: null,
                  error: null,
                  filename: null,
                  conversationsIngested: 0,
                  usersIngested: 0,
                })
              }
              className="mt-4 text-sm text-primary hover:text-primary/80 transition-colors"
            >
              Try again
            </button>
          </div>
        )}
      </div>

      {/* Format info */}
      <div className="mt-8 rounded-lg border border-border bg-card p-5">
        <h3 className="text-sm font-medium text-foreground">
          Expected JSONL Format
        </h3>
        <pre className="mt-3 overflow-x-auto rounded-md bg-muted p-3 text-xs font-mono text-muted-foreground leading-relaxed">
          {`{"user_id": "abc123", "conversation_id": "conv_001", "model": "gpt-4", "language": "English", "conversation_turn": 1, "message_index": 0, "role": "user", "content": "Hello!", "redacted": false}`}
        </pre>
        <p className="mt-3 text-xs text-muted-foreground">
          Each line is one message record. Files are uploaded in chunks of{" "}
          {CHUNK_SIZE} records for reliability.
        </p>
      </div>
    </div>
  );
}
