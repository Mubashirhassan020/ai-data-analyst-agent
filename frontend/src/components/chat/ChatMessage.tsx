import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { AlertCircle, Bot, User, Wrench } from "lucide-react";
import type { ChatUiMessage } from "@/hooks/useChat";
import { PlotlyChart } from "@/components/charts/PlotlyChart";
import { cn } from "@/lib/utils";

export function ChatMessage({ message, onRetry }: { message: ChatUiMessage; onRetry?: () => void }) {
  const isUser = message.role === "user";

  return (
    <div className={cn("flex gap-3", isUser && "flex-row-reverse")}>
      <div
        className={cn(
          "h-7 w-7 rounded-full flex items-center justify-center shrink-0 mt-0.5",
          isUser ? "bg-accent/15 text-accent" : "bg-border/50 text-muted"
        )}
      >
        {isUser ? <User className="h-3.5 w-3.5" /> : <Bot className="h-3.5 w-3.5" />}
      </div>

      <div className={cn("flex-1 min-w-0 space-y-2", isUser && "flex flex-col items-end")}>
        {message.pending ? (
          <div className="inline-flex items-center gap-1.5 text-xs text-muted bg-surface rounded-lg px-3 py-2 border border-border">
            <span className="flex gap-1">
              <span className="h-1.5 w-1.5 rounded-full bg-muted animate-bounce [animation-delay:-0.3s]" />
              <span className="h-1.5 w-1.5 rounded-full bg-muted animate-bounce [animation-delay:-0.15s]" />
              <span className="h-1.5 w-1.5 rounded-full bg-muted animate-bounce" />
            </span>
            thinking…
          </div>
        ) : message.error ? (
          <div className="max-w-[85%] rounded-lg border border-red-500/30 bg-red-500/5 px-3 py-2 text-xs text-red-300 space-y-2">
            <div className="flex items-center gap-1.5">
              <AlertCircle className="h-3.5 w-3.5" /> {message.error}
            </div>
            {onRetry && (
              <button onClick={onRetry} className="underline text-red-300/90 hover:text-red-200">
                Retry
              </button>
            )}
          </div>
        ) : (
          <div
            className={cn(
              "max-w-[85%] rounded-lg px-3.5 py-2.5 text-sm leading-relaxed",
              isUser ? "bg-accent text-white" : "bg-surface border border-border"
            )}
          >
            {isUser ? (
              message.content
            ) : (
              <div className="prose-chat">
                <ReactMarkdown remarkPlugins={[remarkGfm]}>{message.content}</ReactMarkdown>
              </div>
            )}
          </div>
        )}

        {message.toolCalls && message.toolCalls.length > 0 && (
          <details className="text-[11px] text-muted max-w-[85%]">
            <summary className="cursor-pointer inline-flex items-center gap-1 hover:text-fg">
              <Wrench className="h-3 w-3" /> {message.toolCalls.length} tool call
              {message.toolCalls.length === 1 ? "" : "s"} used
            </summary>
            <ul className="mt-1.5 space-y-1 pl-4">
              {message.toolCalls.map((tc, i) => (
                <li key={i} className="font-mono">
                  {tc.name}({Object.keys(tc.arguments).length ? JSON.stringify(tc.arguments) : ""})
                  {"error" in tc.result && <span className="text-red-400"> — error: {String(tc.result.error)}</span>}
                </li>
              ))}
            </ul>
          </details>
        )}

        {message.charts?.map((chart, i) => (
          <div key={i} className="w-full max-w-2xl rounded-lg border border-border bg-surface p-2">
            <PlotlyChart data={chart.data} layout={chart.layout} height={280} />
          </div>
        ))}
      </div>
    </div>
  );
}
