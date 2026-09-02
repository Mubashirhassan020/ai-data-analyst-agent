import { useEffect, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Moon, Sun } from "lucide-react";
import { api } from "@/services/api";
import { Badge } from "@/components/ui/Badge";

function useTheme() {
  const [dark, setDark] = useState(() => document.documentElement.classList.contains("dark"));
  useEffect(() => {
    document.documentElement.classList.toggle("dark", dark);
  }, [dark]);
  return { dark, toggle: () => setDark((d) => !d) };
}

export function Topbar({ title }: { title?: string }) {
  const { dark, toggle } = useTheme();
  const { data } = useQuery({ queryKey: ["health"], queryFn: api.health, refetchInterval: 30_000 });

  return (
    <header className="h-14 border-b border-border/70 flex items-center justify-between px-6 shrink-0">
      <h1 className="text-sm font-semibold text-fg">{title}</h1>
      <div className="flex items-center gap-3">
        {data && (
          <Badge tone={data.status === "ok" ? "success" : "warning"}>
            backend {data.status === "ok" ? "online" : "degraded"}
          </Badge>
        )}
        {data && !data.llm_configured && <Badge tone="warning">LLM not configured</Badge>}
        <button
          onClick={toggle}
          aria-label="Toggle theme"
          className="h-8 w-8 flex items-center justify-center rounded-lg hover:bg-surface text-muted hover:text-fg transition-colors"
        >
          {dark ? <Sun className="h-4 w-4" /> : <Moon className="h-4 w-4" />}
        </button>
      </div>
    </header>
  );
}
