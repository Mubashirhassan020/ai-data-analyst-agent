import { afterEach } from "vitest";
import { cleanup } from "@testing-library/react";
import "@testing-library/jest-dom/vitest";

// RTL's automatic afterEach(cleanup) only self-registers when it detects a
// global `afterEach` (e.g. via Vitest's `globals: true`). This project keeps
// `globals: false` and imports test APIs explicitly, so cleanup is wired here
// instead — without it, components rendered in one test stay mounted into the
// next, causing "multiple elements found" failures across a test file.
afterEach(() => {
  cleanup();
});
