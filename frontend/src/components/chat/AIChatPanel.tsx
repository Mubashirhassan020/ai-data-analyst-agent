import { useEffect, useRef } from "react";
import { AlertTriangle, Sparkles } from "lucide-react";
import { useChat } from "@/hooks/useChat";
import { ChatMessage } from "@/components/chat/ChatMessage";
import { ChatInput } from "@/components/chat/ChatInput";
import { SuggestedQuestions } from "@/components/chat/SuggestedQuestions";

export function AIChatPanel({ datasetId }: { datasetId: string }) {
  const { messages, send, retryLast, clear, sending, llmUnconfigured } = useChat(datasetId);
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  return (
    <div className="flex flex-col h-[calc(100vh-8.5rem)] rounded-xl border border-border bg-surface/40 overflow-hidden">
      <div className="flex-1 overflow-y-auto p-4 space-y-5">
        {messages.length === 0 ? (
          <div className="h-full flex flex-col items-center justify-center text-center px-6">
            <div className="h-11 w-11 rounded-full bg-accent/10 flex items-center justify-center text-accent mb-3">
              <Sparkles className="h-5 w-5" />
            </div>
            <h3 className="text-sm font-semibold">Ask the AI analyst</h3>
            <p className="text-xs text-muted mt-1 max-w-sm">
              Every answer is grounded in real computations run against this dataset — never invented numbers.
            </p>
            <div className="mt-4">
              <SuggestedQuestions onPick={send} />
            </div>
          </div>
        ) : (
          <>
            {messages.map((m) => (
              <ChatMessage key={m.id} message={m} onRetry={m.error ? retryLast : undefined} />
            ))}
            <div ref={bottomRef} />
          </>
        )}
      </div>

      {llmUnconfigured && (
        <div className="flex items-center gap-2 px-4 py-2 bg-amber-500/10 border-t border-amber-500/20 text-xs text-amber-300">
          <AlertTriangle className="h-3.5 w-3.5 shrink-0" />
          The AI provider isn't configured on the server yet (set LLM_API_KEY and LLM_MODEL) — chat can't run until then.
        </div>
      )}

      <ChatInput onSend={send} onClear={clear} disabled={sending} />
    </div>
  );
}
