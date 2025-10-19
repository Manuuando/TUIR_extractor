export interface ConversationEntry {
  id: string;
  question: string;
  answer: string;
  createdAt: string;
}

export interface OutlineSection {
  id: string;
  title: string;
  path: string;
  children?: OutlineSection[];
  keywords?: string[];
}
