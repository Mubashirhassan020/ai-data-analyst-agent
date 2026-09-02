import { NavLink } from "react-router-dom";
import { Activity, Database, LayoutDashboard, MessageSquare, Settings, Sparkles, FileText } from "lucide-react";
import { cn } from "@/lib/utils";

const items = [
  { to: "/app", label: "Dashboard", icon: LayoutDashboard, end: true },
  { to: "/app/datasets", label: "Datasets", icon: Database },
  { to: "/app/ai", label: "AI Analyst", icon: MessageSquare },
  { to: "/app/reports", label: "Reports", icon: FileText },
  { to: "/app/settings", label: "Settings", icon: Settings },
];

export function Sidebar() {
  return (
    <aside className="w-60 shrink-0 border-r border-border/70 bg-surface/40 flex flex-col h-full">
      <div className="h-14 flex items-center gap-2 px-5 border-b border-border/70">
        <Activity className="h-5 w-5 text-accent" />
        <span className="font-semibold text-sm tracking-tight">AI Data Analyst</span>
      </div>
      <nav className="flex-1 px-3 py-4 space-y-1">
        {items.map(({ to, label, icon: Icon, end }) => (
          <NavLink
            key={to}
            to={to}
            end={end}
            className={({ isActive }) =>
              cn(
                "flex items-center gap-2.5 rounded-lg px-3 py-2 text-sm font-medium transition-colors",
                isActive ? "bg-accent/10 text-accent" : "text-muted hover:text-fg hover:bg-border/30"
              )
            }
          >
            <Icon className="h-4 w-4" />
            {label}
          </NavLink>
        ))}
      </nav>
      <div className="px-3 py-4 border-t border-border/70">
        <div className="flex items-center gap-2 px-3 py-2 rounded-lg bg-accent/5 text-xs text-muted">
          <Sparkles className="h-3.5 w-3.5 text-accent shrink-0" />
          <span>Tool-grounded AI analysis — no invented numbers.</span>
        </div>
      </div>
    </aside>
  );
}
