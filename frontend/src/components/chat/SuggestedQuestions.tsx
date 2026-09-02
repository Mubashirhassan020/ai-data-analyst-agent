const QUESTIONS = [
  "Summarize this dataset",
  "Find important trends",
  "Find anomalies",
  "What are the top-performing categories?",
  "Create a revenue analysis",
];

export function SuggestedQuestions({ onPick }: { onPick: (q: string) => void }) {
  return (
    <div className="flex flex-wrap gap-2">
      {QUESTIONS.map((q) => (
        <button
          key={q}
          onClick={() => onPick(q)}
          className="text-xs rounded-full border border-border px-3 py-1.5 text-muted hover:text-fg hover:border-accent/50 transition-colors"
        >
          {q}
        </button>
      ))}
    </div>
  );
}
