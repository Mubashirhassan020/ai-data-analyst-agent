import { useCallback, useState } from "react";
import { ApiError, api } from "@/services/api";
import type { ChartLikeSpec, ToolCallTrace } from "@/types/api";

export interface ChatUiMessage {
  id: string;
  role: "user" | "assistant";
  content: string;
  toolCalls?: ToolCallTrace[];
  charts?: ChartLikeSpec[];
  error?: string;
  pending?: boolean;
}

function uid(): string {
  return Math.random().toString(36).slice(2);
}

export function useChat(datasetId: string | undefined) {
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [messages, setMessages] = useState<ChatUiMessage[]>([]);
  const [sending, setSending] = useState(false);
  const [llmUnconfigured, setLlmUnconfigured] = useState(false);

  const send = useCallback(
    async (text: string) => {
      if (!datasetId || !text.trim() || sending) return;
      const userMsg: ChatUiMessage = { id: uid(), role: "user", content: text };
      const pendingId = uid();
      setMessages((prev) => [...prev, userMsg, { id: pendingId, role: "assistant", content: "", pending: true }]);
      setSending(true);
      try {
        const res = await api.chat(datasetId, text, sessionId);
        setSessionId(res.session_id);
        setMessages((prev) =>
          prev.map((m) =>
            m.id === pendingId
              ? { id: pendingId, role: "assistant", content: res.message.content, toolCalls: res.tool_calls, charts: res.charts }
              : m
          )
        );
      } catch (e) {
        const err = e as ApiError;
        if (err.code === "llm_not_configured") setLlmUnconfigured(true);
        setMessages((prev) =>
          prev.map((m) =>
            m.id === pendingId
              ? { id: pendingId, role: "assistant", content: "", error: err.message || "Something went wrong." }
              : m
          )
        );
      } finally {
        setSending(false);
      }
    },
    [datasetId, sessionId, sending]
  );

  const retryLast = useCallback(() => {
    const lastUser = [...messages].reverse().find((m) => m.role === "user");
    if (lastUser) {
      setMessages((prev) => prev.filter((m) => !(m.role === "assistant" && m.error)));
      void send(lastUser.content);
    }
  }, [messages, send]);

  const clear = useCallback(() => {
    setMessages([]);
    setSessionId(null);
    setLlmUnconfigured(false);
  }, []);

  return { messages, sending, send, retryLast, clear, sessionId, llmUnconfigured };
}
