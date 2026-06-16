import type { ChatMessage } from "@/types";
import { formatResponseLanguageCode } from "@/utils/language";
import { MessageMarkdown } from "./MessageMarkdown";
import { SourceLinks } from "./SourceLinks";
import { TypingIndicator } from "./TypingIndicator";

interface MessageBubbleProps {
  message: ChatMessage;
}

export function MessageBubble({ message }: MessageBubbleProps) {
  const isUser = message.role === "user";
  const isAwaitingFirstToken = message.streaming && message.content.length === 0;
  const languageCode = formatResponseLanguageCode(message.language);
  const showLanguage =
    !isUser && !message.streaming && !message.error && languageCode !== null;

  return (
    <article
      className={`teg-message teg-message--${message.role}${message.error ? " teg-message--error" : ""}`}
      aria-label={isUser ? "Your message" : "Assistant message"}
      aria-busy={isAwaitingFirstToken ? true : undefined}
    >
      {isAwaitingFirstToken ? (
        <div className="teg-message__bubble teg-message__bubble--typing">
          <TypingIndicator />
        </div>
      ) : (
        <div className="teg-message__bubble">
          <div className="teg-message__text">
            <MessageMarkdown content={message.content} />
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
      )}
    </article>
  );
}
