import { describe, expect, it } from "vitest";
import { formatBytes, formatDate, formatNumber, formatPercent, truncate } from "./format";

describe("formatNumber", () => {
  it("formats a plain integer with thousands separators", () => {
    expect(formatNumber(1234567)).toBe("1,234,567");
  });

  it("returns an em dash for null/undefined/NaN", () => {
    expect(formatNumber(null)).toBe("—");
    expect(formatNumber(undefined)).toBe("—");
    expect(formatNumber(NaN)).toBe("—");
  });

  it("respects the decimals argument", () => {
    expect(formatNumber(3.14159, 2)).toBe("3.14");
  });
});

describe("formatBytes", () => {
  it("keeps small byte counts as-is", () => {
    expect(formatBytes(500)).toBe("500 B");
  });

  it("converts to KB/MB/GB with one decimal", () => {
    expect(formatBytes(2048)).toBe("2.0 KB");
    expect(formatBytes(5 * 1024 * 1024)).toBe("5.0 MB");
  });
});

describe("formatPercent", () => {
  it("formats with one decimal by default", () => {
    expect(formatPercent(12.345)).toBe("12.3%");
  });

  it("returns an em dash for missing values", () => {
    expect(formatPercent(null)).toBe("—");
  });
});

describe("formatDate", () => {
  it("returns an em dash for a missing value", () => {
    expect(formatDate(null)).toBe("—");
    expect(formatDate(undefined)).toBe("—");
  });

  it("returns the original string for an unparseable date", () => {
    expect(formatDate("not-a-date")).toBe("not-a-date");
  });

  it("formats a valid ISO date without throwing", () => {
    expect(formatDate("2026-01-15T10:30:00Z")).not.toBe("—");
  });
});

describe("truncate", () => {
  it("leaves short strings untouched", () => {
    expect(truncate("hello", 10)).toBe("hello");
  });

  it("truncates long strings with an ellipsis, respecting max length", () => {
    const result = truncate("this is a long string", 10);
    expect(result.length).toBe(10);
    expect(result.endsWith("…")).toBe(true);
  });
});
