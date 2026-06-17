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
      aria-live="polite"
    >
      <PipelineStatusIcon step={resolvedStep} />
      <span className="teg-message__status-text">
        {pipelineStatusLabel(resolvedStep)}
      </span>
    </p>
  );
}
