import { useState, useEffect } from 'react'
import axios from 'axios'
import './App.css'
import ScenariosView from './ScenariosView.jsx'

const API_URL = import.meta.env.VITE_API_URL || ''

/** Render simple markdown: **text** -> bold; newlines -> paragraphs */
function renderModuleContent(text) {
  if (!text || typeof text !== 'string') return null
  return text.split('\n').map((line, i) => {
    const parts = []
    let rest = line
    let key = 0
    while (rest.length > 0) {
      const m = rest.match(/\*\*(.*?)\*\*/)
      if (!m) {
        if (rest.trim()) parts.push(<span key={key++}>{rest}</span>)
        break
      }
      const idx = rest.indexOf(m[0])
      if (idx > 0) parts.push(<span key={key++}>{rest.slice(0, idx)}</span>)
      parts.push(<strong key={key++}>{m[1]}</strong>)
      rest = rest.slice(idx + m[0].length)
    }
    return <p key={i}>{parts.length ? parts : '\u00A0'}</p>
  })
}

/** Recursive tree node for Skill Map concept graph */
function ConceptTree({ concepts, rootId, onSelect, masteredIds }) {
  const byId = (concepts || []).reduce((acc, c) => ({ ...acc, [c.id]: c }), {})
  const node = rootId ? byId[rootId] : null
  if (!node) return null
  const children = (node.children || []).map(id => byId[id]).filter(Boolean)
  const isMastered = masteredIds.has(node.id)
  return (
    <ul className="concept-tree">
      <li className="concept-tree-item">
        <button
          type="button"
          className={`concept-tree-node ${isMastered ? 'mastered' : ''}`}
          onClick={() => onSelect(node.id)}
        >
          <span className="concept-tree-title">{node.title}</span>
        </button>
        {children.length > 0 && (
          <ul className="concept-tree-children">
            {children.map(child => (
              <li key={child.id}>
                <ConceptTree concepts={concepts} rootId={child.id} onSelect={onSelect} masteredIds={masteredIds} />
              </li>
            ))}
          </ul>
        )}
      </li>
    </ul>
  )
}

