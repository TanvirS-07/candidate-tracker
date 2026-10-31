export const STAGES = ["Applied", "Screening", "Interview", "Offer", "Rejected"] as const;
export type Stage = (typeof STAGES)[number];

export interface Note {
  id: number;
  text: string;
  created_at: string;
}

export interface CandidateSummary {
  headline: string;
  key_skills: string[];
  experience_highlights: string[];
  injection_detected: boolean;
  flags: string[];
}

export interface CandidateListItem {
  id: number;
  name: string;
  email: string;
  role: string;
  stage: Stage;
  source: string | null;
  archived: boolean;
  created_at: string;
}

export interface CandidateDetail extends CandidateListItem {
  phone: string | null;
  resume_text: string;
  notes: Note[];
  summary: CandidateSummary | null;
  summary_generated_at: string | null;
}

export interface NewCandidate {
  name: string;
  email: string;
  phone?: string;
  role: string;
  resume_text: string;
  source?: string;
}
