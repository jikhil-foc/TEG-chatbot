const PIPELINE_STATUS_LABELS: Record<string, string> = {
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
  return PIPELINE_STATUS_LABELS[step] ?? "Thinking…";
}