function LearnView() {
  const [conceptGraph, setConceptGraph] = useState(null) // { concepts, root_id }
  const [conceptGraphLoading, setConceptGraphLoading] = useState(false)
  const [selectedConcept, setSelectedConcept] = useState(null) // full concept object when clicked
  const [masteredIds, setMasteredIds] = useState(() => new Set()) // track completed for "recommend next"
  const [recommendNext, setRecommendNext] = useState([])

  useEffect(() => {
    setConceptGraphLoading(true)
    const url = API_URL ? `${API_URL}/api/learning/concept-graph` : '/api/learning/concept-graph'
    axios.get(url, { timeout: 10000 })
      .then(res => {
        setConceptGraph(res.data?.concepts ? res.data : null)
      })
      .catch(() => setConceptGraph(null))
      .finally(() => setConceptGraphLoading(false))
  }, [])

  useEffect(() => {
    if (!conceptGraph?.concepts) {
      setRecommendNext([])
      return
    }
    if (masteredIds.size === 0) {
      setRecommendNext(conceptGraph.concepts.filter(c => !c.depends_on?.length).slice(0, 5))
      return
    }
    const completed = [...masteredIds]
    const url = API_URL ? `${API_URL}/api/learning/recommend-next` : '/api/learning/recommend-next'
    axios.get(url, { params: { completed: completed.join(',') } })
      .then(res => setRecommendNext(Array.isArray(res.data) ? res.data : []))
      .catch(() => setRecommendNext([]))
  }, [masteredIds, conceptGraph])

  const openConceptDetail = (conceptId) => {
    const base = API_URL || ''
    axios.get(`${base}/api/learning/concepts/${conceptId}`)
      .then(res => {
        if (res.data?.detail === 'Concept not found') return
        setSelectedConcept(res.data)
      })
      .catch(() => setSelectedConcept(null))
  }

  const closeConceptDetail = () => setSelectedConcept(null)

  const markConceptMastered = (conceptId) => {
    setMasteredIds(prev => new Set([...prev, conceptId]))
  }

  return (
    <section className="learn-section">
      <h2>Skill Map + Knowledge Graph</h2>
      <p className="learn-sub">
        ERP concepts with dependencies. See what depends on what and get recommended next steps.
      </p>

      {selectedConcept ? (
        <div className="concept-detail-view">
          <button type="button" className="learn-back" onClick={closeConceptDetail}>
            ← Back to map
          </button>
          <h3 className="learn-path-view-title">{selectedConcept.title}</h3>
          <div className="learn-module-content concept-detail-body">
            {renderModuleContent(selectedConcept.description)}
          </div>
          {selectedConcept.why_it_matters && (
            <div className="concept-why">
              <h4 className="concept-why-title">Why it matters</h4>
              {renderModuleContent(selectedConcept.why_it_matters)}
            </div>
          )}
          {selectedConcept.depends_on_details?.length > 0 && (
            <p className="concept-depends">
              <strong>Depends on:</strong>{' '}
              {selectedConcept.depends_on_details.map((d, i) => (
                <span key={d.id}>
                  {i > 0 && ', '}
                  <button
                    type="button"
                    className="concept-depends-link"
                    onClick={() => openConceptDetail(d.id)}
                  >
                    {d.title}
                  </button>
                </span>
              ))}
            </p>
          )}
          <button
            type="button"
            className="learn-path-btn"
            onClick={() => markConceptMastered(selectedConcept.id)}
          >
            Mark as done
          </button>
        </div>
      ) : conceptGraph?.concepts?.length > 0 ? (
        <>
          {recommendNext.length > 0 && (
            <div className="recommend-next">
              <h3 className="recommend-next-title">Recommended next</h3>
              <p className="recommend-next-sub">
                Concepts you can learn now (dependencies satisfied).
              </p>
              <ul className="recommend-next-list">
                {recommendNext.map((c) => (
                  <li key={c.id}>
                    <button
                      type="button"
                      className="recommend-next-btn"
                      onClick={() => openConceptDetail(c.id)}
                    >
                      {c.title}
                    </button>
                  </li>
                ))}
              </ul>
            </div>
          )}
          <h3 className="concept-tree-title">Concept graph</h3>
          <ConceptTree
            concepts={conceptGraph.concepts}
            rootId={conceptGraph.root_id}
            onSelect={openConceptDetail}
            masteredIds={masteredIds}
          />
        </>
      ) : !conceptGraphLoading ? (
        <p className="learn-empty">
          No concept graph available. Check that the API is running.
        </p>
      ) : (
        <p className="learn-empty">Loading concept graph…</p>
      )}
    </section>
  )
}

