import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import SummaryPanel from "./SummaryPanel";
import type { CandidateSummary } from "../types";

const summary: CandidateSummary = {
  headline: "Graduate engineer.",
  key_skills: ["Python", "React"],
  experience_highlights: ["Built a dashboard"],
  injection_detected: false,
  flags: [],
};

test("shows the backend's message when generation fails, and re-enables the button", async () => {
  const generate = vi.fn().mockRejectedValue(new Error("Resume text looks garbled (mostly symbols)."));
  render(<SummaryPanel summary={null} generatedAt={null} hasResume generate={generate} />);

  await userEvent.click(screen.getByRole("button", { name: /generate summary/i }));

  expect(await screen.findByRole("alert")).toHaveTextContent("looks garbled");
  await waitFor(() => expect(screen.getByRole("button", { name: /generate summary/i })).toBeEnabled());
});

test("warns the recruiter when the resume contained injected instructions", () => {
  render(<SummaryPanel summary={{ ...summary, injection_detected: true }} generatedAt={null} hasResume generate={vi.fn()} />);
  expect(screen.getByRole("status")).toHaveTextContent(/aimed at an AI/i);
});

