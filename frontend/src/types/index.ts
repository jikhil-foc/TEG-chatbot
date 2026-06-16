export interface Source {
  chunk_id: string;
  url: string;
  title: string;
  score: number;
  rerank_score: number;
}

export interface ConversationMessage {
  role: MessageRole;
  content: string;
}

export interface AskRequest {
  query: string;
  messages?: ConversationMessage[];
  session_id?: string;
  top_k?: number;
  rerank_top_n?: number;
}

export interface AskResponse {
  query: string;
  answer: string;
  language: string | null;
  sources: Source[];
  clarification?: boolean;
  off_topic?: boolean;
}

export type MessageRole = "user" | "assistant";

export interface ChatMessage {
  id: string;
  role: MessageRole;
  content: string;
  sources?: Source[];
  language?: string | null;
  error?: boolean;
  streaming?: boolean;
}

export interface ChatWidgetConfig {
  apiBaseUrl?: string;
  title?: string;
  subtitle?: string;
  placeholder?: string;
  welcomeMessage?: string;
  position?: "bottom-right" | "bottom-left";
  primaryColor?: string;
}
