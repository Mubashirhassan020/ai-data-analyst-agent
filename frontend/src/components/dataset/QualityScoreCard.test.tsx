import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";
import { QualityScoreCard } from "./QualityScoreCard";
import type { DatasetProfile } from "@/types/api";

/** Matches text split across sibling text nodes within one element, e.g.
 * `{score.toFixed(1)}/10` — RTL's default getByText only matches a single
 * text node, not concatenated siblings, so exact-string matching fails here. */
function getByOwnTextContent(text: string) {
  return screen.getByText((_content, element) => {
    if (!element || element.textContent !== text) return false;
    return Array.from(element.children).every((child) => child.textContent !== text);
  });
}

function makeProfile(overrides: Partial<DatasetProfile> = {}): DatasetProfile {
  return {
    dataset_id: "ds1",
    row_count: 10,
    column_count: 6,
    missing_cells: 1,
    missing_percentage: 1.7,
    duplicate_rows: 0,
    duplicate_percentage: 0,
    columns: [],
    issues: [
      { type: "missing_values", column: "revenue", severity: "medium", message: "'revenue' is missing 10.0% of values." },
    ],
    quality: { overall: 90, completeness: 9.8, missing_values: 8.3, duplicates: 10, data_types: 10, outliers: 6.7 },
    generated_at: "2026-01-01T00:00:00Z",
    cached: false,
    ...overrides,
  };
}

describe("QualityScoreCard", () => {
  it("renders the real overall score", () => {
    render(<QualityScoreCard profile={makeProfile()} />);
    expect(screen.getByText("90")).toBeInTheDocument();
    expect(screen.getByText("/ 100")).toBeInTheDocument();
  });

  it("renders each sub-score with its label", () => {
    render(<QualityScoreCard profile={makeProfile()} />);
    expect(screen.getByText("Completeness")).toBeInTheDocument();
    expect(getByOwnTextContent("9.8/10")).toBeInTheDocument();
    expect(screen.getByText("Outliers")).toBeInTheDocument();
    expect(getByOwnTextContent("6.7/10")).toBeInTheDocument();
  });

  it("renders real issue messages, not placeholders", () => {
    render(<QualityScoreCard profile={makeProfile()} />);
    expect(screen.getByText(/revenue.*missing 10\.0%/)).toBeInTheDocument();
  });

  it("shows a clean-dataset message when there are no issues", () => {
    render(<QualityScoreCard profile={makeProfile({ issues: [] })} />);
    expect(screen.getByText(/no issues detected/i)).toBeInTheDocument();
  });

  it("shows the correct issue count in the heading", () => {
    render(<QualityScoreCard profile={makeProfile()} />);
    expect(screen.getByRole("heading", { name: "Detected Issues (1)" })).toBeInTheDocument();
  });
});
