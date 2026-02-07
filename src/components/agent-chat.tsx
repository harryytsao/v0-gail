"use client";

import { useState, useRef, useEffect } from "react";
import { useChat } from "@ai-sdk/react";
import { DefaultChatTransport } from "ai";
import { useRouter } from "next/navigation";

interface Profile {
  user_id: string;
  total_conversations: number;
  profile_generated: boolean;
}

interface Score {
  dimension: string;
  score: number;
}

function MiniScoreBar({
  dimension,
  score,
}: {
  dimension: string;
  score: number;
}) {
  return (
    <div className="flex items-center gap-2">
      <span className="w-20 text-xs text-muted-foreground truncate">
        {dimension}
      </span>
      <div className="flex-1 h-1 rounded-full bg-muted overflow-hidden">
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

export function AgentChat({
  userId,
  profiles,
  activeScores,
}: {
  userId: string | null;
  profiles: Profile[];
  activeScores: Score[] | null;
}) {
  const [input, setInput] = useState("");
  const [selectedUser, setSelectedUser] = useState(userId ?? "");
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const router = useRouter();

  const { messages, sendMessage, status } = useChat({
    transport: new DefaultChatTransport({
      api: "/api/chat",
      prepareSendMessagesRequest: ({ id, messages }) => ({
        body: {
          messages,
          userId: selectedUser || undefined,
          id,
        },
      }),
    }),
  });

  const isLoading = status === "streaming" || status === "submitted";

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const handleUserChange = (newUserId: string) => {
    setSelectedUser(newUserId);
    if (newUserId) {
      router.push(`/agent?userId=${encodeURIComponent(newUserId)}`);
    } else {
      router.push("/agent");
    }
  };

  return (
    <div className="flex h-full">
      {/* Chat area */}
      <div className="flex flex-1 flex-col">
        {/* Header */}
        <div className="flex items-center justify-between border-b border-border px-6 py-3">
          <div>
            <h2 className="text-sm font-medium text-foreground">
              Adaptive Agent
            </h2>
            <p className="text-xs text-muted-foreground">
              {selectedUser
                ? `Adapting to: ${selectedUser}`
                : "No user profile selected (neutral mode)"}
            </p>
          </div>
          <div className="flex items-center gap-2">
            <select
              value={selectedUser}
              onChange={(e) => handleUserChange(e.target.value)}
              className="h-8 rounded-md border border-border bg-card px-2 text-xs text-foreground focus:outline-none focus:ring-1 focus:ring-ring"
            >
              <option value="">No profile (neutral)</option>
              {profiles.map((p) => (
                <option key={p.user_id} value={p.user_id}>
                  {p.user_id} ({p.total_conversations} conv)
                </option>
              ))}
            </select>
          </div>
        </div>

        {/* Messages */}
        <div className="flex-1 overflow-y-auto px-6 py-4">
          {messages.length === 0 && (
            <div className="flex h-full flex-col items-center justify-center text-center">
              <div className="flex h-12 w-12 items-center justify-center rounded-lg bg-primary/10">
                <svg
                  className="h-6 w-6 text-primary"
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={1.5}
                    d="M8.625 12a.375.375 0 11-.75 0 .375.375 0 01.75 0zm0 0H8.25m4.125 0a.375.375 0 11-.75 0 .375.375 0 01.75 0zm0 0H12m4.125 0a.375.375 0 11-.75 0 .375.375 0 01.75 0zm0 0h-.375M21 12c0 4.556-4.03 8.25-9 8.25a9.764 9.764 0 01-2.555-.337A5.972 5.972 0 015.41 20.97a5.969 5.969 0 01-.474-.065 4.48 4.48 0 00.978-2.025c.09-.457-.133-.901-.467-1.226C3.93 16.178 3 14.189 3 12c0-4.556 4.03-8.25 9-8.25s9 3.694 9 8.25z"
                  />
                </svg>
              </div>
              <h3 className="mt-4 text-sm font-medium text-foreground">
                Start a conversation
              </h3>
              <p className="mt-1 max-w-xs text-xs text-muted-foreground">
                {selectedUser
                  ? `The agent will adapt its behavior based on ${selectedUser}'s profile.`
                  : "Select a profiled user to see adaptive behavior, or chat in neutral mode."}
              </p>
            </div>
          )}

          <div className="flex flex-col gap-4">
            {messages.map((message) => (
              <div
                key={message.id}
                className={`flex ${message.role === "user" ? "justify-end" : "justify-start"}`}
              >
                <div
                  className={`max-w-[75%] rounded-lg px-4 py-2.5 ${
                    message.role === "user"
                      ? "bg-primary text-primary-foreground"
                      : "bg-muted text-foreground"
                  }`}
                >
                  {message.parts.map((part, idx) => {
                    if (part.type === "text") {
                      return (
                        <p
                          key={idx}
                          className="text-sm whitespace-pre-wrap leading-relaxed"
                        >
                          {part.text}
                        </p>
                      );
                    }
                    return null;
                  })}
                </div>
              </div>
            ))}

            {isLoading &&
              messages[messages.length - 1]?.role === "user" && (
                <div className="flex justify-start">
                  <div className="bg-muted rounded-lg px-4 py-2.5">
                    <div className="flex gap-1">
                      <span className="h-2 w-2 animate-bounce rounded-full bg-muted-foreground [animation-delay:0ms]" />
                      <span className="h-2 w-2 animate-bounce rounded-full bg-muted-foreground [animation-delay:150ms]" />
                      <span className="h-2 w-2 animate-bounce rounded-full bg-muted-foreground [animation-delay:300ms]" />
                    </div>
                  </div>
                </div>
              )}
            <div ref={messagesEndRef} />
          </div>
        </div>

        {/* Input */}
        <div className="border-t border-border p-4">
          <form
            onSubmit={(e) => {
              e.preventDefault();
              if (!input.trim() || isLoading) return;
              sendMessage({ text: input });
              setInput("");
            }}
            className="flex gap-2"
          >
            <input
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder="Type a message..."
              disabled={isLoading}
              className="flex-1 h-10 rounded-md border border-border bg-card px-3 text-sm text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-1 focus:ring-ring disabled:opacity-50"
            />
            <button
              type="submit"
              disabled={isLoading || !input.trim()}
              className="flex h-10 w-10 items-center justify-center rounded-md bg-primary text-primary-foreground transition-colors hover:bg-primary/90 disabled:opacity-50"
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
                  d="M6 12L3.269 3.126A59.768 59.768 0 0121.485 12 59.77 59.77 0 013.27 20.876L5.999 12zm0 0h7.5"
                />
              </svg>
              <span className="sr-only">Send message</span>
            </button>
          </form>
        </div>
      </div>

      {/* Profile sidebar */}
      {selectedUser && activeScores && activeScores.length > 0 && (
        <div className="hidden w-72 border-l border-border p-4 lg:block">
          <h3 className="text-xs font-medium uppercase tracking-wider text-muted-foreground">
            Active Profile
          </h3>
          <p className="mt-1 text-sm font-mono text-foreground truncate">
            {selectedUser}
          </p>
          <div className="mt-4 flex flex-col gap-2">
            {activeScores.map((s) => (
              <MiniScoreBar
                key={s.dimension}
                dimension={s.dimension}
                score={s.score}
              />
            ))}
          </div>
          <div className="mt-4 rounded-md bg-muted/50 p-3">
            <p className="text-xs text-muted-foreground leading-relaxed">
              The agent adapts its communication style based on these
              behavioral scores. Higher patience = more detailed responses.
              Higher verbosity = longer explanations.
            </p>
          </div>
        </div>
      )}
    </div>
  );
}
