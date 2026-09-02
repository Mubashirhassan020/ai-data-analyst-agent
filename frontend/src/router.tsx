import { createBrowserRouter } from "react-router-dom";
import { AppShell } from "@/components/layout/AppShell";
import Landing from "@/pages/Landing";
import Dashboard from "@/pages/Dashboard";
import Datasets from "@/pages/Datasets";
import DatasetDetail from "@/pages/DatasetDetail";
import AIAnalyst from "@/pages/AIAnalyst";
import Reports from "@/pages/Reports";
import Settings from "@/pages/Settings";

export const router = createBrowserRouter([
  { path: "/", element: <Landing /> },
  {
    path: "/app",
    element: <AppShell />,
    children: [
      { index: true, element: <Dashboard />, handle: { title: "Dashboard" } },
      { path: "datasets", element: <Datasets />, handle: { title: "Datasets" } },
      { path: "datasets/:id", element: <DatasetDetail />, handle: { title: "Dataset" } },
      { path: "ai", element: <AIAnalyst />, handle: { title: "AI Analyst" } },
      { path: "reports", element: <Reports />, handle: { title: "Reports" } },
      { path: "settings", element: <Settings />, handle: { title: "Settings" } },
    ],
  },
]);
