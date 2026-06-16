import { useCallback, useEffect, useId, useRef, useState } from "react";
import { askQuestionStream, ChatApiError } from "@/api/chat";
import { ChatInput } from "@/components/ChatInput";
import { MessageList } from "@/components/MessageList";
import type { ChatMessage, ChatWidgetConfig, ConversationMessage } from "@/types";
import { createMessageId } from "@/utils/id";
import { getOrCreateSessionId } from "@/utils/session";
import "@/styles/widget.css";

const DEFAULT_CONFIG: Required<ChatWidgetConfig> = {
  apiBaseUrl: "",
  title: "TEG Assistant",
  subtitle: "Ask about TEG levels, exams, and services",
  placeholder: "Ask a question…",
  welcomeMessage:
    "Hello! I can help answer questions about TEG based on our published content. What would you like to know?",
  position: "bottom-right",
  primaryColor: "#0d6b4f",
};

export interface ChatWidgetProps extends ChatWidgetConfig {}

export function ChatWidget({
  apiBaseUrl = DEFAULT_CONFIG.apiBaseUrl,
  title = DEFAULT_CONFIG.title,
  subtitle = DEFAULT_CONFIG.subtitle,
  placeholder = DEFAULT_CONFIG.placeholder,
  welcomeMessage = DEFAULT_CONFIG.welcomeMessage,
  position = DEFAULT_CONFIG.position,
  primaryColor = DEFAULT_CONFIG.primaryColor,
}: ChatWidgetProps) {
  const panelId = useId();
  const abortRef = useRef<AbortController | null>(null);
  const sessionIdRef = useRef(getOrCreateSessionId());

  const [isOpen, setIsOpen] = useState(false);
  const [input, setInput] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [messages, setMessages] = useState<ChatMessage[]>(() => [
    {
      id: createMessageId(),
      role: "assistant",
      content: welcomeMessage,
    },
  ]);

  const resolvedApiUrl =
    apiBaseUrl || (import.meta.env.DEV ? "" : window.location.origin);

  useEffect(() => {
    document.documentElement.style.setProperty("--teg-primary", primaryColor);
  }, [primaryColor]);

  useEffect(() => {
    return () => {
      abortRef.current?.abort();
    };
  }, []);

  const toggleOpen = useCallback(() => {
    setIsOpen((open) => !open);
  }, []);

  const sendMessage = useCallback(async () => {
    const query = input.trim();
    if (!query || isLoading) {
      return;
    }

    const priorMessages: ConversationMessage[] = messages
      .filter(
        (message) =>
          !message.streaming && !message.error && message.content.trim().length > 0,
      )
      .slice(-10)
      .map((message) => ({
        role: message.role,
        content: message.content,
      }));

    const userMessage: ChatMessage = {
      id: createMessageId(),
      role: "user",
      content: query,
    };

    const assistantId = createMessageId();

    setMessages((prev) => [
      ...prev,
      userMessage,
      {
        id: assistantId,
        role: "assistant",
        content: "",
        streaming: true,
      },
    ]);
    setInput("");
    setIsLoading(true);

    abortRef.current?.abort();
    const controller = new AbortController();
    abortRef.current = controller;

    try {
      await askQuestionStream(
        resolvedApiUrl,
        {
          query,
          messages: priorMessages,
          session_id: sessionIdRef.current,
        },
        {
          onToken: (content) => {
            setMessages((prev) =>
              prev.map((message) =>
                message.id === assistantId
                  ? { ...message, content: message.content + content }
                  : message,
              ),
            );
          },
          onDone: (response) => {
            setMessages((prev) =>
              prev.map((message) =>
                message.id === assistantId
                  ? {
                      ...message,
                      content: response.answer,
                      sources: response.sources,
                      language: response.language,
                      streaming: false,
                    }
                  : message,
              ),
            );
          },
          onError: (message) => {
            setMessages((prev) =>
              prev.map((entry) =>
                entry.id === assistantId
                  ? {
                      ...entry,
                      content: message,
                      error: true,
                      streaming: false,
                    }
                  : entry,
              ),
            );
          },
        },
        controller.signal,
      );
    } catch (error) {
      if (error instanceof DOMException && error.name === "AbortError") {
        setMessages((prev) => prev.filter((message) => message.id !== assistantId));
        return;
      }

      const detail =
        error instanceof ChatApiError
          ? error.message
          : "Something went wrong. Please try again.";

      setMessages((prev) =>
        prev.map((message) =>
          message.id === assistantId
            ? {
                ...message,
                content: detail,
                error: true,
                streaming: false,
              }
            : message,
        ),
      );
    } finally {
      setIsLoading(false);
    }
  }, [input, isLoading, messages, resolvedApiUrl]);

  return (
    <div
      className={`teg-widget teg-widget--${position}`}
      data-open={isOpen ? "true" : "false"}
    >
      {isOpen && (
        <section
          id={panelId}
          className="teg-widget__panel"
          role="dialog"
          aria-modal="false"
          aria-labelledby={`${panelId}-title`}
          aria-describedby={`${panelId}-subtitle`}
        >
          <header className="teg-widget__header">
            <div className="teg-widget__header-text">
              <h2 id={`${panelId}-title`} className="teg-widget__title">
                {title}
              </h2>
              <p id={`${panelId}-subtitle`} className="teg-widget__subtitle">
                {subtitle}
              </p>
            </div>
            <button
              type="button"
              className="teg-widget__close"
              onClick={toggleOpen}
              aria-label="Close chat"
            >
              <CloseIcon />
            </button>
          </header>

          <MessageList messages={messages} />

          <footer className="teg-widget__footer">
            <ChatInput
              value={input}
              onChange={setInput}
              onSubmit={sendMessage}
              disabled={isLoading}
              placeholder={placeholder}
            />
          </footer>
        </section>
      )}

      <button
        type="button"
        className="teg-widget__launcher"
        onClick={toggleOpen}
        aria-expanded={isOpen}
        aria-controls={panelId}
        aria-label={isOpen ? "Close chat" : "Open chat"}
      >
        {isOpen ? <CloseIcon /> : <ChatIcon />}
      </button>
    </div>
  );
}

function ChatIcon() {
  return (
    <svg width="28" height="28" viewBox="0 0 24 24" fill="none" aria-hidden="true">
      <path
        d="M4 4h16a1 1 0 0 1 1 1v11a1 1 0 0 1-1 1H8l-4 4V5a1 1 0 0 1 1-1Z"
        stroke="currentColor"
        strokeWidth="1.75"
        strokeLinejoin="round"
      />
    </svg>
  );
}

function CloseIcon() {
  return (
    <svg width="22" height="22" viewBox="0 0 24 24" fill="none" aria-hidden="true">
      <path
        d="M6 6l12 12M18 6 6 18"
        stroke="currentColor"
        strokeWidth="2"
        strokeLinecap="round"
      />
    </svg>
  );
}