function CompetitiveIntelView() {
  const [health, setHealth] = useState(null)
  const [registry, setRegistry] = useState([])
  const [events, setEvents] = useState([])
  const [eventsLoading, setEventsLoading] = useState(false)
  const [crawlLoading, setCrawlLoading] = useState(false)
  const [selectedCompetitor, setSelectedCompetitor] = useState('all')
  const [selectedTheme, setSelectedTheme] = useState('all')

  useEffect(() => {
    axios.get(API_URL ? `${API_URL}/health` : '/health')
      .then(res => setHealth(res.data))
      .catch(() => setHealth({ status: 'disconnected', database: 'disconnected' }))
  }, [])

  useEffect(() => {
    axios.get(API_URL ? `${API_URL}/api/competitors/sources` : '/api/competitors/sources')
      .then(res => setRegistry(Array.isArray(res.data) ? res.data : []))
      .catch(() => setRegistry([]))

    const loadEvents = () => {
      setEventsLoading(true)
      axios.get(API_URL ? `${API_URL}/api/competitors/events` : '/api/competitors/events', {
        params: { limit: 50 },
      })
        .then(res => setEvents(Array.isArray(res.data) ? res.data : []))
        .catch(() => setEvents([]))
        .finally(() => setEventsLoading(false))
    }
    loadEvents()
  }, [])

  const triggerCrawl = async () => {
    setCrawlLoading(true)
    try {
      await axios.post(API_URL ? `${API_URL}/api/competitors/crawl` : '/api/competitors/crawl')
      const res = await axios.get(API_URL ? `${API_URL}/api/competitors/events` : '/api/competitors/events', {
        params: { limit: 50 },
      })
      setEvents(Array.isArray(res.data) ? res.data : [])
    } catch {
      // swallow; UI will just show existing events
    } finally {
      setCrawlLoading(false)
    }
  }

  const allCompetitors = [
    'all',
    ...registry.map(r => r.competitor),
  ]

  const allThemes = [
    'all',
    ...Array.from(new Set(events.map(e => (e.theme || '').toLowerCase()).filter(Boolean))),
  ]

  const filteredEvents = events.filter(e => {
    const cOk = selectedCompetitor === 'all' || e.competitor === selectedCompetitor
    const tOk = selectedTheme === 'all' || (e.theme || '').toLowerCase() === selectedTheme
    return cOk && tOk
  })

  return (
    <div className="intel-console">
      <section className="intel-hero">
        <div>
          <h2>Release Notes + Docs Capability Feed</h2>
          <p className="intel-hero-sub">
            Live “ERP feature radar” for core competitors, built from diffs in their official
            release notes and documentation.
          </p>
        </div>
        <div className="intel-integrations">
          <div className="intel-status-card">
            <div className="intel-status-row">
              <span className="intel-status-label">Backend</span>
              <span className="intel-status-pill" data-ok={health?.status === 'healthy'}>
                {health?.status || 'unknown'}
              </span>
            </div>
            <div className="intel-status-row">
              <span className="intel-status-label">DB</span>
              <span className="intel-status-pill" data-ok={health?.database === 'connected'}>
                {health?.database || 'unknown'}
              </span>
            </div>
          </div>
        </div>
      </section>

      <section className="intel-watchlist">
        <div className="intel-section-header">
          <div>
            <h3>Source registry by competitor</h3>
            <p className="intel-section-sub">
              High-signal URLs the crawler watches for each ERP vendor (release notes, docs,
              deprecations, changelogs).
            </p>
          </div>
        </div>
        <div className="intel-watchlist-grid">
          {(registry || []).map((c) => {
            const sources = c?.sources ?? []
            return (
            <div key={c.competitor} className="intel-competitor-card">
              <div className="intel-competitor-header">
                <div className="intel-avatar">
                  <span>{(c.competitor || '').charAt(0)}</span>
                </div>
                <div>
                  <h4>{c.competitor}</h4>
                  <p className="intel-competitor-verticals">
                    {sources.length} high-signal source{sources.length === 1 ? '' : 's'}
                  </p>
                </div>
              </div>
              <div className="intel-competitor-metrics registry-layout">
                <div className="intel-registry-column">
                  <span className="intel-metric-label">Watched URLs</span>
                  <ul className="intel-so-what-list">
                    {sources.map((src, idx) => (
                      <li key={idx}>
                        <a
                          href={src.url}
                          className="intel-link"
                          target="_blank"
                          rel="noopener noreferrer"
                        >
                          {src.label || src.url}
                        </a>
                      </li>
                    ))}
                  </ul>
                </div>
              </div>
            </div>
            )
          })}
        </div>
      </section>

      <section className="intel-live-and-timeline">
        <div className="intel-live-column">
          <h3>Capability change feed</h3>
          <p className="intel-section-sub">
            Diff-first view of feature-level changes across competitors – each event is backed by a
            citation to an official page.
          </p>
          <div className="intel-timeline-filter">
            <label htmlFor="competitor-filter">Competitor</label>
            <select
              id="competitor-filter"
              value={selectedCompetitor}
              onChange={(e) => setSelectedCompetitor(e.target.value)}
            >
              {allCompetitors.map((c) => (
                <option key={c} value={c}>
                  {c === 'all' ? 'All competitors' : c}
                </option>
              ))}
            </select>
            <label htmlFor="theme-filter">Theme</label>
            <select
              id="theme-filter"
              value={selectedTheme}
              onChange={(e) => setSelectedTheme(e.target.value)}
            >
              {allThemes.map((t) => (
                <option key={t} value={t}>
                  {t === 'all' ? 'All themes' : t}
                </option>
              ))}
            </select>
            <button
              type="button"
              className="intel-refresh-btn"
              onClick={triggerCrawl}
              disabled={crawlLoading}
            >
              {crawlLoading ? 'Crawling…' : 'Run crawl now'}
            </button>
          </div>

          {eventsLoading ? (
            <p className="intel-empty">Loading capability changes…</p>
          ) : filteredEvents.length === 0 ? (
            <p className="intel-empty">
              No capability-level change events yet. Run a crawl to populate the feed.
            </p>
          ) : (
            <ul className="intel-timeline-list">
              {filteredEvents.map((e) => (
                <li key={e.id} className="intel-event-card">
                  <div className="intel-event-header">
                    <div>
                      <span className="intel-event-competitor">{e.competitor}</span>
                      <span className="intel-event-type">{e.change_type}</span>
                    </div>
                    {e.created_at && (
                      <span className="intel-event-time">
                        {new Date(e.created_at).toLocaleString()}
                      </span>
                    )}
                  </div>
                  <p className="intel-event-content">
                    <strong>{e.theme}</strong> — {e.claim}
                  </p>
                  <ul className="intel-so-what-list">
                    {(e.beginner_summary || []).map((b, i) => (
                      <li key={i}>{b}</li>
                    ))}
                  </ul>
                  <div className="intel-event-footer">
                    <span className="intel-event-tags">
                      {e.theme && <span className="intel-tag">{e.theme}</span>}
                      {e.change_type && <span className="intel-tag">{e.change_type}</span>}
                    </span>
                    <div className="intel-event-links">
                      {e.evidence_url && (
                        <a
                          href={e.evidence_url}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="intel-link"
                        >
                          Evidence
                        </a>
                      )}
                    </div>
                  </div>
                </li>
              ))}
            </ul>
          )}
        </div>
      </section>
    </div>
  )
}

