import { useEffect, useMemo, useState } from 'react';
import { OutlineSection } from '../types';

const OUTLINE_ENDPOINTS = ['/api/documents/outline', '/api/outline', '/tuir_outline.json'];

const normalize = (value: string) => value.toLowerCase();

const matchesQuery = (section: OutlineSection, query: string) => {
  const q = normalize(query);
  if (!q) return true;
  const haystack = [section.title, section.path, ...(section.keywords ?? [])]
    .filter(Boolean)
    .map(normalize);
  return haystack.some((value) => value.includes(q));
};

const filterSections = (sections: OutlineSection[], query: string): OutlineSection[] => {
  if (!query) return sections;
  return sections.reduce<OutlineSection[]>((accumulator, section) => {
    const children = section.children ? filterSections(section.children, query) : [];
    if (matchesQuery(section, query) || children.length > 0) {
      accumulator.push({
        ...section,
        children: children.length > 0 ? children : undefined,
      });
    }
    return accumulator;
  }, []);
};

const SectionNode = ({ section }: { section: OutlineSection }) => {
  return (
    <div className="document-section">
      <h3>{section.title}</h3>
      <small>{section.path}</small>
      {section.keywords && section.keywords.length > 0 && (
        <div>
          {section.keywords.map((keyword) => (
            <span key={keyword} className="keyword-badge">
              {keyword}
            </span>
          ))}
        </div>
      )}
      {section.children && section.children.length > 0 && (
        <div style={{ marginTop: '0.5rem', marginLeft: '0.75rem' }}>
          {section.children.map((child) => (
            <SectionNode key={child.id} section={child} />
          ))}
        </div>
      )}
    </div>
  );
};

const DocumentExplorer = () => {
  const [sections, setSections] = useState<OutlineSection[]>([]);
  const [query, setQuery] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let isMounted = true;
    const loadOutline = async () => {
      setLoading(true);
      let lastError: string | null = null;

      for (const endpoint of OUTLINE_ENDPOINTS) {
        try {
          const response = await fetch(endpoint);
          if (!response.ok) {
            lastError = `Backend responded with ${response.status} for ${endpoint}`;
            continue;
          }
          const payload: OutlineSection[] = await response.json();
          if (isMounted) {
            setSections(payload);
            setError(null);
          }
          return;
        } catch (err) {
          lastError = err instanceof Error ? err.message : 'Failed to load outline';
        }
      }

      if (isMounted) {
        setError(lastError ?? 'Outline not available');
      }
    };

    loadOutline().finally(() => {
      if (isMounted) {
        setLoading(false);
      }
    });

    return () => {
      isMounted = false;
    };
  }, []);

  const filteredSections = useMemo(
    () => filterSections(sections, query),
    [sections, query]
  );

  return (
    <section className="document-explorer">
      <header>
        <h2>TUIR Outline</h2>
        <input
          className="search-input"
          type="search"
          placeholder="Search sections or keywords…"
          value={query}
          onChange={(event) => setQuery(event.target.value)}
        />
        {loading && <small>Loading…</small>}
        {error && <small style={{ color: '#f87171' }}>{error}</small>}
      </header>
      <div className="document-list">
        {filteredSections.map((section) => (
          <SectionNode key={section.id} section={section} />
        ))}
        {!loading && filteredSections.length === 0 && (
          <p>No sections match your search.</p>
        )}
      </div>
    </section>
  );
};

export default DocumentExplorer;
