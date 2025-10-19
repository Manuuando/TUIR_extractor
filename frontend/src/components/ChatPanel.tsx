import { FormEvent, useEffect, useRef, useState } from 'react';
import { ConversationEntry, ConversationMessage } from '../types';

interface ChatPanelProps {
  selectedEntry: ConversationEntry | null;
  onNewEntry: (entry: ConversationEntry) => void;
}

const decoder = new TextDecoder();

const randomId = () =>
  (typeof crypto !== 'undefined' && 'randomUUID' in crypto
    ? crypto.randomUUID()
    : `${Date.now()}-${Math.random().toString(16).slice(2)}`);

const ChatPanel = ({ selectedEntry, onNewEntry }: ChatPanelProps) => {
  const [question, setQuestion] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [messages, setMessages] = useState<ConversationMessage[]>(
    selectedEntry?.messages ?? []
  );
  const [sessionId, setSessionId] = useState(() => selectedEntry?.id ?? randomId());
  const previousSelectedEntry = useRef<ConversationEntry | null>(selectedEntry);
  const assistantMessageIndexRef = useRef<number | null>(null);

  useEffect(() => {
    if (!selectedEntry) {
      if (previousSelectedEntry.current) {
        previousSelectedEntry.current = null;
        setSessionId(randomId());
      }
      setMessages([]);
      assistantMessageIndexRef.current = null;
      return;
    }
    previousSelectedEntry.current = selectedEntry;
    setSessionId(selectedEntry.id);
    setMessages(selectedEntry.messages ?? []);
    assistantMessageIndexRef.current = null;
  }, [selectedEntry]);

  const handleSubmit = async (event: FormEvent) => {
    event.preventDefault();
    const trimmed = question.trim();
    if (!trimmed) return;

    setIsLoading(true);
    setError(null);

    try {
      const userTimestamp = new Date().toISOString();
      const assistantTimestamp = new Date().toISOString();
      let assistantIndex = -1;
      setMessages((previous) => {
        const nextMessages = [
          ...previous,
          { role: 'user', content: trimmed, timestamp: userTimestamp },
          { role: 'assistant', content: '', timestamp: assistantTimestamp },
        ];
        assistantIndex = nextMessages.length - 1;
        return nextMessages;
      });
      assistantMessageIndexRef.current = assistantIndex;

      const response = await fetch('/api/qa', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          question: trimmed,
          session_id: sessionId,
        }),
      });

      if (!response.body) {
        throw new Error('Streaming not supported by the backend response.');
      }

      if (!response.ok) {
        throw new Error(`Backend responded with ${response.status}`);
      }

      const reader = response.body.getReader();
      let answer = '';

      while (true) {
        const { value, done } = await reader.read();
        if (done) break;
        answer += decoder.decode(value, { stream: true });
        setMessages((previous) => {
          if (assistantMessageIndexRef.current === null) {
            return previous;
          }
          return previous.map((message, index) =>
            index === assistantMessageIndexRef.current
              ? { ...message, content: answer }
              : message
          );
        });
      }

      answer += decoder.decode();
      const responseSessionId =
        response.headers.get('X-Conversation-Id') ?? sessionId ?? randomId();
      setSessionId(responseSessionId);

      let finalMessages: ConversationMessage[] = [];
      setMessages((previous) => {
        if (assistantMessageIndexRef.current === null) {
          finalMessages = previous;
          return previous;
        }
        const updated = previous.map((message, index) =>
          index === assistantMessageIndexRef.current ? { ...message, content: answer } : message
        );
        finalMessages = updated;
        return updated;
      });
      assistantMessageIndexRef.current = null;

      const createdAt =
        finalMessages[finalMessages.length - 1]?.timestamp ?? new Date().toISOString();

      const entry: ConversationEntry = {
        id: responseSessionId,
        question: trimmed,
        answer,
        createdAt,
        messages: finalMessages,
      };

      onNewEntry(entry);
      setQuestion('');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to contact backend');
      if (assistantMessageIndexRef.current !== null) {
        setMessages((previous) =>
          previous.map((message, index) =>
            index === assistantMessageIndexRef.current
              ? { ...message, content: 'Failed to retrieve answer.' }
              : message
          )
        );
        assistantMessageIndexRef.current = null;
      }
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <section className="chat-panel">
      <header>
        <h2>Ask about the TUIR</h2>
        {error && <small style={{ color: '#f87171' }}>{error}</small>}
      </header>
      <form onSubmit={handleSubmit}>
        <textarea
          value={question}
          placeholder="Ask a question about the TUIR…"
          onChange={(event) => setQuestion(event.target.value)}
          disabled={isLoading}
        />
        <button type="submit" disabled={isLoading}>
          {isLoading ? 'Thinking…' : 'Send'}
        </button>
      </form>
      <div className="chat-transcript">
        {messages.length === 0 && (
          <div className="chat-turn">
            <small>No conversation yet. Ask a question to get started.</small>
          </div>
        )}
        {messages.map((message, index) => {
          const isAssistant = message.role === 'assistant';
          const isLatestAssistant =
            isAssistant && isLoading && index === messages.length - 1;
          const hasContent = message.content.trim().length > 0;
          const displayContent = hasContent ? message.content : isLatestAssistant ? '…' : message.content;
          return (
            <div
              key={`${message.timestamp ?? 'no-ts'}-${index}`}
              className={`chat-turn chat-turn-${message.role}`}
            >
              <h4>{isAssistant ? 'Assistant' : 'You'}</h4>
              <pre>{displayContent}</pre>
            </div>
          );
        })}
      </div>
    </section>
  );
};

export default ChatPanel;
