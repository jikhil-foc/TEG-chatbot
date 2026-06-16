import { useEffect, useRef } from "react";
import type { ChatMessage } from "@/types";
import { MessageBubble } from "./MessageBubble";

interface MessageListProps {
  messages: ChatMessage[];
  latestAssistantMessageId?: string | null;
  suggestionsDisabled?: boolean;
  onSuggestedQuestion?: (question: string) => void;
}

export function MessageList({
  messages,
  latestAssistantMessageId = null,
  suggestionsDisabled = false,
  onSuggestedQuestion,
}: MessageListProps) {
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth", block: "end" });
  }, [messages]);

  return (
    <div
      className="teg-message-list"
      role="log"
      aria-live="polite"
      aria-relevant="additions text"
      aria-label="Chat messages"
    >
      {messages.map((message) => (
        <MessageBubble
          key={message.id}
          message={message}
          showSuggestions={message.id === latestAssistantMessageId}
          suggestionsDisabled={suggestionsDisabled}
          onSuggestedQuestion={onSuggestedQuestion}
        />
      ))}
      <div ref={bottomRef} />
    </div>
  );
}
