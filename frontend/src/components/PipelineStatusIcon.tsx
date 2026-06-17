import type { ReactElement } from "react";
import { normalizePipelineStep } from "@/utils/pipelineStatus";

interface PipelineStatusIconProps {
  step?: string;
}

const ICON_PROPS = {
  viewBox: "0 0 24 24",
  fill: "none",
  stroke: "currentColor",
  strokeWidth: 2,
  strokeLinecap: "round" as const,
  strokeLinejoin: "round" as const,
  "aria-hidden": true,
};

function ThinkingIcon() {
  return (
    <svg {...ICON_PROPS}>
      <path d="M12 3a7 7 0 0 0-4 12.7V19a1 1 0 0 0 1 1h6a1 1 0 0 0 1-1v-3.3A7 7 0 0 0 12 3Z" />
      <path d="M9 22h6" />
      <path d="M10 7h.01" />
      <path d="M14 7h.01" />
      <path d="M10 11h.01" />
      <path d="M14 11h.01" />
    </svg>
  );
}

function LanguageIcon() {
  return (
    <svg {...ICON_PROPS}>
      <circle cx="12" cy="12" r="10" />
      <path d="M2 12h20" />
      <path d="M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10Z" />
    </svg>
  );
}

function AnalyzeIcon() {
  return (
    <svg {...ICON_PROPS}>
      <circle cx="11" cy="11" r="8" />
      <path d="m21 21-4.3-4.3" />
      <path d="M11 8v6" />
      <path d="M8 11h6" />
    </svg>
  );
}

function SearchIcon() {
  return (
    <svg {...ICON_PROPS}>
      <circle cx="11" cy="11" r="8" />
      <path d="m21 21-4.3-4.3" />
    </svg>
  );
}

function RankIcon() {
  return (
    <svg {...ICON_PROPS}>
      <path d="M3 6h18" />
      <path d="M7 12h10" />
      <path d="M10 18h4" />
      <path d="M16 6l2 2-2 2" />
      <path d="M8 12l-2 2 2 2" />
    </svg>
  );
}

function WriteIcon() {
  return (
    <svg {...ICON_PROPS}>
      <path d="M12 20h9" />
      <path d="M16.5 3.5a2.1 2.1 0 0 1 3 3L7 19l-4 1 1-4Z" />
    </svg>
  );
}

function SourcesIcon() {
  return (
    <svg {...ICON_PROPS}>
      <path d="M10 13a5 5 0 0 0 7.54.54l3-3a5 5 0 0 0-7.07-7.07l-1.72 1.71" />
      <path d="M14 11a5 5 0 0 0-7.54-.54l-3 3a5 5 0 0 0 7.07 7.07l1.71-1.71" />
    </svg>
  );
}

function ValidateIcon() {
  return (
    <svg {...ICON_PROPS}>
      <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10Z" />
      <path d="m9 12 2 2 4-4" />
    </svg>
  );
}

function ReplyIcon() {
  return (
    <svg {...ICON_PROPS}>
      <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2Z" />
    </svg>
  );
}

const STEP_ICON: Record<string, () => ReactElement> = {
  thinking: ThinkingIcon,
  detect_language: LanguageIcon,
  analyze_query: AnalyzeIcon,
  retrieve: SearchIcon,
  rerank: RankIcon,
  generate: WriteIcon,
  generate_answer: WriteIcon,
  citations: SourcesIcon,
  validation: ValidateIcon,
  greeting: ReplyIcon,
  clarify: ReplyIcon,
  fallback: ReplyIcon,
};

const SPINNING_STEPS = new Set(["detect_language", "retrieve", "rerank"]);
const PULSE_STEPS = new Set([
  "thinking",
  "analyze_query",
  "generate",
  "generate_answer",
  "validation",
]);

export function PipelineStatusIcon({ step }: PipelineStatusIconProps) {
  const resolvedStep = normalizePipelineStep(step);
  const Icon = STEP_ICON[resolvedStep] ?? ThinkingIcon;
  const animationClass = SPINNING_STEPS.has(resolvedStep)
    ? "teg-message__status-icon--spin"
    : PULSE_STEPS.has(resolvedStep)
      ? "teg-message__status-icon--pulse"
      : "";

  return (
    <span
      className={`teg-message__status-icon${animationClass ? ` ${animationClass}` : ""}`}
    >
      <Icon />
    </span>
  );
}
