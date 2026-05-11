"use client";

import {
  useState,
  useEffect,
  useRef,
  useCallback,
  KeyboardEvent,
} from "react";
import { useParams } from "next/navigation";
import { format } from "date-fns";
import { Send, Trash2, Bot, User, Sparkles } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
  AlertDialogTrigger,
} from "@/components/ui/alert-dialog";
import { chatApi } from "@/lib/api/endpoints";
import type { ChatResponse, SuggestedAction } from "@/lib/api/types";
import { toast } from "sonner";
import { cn } from "@/lib/utils";

// ─── Types ────────────────────────────────────────────────────────────────────

interface Message {
  id: string;
  role: "user" | "assistant";
  content: string;
  timestamp: string;
  suggested_actions?: SuggestedAction[];
  references?: string[];
}

// ─── Helpers ──────────────────────────────────────────────────────────────────

let _seq = 0;
function uid() {
  return `msg-${Date.now()}-${++_seq}`;
}

function formatTs(ts: string) {
  try {
    return format(new Date(ts), "h:mm a");
  } catch {
    return "";
  }
}

// ─── Typing indicator ─────────────────────────────────────────────────────────

function TypingIndicator() {
  return (
    <div className="flex items-end gap-2">
      <div className="flex h-8 w-8 flex-shrink-0 items-center justify-center rounded-full bg-accent-violet/10 text-accent-violet">
        <Bot className="h-4 w-4" />
      </div>
      <div className="rounded-2xl rounded-bl-sm border border-white/8 bg-white/4 px-4 py-3 backdrop-blur-sm">
        <span className="flex gap-1.5 items-center h-4">
          <span className="h-2 w-2 rounded-full bg-accent-violet animate-bounce [animation-delay:0ms]" />
          <span className="h-2 w-2 rounded-full bg-accent-violet animate-bounce [animation-delay:150ms]" />
          <span className="h-2 w-2 rounded-full bg-accent-violet animate-bounce [animation-delay:300ms]" />
        </span>
      </div>
    </div>
  );
}

// ─── Message bubble ───────────────────────────────────────────────────────────

function MessageBubble({
  msg,
  onSuggestedAction,
}: {
  msg: Message;
  onSuggestedAction: (text: string) => void;
}) {
  const isUser = msg.role === "user";

  return (
    <div
      className={cn(
        "flex items-end gap-2",
        isUser ? "flex-row-reverse" : "flex-row",
      )}
    >
      {/* Avatar */}
      <div
        className={cn(
          "flex h-8 w-8 flex-shrink-0 items-center justify-center rounded-full",
          isUser
            ? "bg-accent-violet/20 text-accent-violet"
            : "bg-accent-violet/10 text-accent-violet",
        )}
      >
        {isUser ? <User className="h-4 w-4" /> : <Bot className="h-4 w-4" />}
      </div>

      {/* Bubble + actions */}
      <div
        className={cn(
          "flex max-w-[75%] flex-col gap-2",
          isUser ? "items-end" : "items-start",
        )}
      >
        <div
          className={cn(
            "rounded-2xl px-4 py-3 text-sm leading-relaxed",
            isUser
              ? "rounded-br-sm bg-accent-violet/20 text-foreground"
              : "rounded-bl-sm border border-white/8 bg-white/4 text-foreground backdrop-blur-sm",
          )}
        >
          <p className="whitespace-pre-wrap break-words">{msg.content}</p>
        </div>

        <span className="text-[10px] text-muted-foreground font-mono px-1">
          {formatTs(msg.timestamp)}
        </span>

        {/* References */}
        {!isUser && msg.references && msg.references.length > 0 && (
          <div className="flex flex-wrap gap-1.5">
            {msg.references.map((ref, i) => (
              <span
                key={i}
                className="rounded-md bg-white/6 px-2 py-0.5 text-[10px] font-mono text-white/50"
              >
                {ref}
              </span>
            ))}
          </div>
        )}

        {/* Suggested actions */}
        {!isUser &&
          msg.suggested_actions &&
          msg.suggested_actions.length > 0 && (
            <div className="flex flex-wrap gap-2 mt-1">
              {msg.suggested_actions.map((sa, i) => (
                <button
                  key={i}
                  type="button"
                  onClick={() => onSuggestedAction(sa.label)}
                  className={cn(
                    "inline-flex items-center gap-1.5 rounded-full px-3 py-1 text-xs font-medium",
                    "border border-accent-violet/30 bg-accent-violet/8 text-accent-violet",
                    "hover:border-accent-violet/60 hover:bg-accent-violet/15 transition-colors",
                  )}
                >
                  <Sparkles className="h-3 w-3 flex-shrink-0" />
                  {sa.label}
                </button>
              ))}
            </div>
          )}
      </div>
    </div>
  );
}

