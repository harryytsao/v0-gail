"use client";

import { Suspense, useState, useRef, useEffect } from "react";
import { useSearchParams } from "next/navigation";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Separator } from "@/components/ui/separator";
import { Skeleton } from "@/components/ui/skeleton";
import { sendChat, type ChatResponse } from "@/lib/api";

interface Message {
  role: "user" | "assistant";
  content: string;
  adaptations?: string[];
}

export default function ChatPage() {
  return (
    <Suspense fallback={<div className="p-6"><Skeleton className="h-8 w-48" /></div>}>
      <ChatPageInner />
    </Suspense>
  );
}

function ChatPageInner() {
  const searchParams = useSearchParams();
  const [userId, setUserId] = useState(searchParams.get("user_id") || "");
  const [userIdInput, setUserIdInput] = useState(
    searchParams.get("user_id") || ""
  );
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [conversationId, setConversationId] = useState<string | null>(null);
  const [sending, setSending] = useState(false);
  const [lastAdaptations, setLastAdaptations] = useState<string[]>([]);
  const [error, setError] = useState<string | null>(null);
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [messages]);

  async function handleSend() {
    if (!input.trim() || !userId.trim() || sending) return;

    const userMessage = input.trim();
    setInput("");
    setError(null);
    setMessages((prev) => [...prev, { role: "user", content: userMessage }]);
    setSending(true);

    try {
      const res = await sendChat(userId, userMessage, conversationId || undefined);
      setConversationId(res.conversation_id);
      setLastAdaptations(res.adaptations_applied);
      setMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          content: res.response,
          adaptations: res.adaptations_applied,
        },
      ]);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Failed to send message");
    } finally {
      setSending(false);
    }
  }

  function handleSetUser() {
    if (userIdInput.trim()) {
      setUserId(userIdInput.trim());
      setMessages([]);
      setConversationId(null);
      setLastAdaptations([]);
      setError(null);
    }
  }

  function handleNewChat() {
    setMessages([]);
    setConversationId(null);
    setLastAdaptations([]);
    setError(null);
  }

  return (
    <div className="flex h-[calc(100vh-2rem)] flex-col gap-4 p-6">
      <div className="flex items-start justify-between">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">
            Adaptive Chat
          </h1>
          <p className="text-sm text-muted-foreground mt-1">
            Chat with the Gail agent as a specific user.
          </p>
        </div>
        {conversationId && (
          <Button variant="outline" size="sm" onClick={handleNewChat}>
            New Chat
          </Button>
        )}
      </div>

      {/* User ID selector */}
      <div className="flex items-center gap-3">
        <Input
          placeholder="Enter user ID (UUID)..."
          value={userIdInput}
          onChange={(e) => setUserIdInput(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && handleSetUser()}
          className="h-9 max-w-md bg-secondary/50 font-mono text-xs"
        />
        <Button variant="secondary" size="sm" onClick={handleSetUser}>
          Set User
        </Button>
        {userId && (
          <span className="text-xs text-muted-foreground">
            Active: <span className="font-mono">{userId.slice(0, 8)}...</span>
          </span>
        )}
      </div>

      {error && (
        <div className="rounded-lg border border-destructive/50 bg-destructive/10 p-3 text-sm text-destructive">
          {error}
        </div>
      )}

      {/* Chat area */}
      <div className="flex flex-1 gap-4 min-h-0">
        {/* Messages */}
        <Card className="flex-1 flex flex-col">
          <div ref={scrollRef} className="flex-1 overflow-y-auto p-4 space-y-4">
            {messages.length === 0 ? (
              <div className="flex h-full items-center justify-center">
                <p className="text-sm text-muted-foreground">
                  {userId
                    ? "Send a message to start chatting."
                    : "Set a user ID to begin."}
                </p>
              </div>
            ) : (
              messages.map((msg, i) => (
                <div
                  key={i}
                  className={`flex ${msg.role === "user" ? "justify-end" : "justify-start"}`}
                >
                  <div
                    className={`max-w-[80%] rounded-lg px-4 py-2.5 text-sm ${
                      msg.role === "user"
                        ? "bg-foreground text-background"
                        : "bg-secondary text-foreground"
                    }`}
                  >
                    <p className="whitespace-pre-wrap">{msg.content}</p>
                  </div>
                </div>
              ))
            )}
            {sending && (
              <div className="flex justify-start">
                <div className="bg-secondary rounded-lg px-4 py-2.5">
                  <div className="flex gap-1">
                    <span className="w-1.5 h-1.5 rounded-full bg-muted-foreground animate-bounce" />
                    <span className="w-1.5 h-1.5 rounded-full bg-muted-foreground animate-bounce [animation-delay:150ms]" />
                    <span className="w-1.5 h-1.5 rounded-full bg-muted-foreground animate-bounce [animation-delay:300ms]" />
                  </div>
                </div>
              </div>
            )}
          </div>
          <Separator />
          <div className="p-4">
            <div className="flex gap-2">
              <Input
                placeholder={
                  userId ? "Type a message..." : "Set a user ID first"
                }
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && !e.shiftKey && handleSend()}
                disabled={!userId || sending}
                className="h-10 bg-secondary/50"
              />
              <Button
                onClick={handleSend}
                disabled={!userId || !input.trim() || sending}
                size="sm"
                className="h-10 px-6"
              >
                Send
              </Button>
            </div>
          </div>
        </Card>

        {/* Adaptations panel */}
        <Card className="w-72 shrink-0 hidden lg:flex flex-col">
          <CardHeader className="pb-3">
            <CardTitle className="text-xs font-medium uppercase tracking-wider text-muted-foreground">
              Adaptations
            </CardTitle>
          </CardHeader>
          <CardContent className="flex-1 overflow-auto">
            {lastAdaptations.length > 0 ? (
              <ul className="space-y-2">
                {lastAdaptations.map((a, i) => (
                  <li
                    key={i}
                    className="flex items-start gap-2 text-xs text-muted-foreground"
                  >
                    <span className="mt-1.5 h-1 w-1 rounded-full bg-chart-1 shrink-0" />
                    {a}
                  </li>
                ))}
              </ul>
            ) : (
              <p className="text-xs text-muted-foreground">
                Adaptations will appear here after the first response.
              </p>
            )}
          </CardContent>
          {conversationId && (
            <div className="border-t border-border p-3">
              <div className="text-[10px] text-muted-foreground font-mono truncate">
                Conv: {conversationId.slice(0, 8)}...
              </div>
            </div>
          )}
        </Card>
      </div>
    </div>
  );
}
