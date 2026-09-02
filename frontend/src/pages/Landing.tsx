import { Link } from "react-router-dom";
import {
  Activity,
  BarChart3,
  Bot,
  Database,
  FileText,
  LineChart,
  ShieldCheck,
  Sparkles,
  UploadCloud,
  Wand2,
} from "lucide-react";
import { Button } from "@/components/ui/Button";
import { Card, CardContent } from "@/components/ui/Card";

const features = [
  { icon: UploadCloud, title: "Upload anything tabular", desc: "CSV or Excel, validated and profiled automatically on upload." },
  { icon: BarChart3, title: "Automated EDA", desc: "Type-aware charts generated from your actual columns — no meaningless plots." },
  { icon: Bot, title: "Tool-grounded AI analyst", desc: "The AI calls real pandas/statistics tools — it never guesses a number." },
  { icon: ShieldCheck, title: "Data quality scoring", desc: "Missing values, duplicates, outliers, and type issues surfaced automatically." },
  { icon: LineChart, title: "Manual analysis builder", desc: "Chart type, aggregation, group-by and filters — no AI required." },
  { icon: FileText, title: "Exportable reports", desc: "Executive summaries with your real statistics and visualizations." },
];

const steps = [
  { n: "01", title: "Upload your dataset", desc: "Drop a CSV or Excel file. It's validated, parsed, and cached as Parquet." },
  { n: "02", title: "Automated profiling", desc: "Types, statistics, and a data-quality score are computed immediately." },
  { n: "03", title: "Explore & ask questions", desc: "Browse auto-generated charts, or ask the AI analyst in plain English." },
  { n: "04", title: "Get grounded answers", desc: "Every number the AI states came from a real tool call against your data." },
];

export default function Landing() {
  return (
    <div className="min-h-screen">
      <header className="border-b border-border/70">
        <div className="max-w-6xl mx-auto px-6 h-16 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Activity className="h-5 w-5 text-accent" />
            <span className="font-semibold tracking-tight">AI Data Analyst Agent</span>
          </div>
          <Link to="/app">
            <Button size="sm">Open Dashboard</Button>
          </Link>
        </div>
      </header>

      <section className="max-w-4xl mx-auto px-6 pt-24 pb-16 text-center">
        <div className="inline-flex items-center gap-1.5 rounded-full border border-border px-3 py-1 text-xs text-muted mb-6">
          <Sparkles className="h-3.5 w-3.5 text-accent" /> Grounded AI analysis — no hallucinated numbers
        </div>
        <h1 className="text-5xl font-semibold tracking-tight leading-[1.1]">
          Turn your data into <span className="text-accent">actionable insights</span>
        </h1>
        <p className="text-muted mt-5 text-lg max-w-2xl mx-auto leading-relaxed">
          Upload your dataset, ask questions in natural language, generate visualizations, discover
          patterns, and make data-driven decisions with an AI-powered analyst.
        </p>
        <div className="flex items-center justify-center gap-3 mt-8">
          <Link to="/app/datasets">
            <Button size="lg">
              <UploadCloud className="h-4 w-4" /> Upload Dataset
            </Button>
          </Link>
          <Link to="/app">
            <Button size="lg" variant="secondary">
              <Wand2 className="h-4 w-4" /> Explore Dashboard
            </Button>
          </Link>
        </div>
      </section>

      <section className="max-w-6xl mx-auto px-6 py-16">
        <h2 className="text-2xl font-semibold text-center mb-2">Everything an analyst needs</h2>
        <p className="text-muted text-center mb-10">Automated where it saves time, manual where you want control.</p>
        <div className="grid md:grid-cols-3 gap-4">
          {features.map(({ icon: Icon, title, desc }) => (
            <Card key={title}>
              <CardContent className="pt-5">
                <div className="h-9 w-9 rounded-lg bg-accent/10 flex items-center justify-center text-accent mb-3">
                  <Icon className="h-4.5 w-4.5" />
                </div>
                <h3 className="text-sm font-semibold mb-1">{title}</h3>
                <p className="text-xs text-muted leading-relaxed">{desc}</p>
              </CardContent>
            </Card>
          ))}
        </div>
      </section>

      <section className="border-y border-border/70 bg-surface/30">
        <div className="max-w-6xl mx-auto px-6 py-16">
          <h2 className="text-2xl font-semibold text-center mb-10">How it works</h2>
          <div className="grid md:grid-cols-4 gap-6">
            {steps.map(({ n, title, desc }) => (
              <div key={n}>
                <div className="text-3xl font-bold text-accent/40 mb-2">{n}</div>
                <h3 className="text-sm font-semibold mb-1">{title}</h3>
                <p className="text-xs text-muted leading-relaxed">{desc}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      <section className="max-w-4xl mx-auto px-6 py-16">
        <h2 className="text-2xl font-semibold text-center mb-8">Built with real AI engineering</h2>
        <div className="grid sm:grid-cols-2 gap-3 text-sm">
          {[
            "The LLM decides which tool to call — it never fabricates a statistic.",
            "Pandas, correlation, and outlier detection run as deterministic tools.",
            "Every chat answer cites the actual computed evidence behind it.",
            "If the data can't answer a question, the agent says so plainly.",
          ].map((line) => (
            <div key={line} className="flex items-start gap-2 rounded-lg border border-border bg-surface px-4 py-3">
              <ShieldCheck className="h-4 w-4 text-accent shrink-0 mt-0.5" />
              <span className="text-muted">{line}</span>
            </div>
          ))}
        </div>
      </section>

      <footer className="border-t border-border/70 py-8 text-center text-xs text-muted">
        <div className="flex items-center justify-center gap-1.5">
          <Database className="h-3.5 w-3.5" /> AI Data Analyst Agent — an open-source portfolio project
        </div>
      </footer>
    </div>
  );
}
