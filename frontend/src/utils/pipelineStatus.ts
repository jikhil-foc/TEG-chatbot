export const DEFAULT_PIPELINE_STEP = "thinking";

const PIPELINE_STATUS_LABELS: Record<string, string> = {
  thinking: "Thinking…",
  detect_language: "Detecting language…",
  analyze_query: "Analyzing your question…",
  retrieve: "Searching…",
  rerank: "Ranking results…",
  generate: "Writing answer…",
  generate_answer: "Writing answer…",
  citations: "Preparing sources…",
  validation: "Checking answer…",
  greeting: "Preparing reply…",
  clarify: "Preparing reply…",
  fallback: "Preparing reply…",
};

export function pipelineStatusLabel(step: string): string {
  return PIPELINE_STATUS_LABELS[step] ?? PIPELINE_STATUS_LABELS.thinking;
}

export function normalizePipelineStep(step: string | undefined): string {
  if (!step) {
    return DEFAULT_PIPELINE_STEP;
  }
  return step in PIPELINE_STATUS_LABELS ? step : DEFAULT_PIPELINE_STEP;
}
