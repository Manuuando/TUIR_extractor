import { useState } from 'react';
import ChatPanel from './components/ChatPanel';
import DocumentExplorer from './components/DocumentExplorer';
import HistorySidebar from './components/HistorySidebar';
import { ConversationEntry } from './types';
import './styles/layout.css';

const App = () => {
  const [selectedEntry, setSelectedEntry] = useState<ConversationEntry | null>(null);
  const [history, setHistory] = useState<ConversationEntry[]>([]);

  return (
    <div className="app-shell">
      <HistorySidebar
        history={history}
        selectedEntryId={selectedEntry?.id ?? null}
        onHistoryLoaded={setHistory}
        onSelectEntry={setSelectedEntry}
      />
      <main className="main-content">
        <DocumentExplorer />
        <ChatPanel
          selectedEntry={selectedEntry}
          onNewEntry={(entry) => {
            setHistory((prev) => [entry, ...prev.filter((item) => item.id !== entry.id)]);
            setSelectedEntry(entry);
          }}
        />
      </main>
    </div>
  );
};

export default App;