// ─── Page ─────────────────────────────────────────────────────────────────────

export default function ChatPage() {
  const { projectId } = useParams<{ projectId: string }>();
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [historyLoading, setHistoryLoading] = useState(true);
  const bottomRef = useRef<HTMLDivElement>(null);

  // Load history on mount
  useEffect(() => {
    let cancelled = false;
    async function load() {
      try {
        const history = await chatApi.history(projectId);
        if (cancelled) return;
        setMessages(
          history.messages.map((m) => ({
            id: uid(),
            role: m.role as "user" | "assistant",
            content: m.content,
            timestamp: m.timestamp,
          })),
        );
      } catch {
        // Empty history is fine — start fresh
      } finally {
        if (!cancelled) setHistoryLoading(false);
      }
    }
    void load();
    return () => {
      cancelled = true;
    };
  }, [projectId]);

  // Scroll to bottom whenever messages change
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, loading]);

  const sendMessage = useCallback(
    async (text: string) => {
      const trimmed = text.trim();
      if (!trimmed || loading) return;

      setInput("");

      // Optimistic user bubble
      const userMsg: Message = {
        id: uid(),
        role: "user",
        content: trimmed,
        timestamp: new Date().toISOString(),
      };
      setMessages((prev) => [...prev, userMsg]);
      setLoading(true);

      try {
        const res = await chatApi.send({ project_id: projectId, message: trimmed });
        const chatRes = res as unknown as ChatResponse;
        const assistantMsg: Message = {
          id: uid(),
          role: "assistant",
          content: chatRes.reply,
          timestamp: new Date().toISOString(),
          suggested_actions: chatRes.suggested_actions ?? [],
          references: chatRes.references ?? [],
        };
        setMessages((prev) => [...prev, assistantMsg]);
      } catch (e) {
        toast.error(e instanceof Error ? e.message : "Failed to send message.");
        // Remove the optimistic user bubble on error
        setMessages((prev) => prev.filter((m) => m.id !== userMsg.id));
      } finally {
        setLoading(false);
      }
    },
    [projectId, loading],
  );

  const handleKeyDown = (e: KeyboardEvent<HTMLInputElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      void sendMessage(input);
    }
  };

  const handleClear = async () => {
    try {
      await chatApi.clear(projectId);
      setMessages([]);
      toast.success("Chat history cleared.");
    } catch (e) {
      toast.error(e instanceof Error ? e.message : "Failed to clear history.");
    }
  };

  return (
    <div className="flex h-full flex-col overflow-hidden">
      {/* Header */}
      <div className="flex flex-shrink-0 items-center justify-between border-b border-white/8 px-6 py-4">
        <div>
          <h1 className="font-display italic text-2xl font-bold text-foreground">
            Ask Anything
          </h1>
          <p className="text-sm text-muted-foreground">
            Conversational follow-up on your data, model, and results.
          </p>
        </div>

        <AlertDialog>
          <AlertDialogTrigger
            disabled={messages.length === 0}
            className={cn(
              "inline-flex items-center justify-center gap-2 rounded-md border px-3 py-1.5 text-sm font-medium transition-colors",
              "border-red-500/30 text-red-400 hover:border-red-500/60 hover:bg-red-500/8 hover:text-red-300",
              "disabled:pointer-events-none disabled:opacity-50",
            )}
          >
            <Trash2 className="h-4 w-4" />
            Clear Chat
          </AlertDialogTrigger>
          <AlertDialogContent className="border-white/10 bg-[#0c0f2d]">
            <AlertDialogHeader>
              <AlertDialogTitle className="text-foreground">
                Clear chat history?
              </AlertDialogTitle>
              <AlertDialogDescription className="text-muted-foreground">
                This permanently deletes all messages in this project&apos;s
                chat. This action cannot be undone.
              </AlertDialogDescription>
            </AlertDialogHeader>
            <AlertDialogFooter>
              <AlertDialogCancel className="border-white/10 hover:border-white/20">
                Cancel
              </AlertDialogCancel>
              <AlertDialogAction
                onClick={() => void handleClear()}
                className="bg-red-600 hover:bg-red-700 text-white"
              >
                Clear
              </AlertDialogAction>
            </AlertDialogFooter>
          </AlertDialogContent>
        </AlertDialog>
      </div>

      {/* Message list */}
      <div className="flex-1 overflow-y-auto px-6 py-6">
        {historyLoading ? (
          <div className="flex h-full items-center justify-center">
            <div className="flex flex-col items-center gap-3">
              <div className="h-8 w-8 rounded-full border-2 border-accent-violet border-t-transparent animate-spin" />
              <p className="text-sm text-muted-foreground">Loading history…</p>
            </div>
          </div>
        ) : messages.length === 0 && !loading ? (
          /* Empty state */
          <div className="flex h-full flex-col items-center justify-center gap-4 text-center">
            <div className="rounded-2xl bg-accent-violet/10 p-5">
              <Bot className="h-10 w-10 text-accent-violet" />
            </div>
            <div>
              <p className="font-display italic text-xl font-semibold text-foreground">
                No messages yet
              </p>
              <p className="mt-1 text-sm text-muted-foreground max-w-xs">
                Ask anything about your dataset, model performance, feature
                importance, or next steps.
              </p>
            </div>
            {/* Quick starters */}
            <div className="flex flex-wrap justify-center gap-2 mt-2">
              {[
                "Summarize model performance",
                "Which features matter most?",
                "Suggest next steps",
                "Explain top prediction",
              ].map((s) => (
                <button
                  key={s}
                  type="button"
                  onClick={() => void sendMessage(s)}
                  className={cn(
                    "rounded-full px-3 py-1.5 text-xs font-medium",
                    "border border-accent-violet/30 bg-accent-violet/8 text-accent-violet",
                    "hover:border-accent-violet/60 hover:bg-accent-violet/15 transition-colors",
                  )}
                >
                  {s}
                </button>
              ))}
            </div>
          </div>
        ) : (
          <div className="flex flex-col gap-5 max-w-3xl mx-auto">
            {messages.map((msg) => (
              <MessageBubble
                key={msg.id}
                msg={msg}
                onSuggestedAction={(text) => void sendMessage(text)}
              />
            ))}
            {loading && <TypingIndicator />}
            <div ref={bottomRef} />
          </div>
        )}
      </div>

      {/* Input bar */}
      <div className="flex-shrink-0 border-t border-white/8 bg-[rgba(7,9,26,0.8)] px-6 py-4 backdrop-blur-md">
        <div className="mx-auto flex max-w-3xl items-center gap-3">
          <Input
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Ask anything about your data, model, or results…"
            disabled={loading || historyLoading}
            className="flex-1 bg-white/4 border-white/10 text-sm placeholder:text-white/30 focus-visible:border-accent-violet/50"
          />
          <Button
            onClick={() => void sendMessage(input)}
            disabled={loading || historyLoading || !input.trim()}
            className="btn-glow flex-shrink-0"
            size="icon"
            aria-label="Send message"
          >
            <Send className="h-4 w-4" />
          </Button>
        </div>
      </div>
    </div>
  );
}
