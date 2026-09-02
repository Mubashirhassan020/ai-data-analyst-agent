import { Outlet, useMatches } from "react-router-dom";
import { Sidebar } from "@/components/layout/Sidebar";
import { Topbar } from "@/components/layout/Topbar";

interface Handle {
  title?: string;
}

export function AppShell() {
  const matches = useMatches();
  const current = [...matches].reverse().find((m) => (m.handle as Handle | undefined)?.title);
  const title = (current?.handle as Handle | undefined)?.title ?? "Dashboard";

  return (
    <div className="h-screen flex overflow-hidden">
      <Sidebar />
      <div className="flex-1 flex flex-col min-w-0">
        <Topbar title={title} />
        <main className="flex-1 overflow-y-auto">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
