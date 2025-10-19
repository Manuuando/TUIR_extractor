import { FormEvent, useEffect, useMemo, useState } from 'react';
import { ConversationEntry } from '../types';

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
  const [streamedAnswer, setStreamedAnswer] = useState('');
  const [transcript, setTranscript] = useState<ConversationEntry[]>([]);
  const activeEntry = useMemo(() => {
    if (isLoading && question.trim()) {
      return {
        id: 'pending',
        question,
        answer: streamedAnswer,
        createdAt: new Date().toISOString(),
      } satisfies ConversationEntry;
    }
    return selectedEntry;
  }, [isLoading, question, streamedAnswer, selectedEntry]);

  useEffect(() => {
    if (!selectedEntry) return;
    setTranscript((previous) => {
      if (previous.some((entry) => entry.id === selectedEntry.id)) {
        return previous;
      }
      return [selectedEntry, ...previous];
    });
  }, [selectedEntry]);

  const handleSubmit = async (event: FormEvent) => {
    event.preventDefault();
    const trimmed = question.trim();
    if (!trimmed) return;

    setIsLoading(true);
    setError(null);
    setStreamedAnswer('');

    try {
      const response = await fetch('/api/qa', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ question: trimmed }),
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
        setStreamedAnswer(answer);
      }

      answer += decoder.decode();
      const entry: ConversationEntry = {
        id: response.headers.get('X-Conversation-Id') ?? randomId(),
        question: trimmed,
        answer,
        createdAt: new Date().toISOString(),
      };

      setTranscript((previous) => [entry, ...previous]);
      onNewEntry(entry);
      setQuestion('');
      setStreamedAnswer('');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to contact backend');
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
        {activeEntry && (
          <div className="chat-turn">
            <h4>You asked</h4>
            <pre>{activeEntry.question}</pre>
            <h4>Answer</h4>
            <pre>{isLoading ? streamedAnswer || '…' : activeEntry.answer}</pre>
          </div>
        )}
        {transcript
          .filter((entry) => !activeEntry || entry.id !== activeEntry.id)
          .map((entry) => (
            <div key={entry.id} className="chat-turn">
              <h4>You asked</h4>
              <pre>{entry.question}</pre>
              <h4>Answer</h4>
              <pre>{entry.answer}</pre>
            </div>
          ))}
      </div>
    </section>
  );
};

export default ChatPanel;
