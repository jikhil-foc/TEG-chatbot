import type { AskRequest, AskResponse } from "@/types";

export class ChatApiError extends Error {
  constructor(
    message: string,
    readonly status?: number,
  ) {
    super(message);
    this.name = "ChatApiError";
  }
}

export interface AskStreamCallbacks {
  onStatus?: (step: string) => void;
  onToken: (content: string) => void;
  onDone: (response: AskResponse) => void;
  onError: (message: string) => void;
}

function normalizeBaseUrl(baseUrl: string): string {
  return baseUrl.replace(/\/+$/, "");
}

function parseSseEvents(
  buffer: string,
  onEvent: (event: Record<string, unknown>) => void,
): string {
  const parts = buffer.split("\n\n");
  const remainder = parts.pop() ?? "";

  for (const part of parts) {
    const line = part
      .split("\n")
      .find((entry) => entry.startsWith("data: "));
    if (!line) {
      continue;
    }

    try {
      onEvent(JSON.parse(line.slice(6)) as Record<string, unknown>);
    } catch {
      // ignore malformed chunks
    }
  }

  return remainder;
}

export async function askQuestionStream(
  apiBaseUrl: string,
  request: AskRequest,
  callbacks: AskStreamCallbacks,
  signal?: AbortSignal,
): Promise<void> {
  const url = `${normalizeBaseUrl(apiBaseUrl)}/api/v1/ask`;

  let response: Response;
  try {
    response = await fetch(url, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Accept: "text/event-stream",
      },
      body: JSON.stringify(request),
      signal,
    });
  } catch (error) {
    if (error instanceof DOMException && error.name === "AbortError") {
      throw error;
    }
    throw new ChatApiError(
      "Unable to reach the chatbot service. Check that the API is running.",
    );
  }

  if (!response.ok) {
    let detail = `Request failed (${response.status})`;
    try {
      const body = (await response.json()) as { detail?: string };
      if (body.detail) {
        detail = body.detail;
      }
    } catch {
      // ignore parse errors
    }
    throw new ChatApiError(detail, response.status);
  }

  if (!response.body) {
    throw new ChatApiError("The chatbot returned an empty response.");
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  let finished = false;

  const handleEvent = (event: Record<string, unknown>) => {
    switch (event.type) {
      case "status":
        if (typeof event.step === "string") {
          callbacks.onStatus?.(event.step);
        }
        break;
      case "token":
        if (typeof event.content === "string" && event.content.length > 0) {
          callbacks.onToken(event.content);
        }
        break;
      case "done":
        finished = true;
        callbacks.onDone({
          query: String(event.query ?? request.query),
          answer: String(event.answer ?? ""),
          language:
            typeof event.language === "string" ? event.language : null,
          sources: Array.isArray(event.sources) ? event.sources : [],
        });
        break;
      case "error":
        finished = true;
        callbacks.onError(
          typeof event.message === "string"
            ? event.message
            : "Something went wrong. Please try again.",
        );
        break;
      default:
        break;
    }
  };

  while (true) {
    const { done, value } = await reader.read();
    if (done) {
      break;
    }

    buffer += decoder.decode(value, { stream: true });
    buffer = parseSseEvents(buffer, handleEvent);
  }

  buffer += decoder.decode();
  if (buffer.trim()) {
    parseSseEvents(`${buffer}\n\n`, handleEvent);
  }

  if (!finished) {
    callbacks.onError("The response ended before the answer was completed.");
  }
}
