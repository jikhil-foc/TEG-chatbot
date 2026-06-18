import { PipelineStatusIcon } from "./PipelineStatusIcon";
import {
  DEFAULT_PIPELINE_STEP,
  pipelineStatusLabel,
} from "@/utils/pipelineStatus";

interface PipelineStatusMessageProps {
  step?: string;
  id?: string;
}

export function PipelineStatusMessage({ step, id }: PipelineStatusMessageProps) {
  const resolvedStep = step ?? DEFAULT_PIPELINE_STEP;

  return (
    <p
      id={id}
      className="teg-message__status"
      role="status"
      aria-live="polite"
    >
      <PipelineStatusIcon step={resolvedStep} />
      <span
        key={resolvedStep}
        className="teg-message__status-text teg-message__status-text--fade"
      >
        {pipelineStatusLabel(resolvedStep)}
      </span>
      <span className="teg-sr-only">Assistant is working</span>
    </p>
  );
}
