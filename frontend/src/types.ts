export interface ConversationMessage {
  role: string;
  content: string;
  timestamp?: string;
}

export interface ConversationEntry {
  id: string;
  question: string;
  answer: string;
  createdAt: string;
  messages?: ConversationMessage[];
}

export interface HistoryResponse {
  session_id: string;
  messages: ConversationMessage[];
}

export interface OutlineSection {
  id: string;
  title: string;
  path: string;
  children?: OutlineSection[];
  keywords?: string[];
}
