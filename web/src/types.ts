export type Label = "grounded" | "partial" | "unsupported";

export interface Section {
  id: string; page: number; char_start: number; char_end: number; text: string;
}
export interface Claim {
  id: string; text: string; label: Label;
  evidence_span_ids: string[]; quote: string | null; page: number | null; rationale: string;
}
export interface Groundedness {
  score: number; n_grounded: number; n_partial: number; n_unsupported: number;
}
export interface Scorecard {
  recall: number; recall_ci: [number, number]; false_negatives: number; n_positive: number;
  citation_precision: number | null; cohen_kappa: number | null;
  balanced_accuracy: number | null;
  validated_on: string; domain_note: string;
}
export interface Fixture {
  fixture_id: string;
  source: { title: string; sections: Section[] };
  ai_output: string;
  claims: Claim[];
  groundedness: Groundedness;
  scorecard: Scorecard;
}
