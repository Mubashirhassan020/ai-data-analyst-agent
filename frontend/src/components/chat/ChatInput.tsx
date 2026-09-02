import { type FormEvent, useState } from "react";
import { Send, Trash2 } from "lucide-react";
import { Button } from "@/components/ui/Button";

export function ChatInput({
  onSend,
  onClear,
  disabled,
}: {
  onSend: (text: string) => void;
  onClear: () => void;
  disabled?: boolean;
}) {
  const [value, setValue] = useState("");

  const submit = (e: FormEvent) => {
    e.preventDefault();
    if (!value.trim()) return;
    onSend(value);
    setValue("");
  };

  return (
    <form onSubmit={submit} className="flex items-end gap-2 border-t border-border p-3">
      <textarea
        value={value}
        onChange={(e) => setValue(e.target.value)}
        onKeyDown={(e) => {
          if (e.key === "Enter" && !e.shiftKey) {
            e.preventDefault();
            submit(e);
          }
        }}
        rows={1}
        placeholder="Ask a question about this dataset…"
        className="flex-1 resize-none rounded-lg border border-border bg-bg px-3 py-2 text-sm placeholder:text-muted focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent/50 max-h-32"
      />
      <Button type="button" variant="ghost" size="md" onClick={onClear} title="Clear conversation">
        <Trash2 className="h-4 w-4" />
      </Button>
      <Button type="submit" disabled={disabled || !value.trim()}>
        <Send className="h-4 w-4" /> Send
      </Button>
    </form>
  );
}
