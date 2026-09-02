import { describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { ChatMessage } from "./ChatMessage";
import type { ChatUiMessage } from "@/hooks/useChat";

describe("ChatMessage", () => {
  it("renders a user message as plain text", () => {
    const message: ChatUiMessage = { id: "1", role: "user", content: "What is the average revenue?" };
    render(<ChatMessage message={message} />);
    expect(screen.getByText("What is the average revenue?")).toBeInTheDocument();
  });

  it("renders assistant markdown content (bold, not raw asterisks)", () => {
    const message: ChatUiMessage = {
      id: "2", role: "assistant", content: "**Answer:** Revenue averages $120.50.",
    };
    render(<ChatMessage message={message} />);
    expect(screen.getByText("Answer:")).toBeInTheDocument();
    expect(screen.getByText(/Revenue averages \$120\.50/)).toBeInTheDocument();
  });

  it("shows a pending indicator instead of content while pending", () => {
    const message: ChatUiMessage = { id: "3", role: "assistant", content: "", pending: true };
    render(<ChatMessage message={message} />);
    expect(screen.getByText("thinking…")).toBeInTheDocument();
  });

  it("shows the error message and a working retry button", async () => {
    const onRetry = vi.fn();
    const message: ChatUiMessage = { id: "4", role: "assistant", content: "", error: "LLM is not configured." };
    render(<ChatMessage message={message} onRetry={onRetry} />);
    expect(screen.getByText("LLM is not configured.")).toBeInTheDocument();
    await userEvent.click(screen.getByText("Retry"));
    expect(onRetry).toHaveBeenCalledTimes(1);
  });

  it("summarizes tool calls and flags a failed one", () => {
    const message: ChatUiMessage = {
      id: "5", role: "assistant", content: "Done.",
      toolCalls: [
        { name: "dataset_schema", arguments: {}, result: { row_count: 10 } },
        { name: "run_query", arguments: { group_by: ["region"] }, result: { error: "Unknown column" } },
      ],
    };
    render(<ChatMessage message={message} />);
    expect(screen.getByText(/2 tool calls used/)).toBeInTheDocument();
    expect(screen.getByText(/error: Unknown column/)).toBeInTheDocument();
  });
});
