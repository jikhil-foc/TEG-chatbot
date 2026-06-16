const SESSION_STORAGE_KEY = "teg-chatbot-session-id";

export function getOrCreateSessionId(): string {
  try {
    const existing = sessionStorage.getItem(SESSION_STORAGE_KEY);
    if (existing) {
      return existing;
    }

    const sessionId = crypto.randomUUID();
    sessionStorage.setItem(SESSION_STORAGE_KEY, sessionId);
    return sessionId;
  } catch {
    return crypto.randomUUID();
  }
}
