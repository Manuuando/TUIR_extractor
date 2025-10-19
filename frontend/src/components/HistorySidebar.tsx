import { useEffect, useState } from 'react';
import { ConversationEntry } from '../types';

interface HistorySidebarProps {
  history: ConversationEntry[];
  selectedEntryId: string | null;
  onHistoryLoaded: (history: ConversationEntry[]) => void;
  onSelectEntry: (entry: ConversationEntry) => void;
}

const HistorySidebar = ({
  history,
  selectedEntryId,
  onHistoryLoaded,
  onSelectEntry,
}: HistorySidebarProps) => {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [activeId, setActiveId] = useState<string | null>(null);

  useEffect(() => {
    let isMounted = true;
    const loadHistory = async () => {
      setLoading(true);
      try {
        const response = await fetch('/api/history');
        if (!response.ok) {
          throw new Error(`Backend responded with ${response.status}`);
        }
        const payload: ConversationEntry[] = await response.json();
        if (isMounted) {
          onHistoryLoaded(payload);
          setError(null);
          if (payload.length > 0) {
            setActiveId(payload[0].id);
          }
        }
      } catch (err) {
        if (isMounted) {
          setError(err instanceof Error ? err.message : 'Unknown error');
        }
      } finally {
        if (isMounted) {
          setLoading(false);
        }
      }
    };

    loadHistory();
    return () => {
      isMounted = false;
    };
  }, [onHistoryLoaded]);

  useEffect(() => {
    if (!selectedEntryId) return;
    setActiveId(selectedEntryId);
  }, [selectedEntryId]);

  useEffect(() => {
    if (history.length === 0) {
      setActiveId(null);
      return;
    }
    if (activeId && history.some((entry) => entry.id === activeId)) {
      return;
    }
    setActiveId(history[0].id);
  }, [history, activeId]);

  return (
    <aside className="sidebar">
      <header>
        <h2>History</h2>
        {loading && <small>Loading…</small>}
        {error && <small style={{ color: '#f87171' }}>{error}</small>}
      </header>
      <ul>
        {history.map((entry) => (
          <li
            key={entry.id}
            className={entry.id === activeId ? 'active' : ''}
            onClick={() => {
              setActiveId(entry.id);
              onSelectEntry(entry);
            }}
          >
            <strong>{entry.question}</strong>
            <small>{new Date(entry.createdAt).toLocaleString()}</small>
          </li>
        ))}
        {!loading && history.length === 0 && (
          <li>
            <small>No conversations yet.</small>
          </li>
        )}
      </ul>
    </aside>
  );
};

export default HistorySidebar;
