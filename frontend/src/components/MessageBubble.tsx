import type { ChatMessage } from "@/types";
import { formatResponseLanguageCode } from "@/utils/language";
import { AssistantAvatar } from "./AssistantAvatar";
import { MessageMarkdown } from "./MessageMarkdown";
import { SourceLinks } from "./SourceLinks";
import { SuggestedQuestions } from "./SuggestedQuestions";
import { PipelineStatusMessage } from "./PipelineStatusMessage";

interface MessageBubbleProps {
  message: ChatMessage;
  showSuggestions?: boolean;
  suggestionsDisabled?: boolean;
  onSuggestedQuestion?: (question: string) => void;
}

export function MessageBubble({
  message,
  showSuggestions = false,
  suggestionsDisabled = false,
  onSuggestedQuestion,
}: MessageBubbleProps) {
  const isUser = message.role === "user";
  const isAwaitingFirstToken = message.streaming && message.content.length === 0;
  const languageCode = formatResponseLanguageCode(message.language);
  const showLanguage =
    !isUser && !message.streaming && !message.error && languageCode !== null;

  const bubble = isAwaitingFirstToken ? (
    <div className="teg-message__bubble teg-message__bubble--typing">
      <PipelineStatusMessage
        id={`teg-status-${message.id}`}
        step={message.statusStep}
      />
    </div>
  ) : (
    <div className="teg-message__bubble">
      <div className="teg-message__text">
        <MessageMarkdown
          content={message.content}
          sources={message.sources}
        />
        {message.streaming && (
          <span className="teg-message__cursor" aria-hidden="true" />
        )}
      </div>
      {!isUser &&
        !message.streaming &&
        message.sources &&
        message.sources.length > 0 && (
          <SourceLinks sources={message.sources} />
        )}
      {showSuggestions &&
        !isUser &&
        !message.streaming &&
        !message.error &&
        message.relatedQuestions &&
        message.relatedQuestions.length > 0 &&
        onSuggestedQuestion && (
          <SuggestedQuestions
            questions={message.relatedQuestions}
            disabled={suggestionsDisabled}
            onSelect={onSuggestedQuestion}
          />
        )}
      {showLanguage && (
        <footer className="teg-message__meta">
          <span
            className="teg-message__lang"
            aria-label={`Response language: ${message.language}`}
            title={`Response language: ${message.language}`}
          >
            {languageCode}
          </span>
        </footer>
      )}
    </div>
  );

  return (
    <article
      className={`teg-message teg-message--${message.role}${message.error ? " teg-message--error" : ""}`}
      aria-label={isUser ? "Your message" : "Assistant message"}
      aria-busy={isAwaitingFirstToken ? true : undefined}
      aria-describedby={
        isAwaitingFirstToken ? `teg-status-${message.id}` : undefined
      }
    >
      {!isUser && <AssistantAvatar />}
      {bubble}
    </article>
  );
}