function App() {
  const [health, setHealth] = useState(null)
  const [activePrimaryTab, setActivePrimaryTab] = useState('intel') // 'learn' | 'intel' | 'scenarios' — intel (competitors) active by default

  useEffect(() => {
    axios.get(API_URL ? `${API_URL}/health` : '/health')
      .then(res => setHealth(res.data))
      .catch(() => setHealth({ status: 'disconnected', database: 'disconnected' }))
  }, [])

  return (
    <div className="App">
      <header>
        <h1>Kindling</h1>
        <p>Sparking ERP fluency</p>
        <div className="header-actions">
          {health && (
            <div className="status-badge" data-ok={health.status === 'healthy'}>
              Backend: {health.status} · DB: {health.database}
            </div>
          )}
        </div>
      </header>

      <div className="app-main-layout">
        <nav
          className="primary-rail"
          role="tablist"
          aria-orientation="vertical"
        >
          <button
            type="button"
            role="tab"
            aria-selected={activePrimaryTab === 'learn'}
            className={`primary-rail-item ${activePrimaryTab === 'learn' ? 'active' : ''}`}
            onClick={() => setActivePrimaryTab('learn')}
          >
            <span className="primary-rail-title">Learning</span>
            <span className="primary-rail-sub">Skill map and ERP concepts</span>
          </button>
          <button
            type="button"
            role="tab"
            aria-selected={activePrimaryTab === 'intel'}
            className={`primary-rail-item ${activePrimaryTab === 'intel' ? 'active' : ''}`}
            onClick={() => setActivePrimaryTab('intel')}
          >
            <span className="primary-rail-title">Competitive Intel</span>
            <span className="primary-rail-sub">Battlecards, timelines, pricing</span>
          </button>
          <button
            type="button"
            role="tab"
            aria-selected={activePrimaryTab === 'scenarios'}
            className={`primary-rail-item ${activePrimaryTab === 'scenarios' ? 'active' : ''}`}
            onClick={() => setActivePrimaryTab('scenarios')}
          >
            <span className="primary-rail-title">Simulated ERP Scenarios</span>
            <span className="primary-rail-sub">Decision-driven practice runs</span>
          </button>
        </nav>

        <main className="app-content">
          {activePrimaryTab === 'learn' && <LearnView />}
          {activePrimaryTab === 'intel' && <CompetitiveIntelView />}
          {activePrimaryTab === 'scenarios' && <ScenariosView />}
        </main>
      </div>

      <footer className="app-footer">
        <span>Integrations</span>
        <a href="https://you.com" target="_blank" rel="noopener noreferrer">You.com</a>
        <span>·</span>
        <a href="https://render.com" target="_blank" rel="noopener noreferrer">Render</a>
      </footer>
    </div>
  )
}

export default App
