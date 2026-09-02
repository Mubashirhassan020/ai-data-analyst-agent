import { afterEach, describe, expect, it, vi } from "vitest";
import { act, renderHook, waitFor } from "@testing-library/react";
import { useChat } from "./useChat";
import { ApiError, api } from "@/services/api";

vi.mock("@/services/api", async () => {
  const actual = await vi.importActual<typeof import("@/services/api")>("@/services/api");
  return { ...actual, api: { ...actual.api, chat: vi.fn() } };
});

const mockedChat = vi.mocked(api.chat);

afterEach(() => {
  vi.clearAllMocks();
});

describe("useChat", () => {
  it("appends a pending assistant message immediately, then resolves it", async () => {
    mockedChat.mockResolvedValueOnce({
      session_id: "s1",
      message: { role: "assistant", content: "**Answer:** 10 rows." },
      tool_calls: [],
      charts: [],
    });

    const { result } = renderHook(() => useChat("ds1"));

    act(() => {
      void result.current.send("How many rows?");
    });

    // User message + pending assistant placeholder appear synchronously.
    expect(result.current.messages).toHaveLength(2);
    expect(result.current.messages[0]).toMatchObject({ role: "user", content: "How many rows?" });
    expect(result.current.messages[1]).toMatchObject({ role: "assistant", pending: true });

    await waitFor(() => expect(result.current.sending).toBe(false));

    expect(result.current.messages[1]).toMatchObject({
      role: "assistant", content: "**Answer:** 10 rows.",
    });
    expect(result.current.messages[1].pending).toBeFalsy();
    expect(result.current.sessionId).toBe("s1");
  });

  it("reuses the session id from the first response on the next send", async () => {
    mockedChat.mockResolvedValueOnce({
      session_id: "s1", message: { role: "assistant", content: "first" }, tool_calls: [], charts: [],
    });
    const { result } = renderHook(() => useChat("ds1"));
    await act(async () => {
      await result.current.send("first question");
    });

    mockedChat.mockResolvedValueOnce({
      session_id: "s1", message: { role: "assistant", content: "second" }, tool_calls: [], charts: [],
    });
    await act(async () => {
      await result.current.send("second question");
    });

    expect(mockedChat).toHaveBeenLastCalledWith("ds1", "second question", "s1");
  });

  it("surfaces a normal API error on the message and flags llmUnconfigured for that code", async () => {
    mockedChat.mockRejectedValueOnce(new ApiError(503, "llm_not_configured", "LLM is not configured."));

    const { result } = renderHook(() => useChat("ds1"));
    await act(async () => {
      await result.current.send("hi");
    });

    expect(result.current.llmUnconfigured).toBe(true);
    expect(result.current.messages[1]).toMatchObject({ error: "LLM is not configured." });
  });

  it("retryLast resends the last user message and clears the error", async () => {
    mockedChat.mockRejectedValueOnce(new ApiError(500, "internal_error", "boom"));
    const { result } = renderHook(() => useChat("ds1"));
    await act(async () => {
      await result.current.send("retry me");
    });
    expect(result.current.messages.some((m) => m.error)).toBe(true);

    mockedChat.mockResolvedValueOnce({
      session_id: "s2", message: { role: "assistant", content: "worked this time" }, tool_calls: [], charts: [],
    });
    await act(async () => {
      await result.current.retryLast();
    });

    expect(result.current.messages.some((m) => m.error)).toBe(false);
    expect(result.current.messages.some((m) => m.content === "worked this time")).toBe(true);
  });

  it("clear resets messages, session, and the unconfigured flag", async () => {
    mockedChat.mockRejectedValueOnce(new ApiError(503, "llm_not_configured", "not configured"));
    const { result } = renderHook(() => useChat("ds1"));
    await act(async () => {
      await result.current.send("hi");
    });
    expect(result.current.messages).not.toHaveLength(0);

    act(() => {
      result.current.clear();
    });

    expect(result.current.messages).toHaveLength(0);
    expect(result.current.sessionId).toBeNull();
    expect(result.current.llmUnconfigured).toBe(false);
  });

  it("does nothing when sending an empty/whitespace message", () => {
    const { result } = renderHook(() => useChat("ds1"));
    act(() => {
      void result.current.send("   ");
    });
    expect(result.current.messages).toHaveLength(0);
    expect(mockedChat).not.toHaveBeenCalled();
  });

  it("does nothing when no dataset id is set", () => {
    const { result } = renderHook(() => useChat(undefined));
    act(() => {
      void result.current.send("hi");
    });
    expect(result.current.messages).toHaveLength(0);
    expect(mockedChat).not.toHaveBeenCalled();
  });
});
