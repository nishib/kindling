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
          {node.depends_on?.length > 0 && (
            <span className="concept-tree-deps">depends on {node.depends_on.length}</span>
          )}
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
  const [intelFeed, setIntelFeed] = useState([])
  const [intelRefreshing, setIntelRefreshing] = useState(false)
  const [liveSearchQuery, setLiveSearchQuery] = useState('')
  const [liveSearchResults, setLiveSearchResults] = useState(null)
  const [liveSearchLoading, setLiveSearchLoading] = useState(false)
  const [health, setHealth] = useState(null)
  const [youStatus, setYouStatus] = useState('Unknown')
  const [watchlist, setWatchlist] = useState([
    {
      id: 'netsuite',
      name: 'NetSuite',
      verticals: 'Mid-market SaaS, Services',
      status: 'Monitoring',
      momentum: 'High',
      velocity: 'High',
      risk: 'High',
    },
    {
      id: 'sap',
      name: 'SAP',
      verticals: 'Enterprise, Manufacturing',
      status: 'Monitoring',
      momentum: 'Medium',
      velocity: 'Medium',
      risk: 'High',
    },
    {
      id: 'oracle',
      name: 'Oracle',
      verticals: 'Enterprise, Financials',
      status: 'Monitoring',
      momentum: 'Medium',
      velocity: 'High',
      risk: 'Medium',
    },
    {
      id: 'workday',
      name: 'Workday',
      verticals: 'HCM, Finance',
      status: 'Limited Data',
      momentum: 'Medium',
      velocity: 'Medium',
      risk: 'Medium',
    },
  ])
  const [newCompetitor, setNewCompetitor] = useState('')
  const [timelineFilter, setTimelineFilter] = useState('all')

  useEffect(() => {
    axios.get(API_URL ? `${API_URL}/health` : '/health')
      .then(res => setHealth(res.data))
      .catch(() => setHealth({ status: 'disconnected', database: 'disconnected' }))
  }, [])

  useEffect(() => {
    axios.get(API_URL ? `${API_URL}/api/intel/feed` : '/api/intel/feed')
      .then(res => setIntelFeed(Array.isArray(res.data) ? res.data : []))
      .catch(() => setIntelFeed([]))
  }, [])

  const refreshIntel = async () => {
    setIntelRefreshing(true)
    try {
      await axios.post(API_URL ? `${API_URL}/api/intel/refresh` : '/api/intel/refresh')
      const res = await axios.get(API_URL ? `${API_URL}/api/intel/feed` : '/api/intel/feed')
      setIntelFeed(Array.isArray(res.data) ? res.data : [])
    } catch {
      setIntelFeed([])
    } finally {
      setIntelRefreshing(false)
    }
  }

  const runLiveSearch = async (e) => {
    e?.preventDefault()
    const q = (typeof e?.target?.query?.value === 'string' ? e.target.query.value : liveSearchQuery).trim()
    if (!q) return
    setLiveSearchLoading(true)
    setLiveSearchResults(null)
    try {
      const res = await axios.get(API_URL ? `${API_URL}/api/intel/search` : '/api/intel/search', {
        params: { q, count: 8, freshness: 'month' },
      })
      setLiveSearchResults(res.data)
      setYouStatus('Connected')
    } catch (err) {
      setLiveSearchResults({
        web: [],
        news: [],
        query: q,
        error: err.response?.data?.error || err.message || 'Search failed',
      })
      setYouStatus('Error')
    } finally {
      setLiveSearchLoading(false)
    }
  }

  const addCompetitorToWatchlist = (e) => {
    e.preventDefault()
    const name = newCompetitor.trim()
    if (!name) return
    const id = name.toLowerCase().replace(/\s+/g, '-')
    if (watchlist.some((c) => c.id === id)) {
      setNewCompetitor('')
      return
    }
    setWatchlist((prev) => [
      ...prev,
      {
        id,
        name,
        verticals: 'Custom',
        status: 'Setup Required',
        momentum: 'Unknown',
        velocity: 'Unknown',
        risk: 'Unknown',
      },
    ])
    setNewCompetitor('')
  }

  const sortedEvents = [...intelFeed].sort((a, b) => {
    const ta = a.timestamp ? new Date(a.timestamp).getTime() : 0
    const tb = b.timestamp ? new Date(b.timestamp).getTime() : 0
    return tb - ta
  })

  const filteredEvents = timelineFilter === 'all'
    ? sortedEvents
    : sortedEvents.filter((e) => e.competitor?.toLowerCase() === timelineFilter)

  const lastCrawlAt = sortedEvents[0]?.timestamp

  const aiFocusCount = sortedEvents.filter((e) =>
    /ai|copilot|machine learning/i.test(e.content || '')
  ).length
  const upmarketCount = sortedEvents.filter((e) =>
    /enterprise|up-market|enterprise-only/i.test(e.content || '')
  ).length

  const competitorsForFilter = [
    { id: 'all', name: 'All competitors' },
    ...watchlist.map((c) => ({ id: c.id, name: c.name })),
  ]

  const hasIntel = sortedEvents.length > 0

  return (
    <div className="intel-console">
      <section className="intel-hero">
        <div>
          <h2>Competitive Intelligence Engine</h2>
          <p className="intel-hero-sub">
            Always-on monitoring for your ERP competitive landscape. Battlecards, timelines, and
            “so what?” insights instead of raw links.
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
            <div className="intel-status-row">
              <span className="intel-status-label">You.com</span>
              <span className="intel-status-pill" data-ok={youStatus === 'Connected'}>
                {youStatus}
              </span>
            </div>
            <div className="intel-status-meta">
              <span>
                Last crawl:{' '}
                {lastCrawlAt ? new Date(lastCrawlAt).toLocaleString() : 'No events yet'}
              </span>
              <span>Next refresh: ~60 minutes</span>
            </div>
          </div>
        </div>
      </section>

      {!hasIntel && (
        <section className="intel-empty-state">
          <div className="intel-empty-main">
            <h3>Trending battles to explore</h3>
            <p>
              Jump into example intel views to see how competitive monitoring works before you plug
              in your own stack.
            </p>
            <div className="intel-empty-prompts">
              <button
                type="button"
                className="intel-empty-btn"
                onClick={() => setLiveSearchQuery('NetSuite AI vs Oracle AI')}
              >
                How does NetSuite’s new AI compare to Oracle’s?
              </button>
              <button
                type="button"
                className="intel-empty-btn"
                onClick={() => setLiveSearchQuery('SAP ERP pricing changes last 90 days')}
              >
                What&apos;s changed in SAP pricing over the last 90 days?
              </button>
              <button
                type="button"
                className="intel-empty-btn"
                onClick={() => setLiveSearchQuery('Top reasons companies churn from NetSuite')}
              >
                What are the top 5 reasons companies churn from NetSuite?
              </button>
            </div>
          </div>
          <div className="intel-empty-side">
            <h4>Industry templates</h4>
            <p className="intel-empty-side-sub">
              Pick a starting vertical and we&apos;ll suggest competitors and themes.
            </p>
            <div className="intel-empty-tags">
              <span className="intel-tag">SaaS · Churn · Usage-based pricing · AI copilots</span>
              <span className="intel-tag">Manufacturing · Supply chain · WMS · ERP integration</span>
              <span className="intel-tag">Fintech · Risk · Reconciliation · Compliance</span>
            </div>
          </div>
        </section>
      )}

      <section className="intel-watchlist">
        <div className="intel-section-header">
          <div>
            <h3>Tracked competitors</h3>
            <p className="intel-section-sub">
              Your always-on watchlist across ERP and adjacent players.
            </p>
          </div>
          <form className="intel-add-form" onSubmit={addCompetitorToWatchlist}>
            <input
              type="text"
              placeholder="Add competitor (e.g. QuickBooks)"
              value={newCompetitor}
              onChange={(e) => setNewCompetitor(e.target.value)}
            />
            <button type="submit">Add</button>
          </form>
        </div>
        <div className="intel-watchlist-grid">
          {watchlist.map((c) => (
            <div key={c.id} className="intel-competitor-card">
              <div className="intel-competitor-header">
                <div className="intel-avatar">
                  <span>{c.name.charAt(0)}</span>
                </div>
                <div>
                  <h4>{c.name}</h4>
                  <p className="intel-competitor-verticals">{c.verticals}</p>
                </div>
              </div>
              <div className="intel-competitor-metrics">
                <div>
                  <span className="intel-metric-label">Status</span>
                  <span className={`intel-metric-pill status-${c.status.replace(/\s+/g, '-').toLowerCase()}`}>
                    {c.status}
                  </span>
                </div>
                <div>
                  <span className="intel-metric-label">Market momentum</span>
                  <span className="intel-metric-value">{c.momentum}</span>
                </div>
                <div>
                  <span className="intel-metric-label">Product velocity</span>
                  <span className="intel-metric-value">{c.velocity}</span>
                </div>
                <div>
                  <span className="intel-metric-label">Risk level</span>
                  <span className="intel-metric-value">{c.risk}</span>
                </div>
              </div>
            </div>
          ))}
        </div>
      </section>

      <section className="intel-live-and-timeline">
        <div className="intel-live-column">
          <h3>Live web &amp; news search</h3>
          <p className="intel-section-sub">
            Powered by You.com to pull in the latest docs, news, and forum threads.
          </p>
          <form className="intel-live-search" onSubmit={runLiveSearch}>
            <input
              type="text"
              name="query"
              className="intel-live-input"
              placeholder="Search live: e.g. NetSuite vs SAP, QuickBooks ERP…"
              value={liveSearchQuery}
              onChange={(e) => setLiveSearchQuery(e.target.value)}
              disabled={liveSearchLoading}
            />
            <button type="submit" className="intel-live-btn" disabled={liveSearchLoading}>
              {liveSearchLoading ? 'Searching…' : 'Search live'}
            </button>
          </form>
          {liveSearchResults && (
            <div className="intel-live-results">
              <h4 className="intel-live-heading">
                Live results for “{liveSearchResults.query}”
              </h4>
              {liveSearchResults.error && (
                <p className="intel-live-error">{liveSearchResults.error}</p>
              )}
              {!liveSearchResults.error && (
                <>
                  {((liveSearchResults.web || []).length > 0 ||
                    (liveSearchResults.news || []).length > 0) ? (
                    <>
                      {(liveSearchResults.news || []).length > 0 && (
                        <div className="intel-live-block">
                          <h4>News</h4>
                          <ul className="intel-live-list">
                            {(liveSearchResults.news || []).map((item, i) => (
                              <li key={i} className="intel-live-item">
                                <span className="intel-live-title">{item.title}</span>
                                {item.source_name && (
                                  <span className="intel-live-source">{item.source_name}</span>
                                )}
                                <p className="intel-live-content">{item.content}</p>
                                {item.url && (
                                  <a
                                    href={item.url}
                                    target="_blank"
                                    rel="noopener noreferrer"
                                    className="intel-link"
                                  >
                                    Read
                                  </a>
                                )}
                              </li>
                            ))}
                          </ul>
                        </div>
                      )}
                      {(liveSearchResults.web || []).length > 0 && (
                        <div className="intel-live-block">
                          <h4>Web</h4>
                          <ul className="intel-live-list">
                            {(liveSearchResults.web || []).map((item, i) => (
                              <li key={i} className="intel-live-item">
                                <span className="intel-live-title">{item.title}</span>
                                <p className="intel-live-content">{item.content}</p>
                                {item.url && (
                                  <a
                                    href={item.url}
                                    target="_blank"
                                    rel="noopener noreferrer"
                                    className="intel-link"
                                  >
                                    Source
                                  </a>
                                )}
                              </li>
                            ))}
                          </ul>
                        </div>
                      )}
                    </>
                  ) : (
                    <p className="intel-empty">
                      No live results. Try another query or expand your timeframe.
                    </p>
                  )}
                </>
              )}
            </div>
          )}
        </div>

        <div className="intel-timeline-column">
          <div className="intel-cached-heading">
            <span>Intel timeline</span>
            <button
              type="button"
              className="intel-refresh-btn"
              onClick={refreshIntel}
              disabled={intelRefreshing}
            >
              {intelRefreshing ? 'Refreshing…' : 'Refresh intel'}
            </button>
          </div>
          <div className="intel-timeline-filter">
            <label htmlFor="timeline-filter">View</label>
            <select
              id="timeline-filter"
              value={timelineFilter}
              onChange={(e) => setTimelineFilter(e.target.value)}
            >
              {competitorsForFilter.map((c) => (
                <option key={c.id} value={c.id === 'all' ? 'all' : c.name.toLowerCase()}>
                  {c.name}
                </option>
              ))}
            </select>
          </div>
          {sortedEvents.length > 0 ? (
            <ul className="intel-timeline-list">
              {filteredEvents.slice(0, 20).map((item) => (
                <li key={item.id} className="intel-event-card">
                  <div className="intel-event-header">
                    <div>
                      <span className="intel-event-competitor">
                        {item.competitor || 'Unknown competitor'}
                      </span>
                      <span className="intel-event-type">{item.type}</span>
                    </div>
                    {item.timestamp && (
                      <span className="intel-event-time">
                        {new Date(item.timestamp).toLocaleString()}
                      </span>
                    )}
                  </div>
                  <p className="intel-event-content">{item.content}</p>
                  <div className="intel-event-footer">
                    <span className="intel-event-tags">
                      {item.type && <span className="intel-tag">{item.type}</span>}
                    </span>
                    <div className="intel-event-links">
                      {item.source_url && (
                        <a
                          href={item.source_url}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="intel-link"
                        >
                          Source
                        </a>
                      )}
                    </div>
                  </div>
                </li>
              ))}
            </ul>
          ) : (
            <p className="intel-empty">
              No competitive intelligence data yet. Click Refresh to trigger the first crawl.
            </p>
          )}
        </div>
      </section>

      <section className="intel-so-what">
        <h3>So what? Cross-competitor signals</h3>
        <p className="intel-section-sub">
          Synthesized deltas across your watchlist, with suggested implications.
        </p>
        <div className="intel-so-what-grid">
          <div className="intel-so-what-card">
            <h4>AI forecasting focus</h4>
            <p className="intel-so-what-metric">
              <strong>{aiFocusCount}</strong> recent signals mentioning AI, copilots, or ML
              forecasting.
            </p>
            <ul className="intel-so-what-list">
              <li>
                This trend will increase pressure on your AI roadmap and talk tracks in mid-market
                deals.
              </li>
              <li>
                Consider a focused enablement push on how your product handles forecasting and
                anomaly detection.
              </li>
            </ul>
          </div>
          <div className="intel-so-what-card">
            <h4>Up-market motion</h4>
            <p className="intel-so-what-metric">
              <strong>{upmarketCount}</strong> events tied to enterprise-only SKUs or up-market
              positioning.
            </p>
            <ul className="intel-so-what-list">
              <li>
                Expect more head-to-heads in upper mid-market and lower enterprise opportunities.
              </li>
              <li>
                Update battlecards to clearly show where you win on implementation speed and
                total cost of ownership.
              </li>
            </ul>
          </div>
        </div>
      </section>

      <section className="intel-frameworks">
        <div className="intel-framework">
          <h3>Feature parity matrix</h3>
          <p className="intel-section-sub">
            High-level parity view across core ERP capabilities. Ideal for deal strategy and
            roadmap alignment.
          </p>
          <div className="intel-table-scroll">
            <table className="intel-matrix">
              <thead>
                <tr>
                  <th>Capability</th>
                  <th>Your product</th>
                  <th>NetSuite</th>
                  <th>SAP</th>
                  <th>Oracle</th>
                  <th>Workday</th>
                </tr>
              </thead>
              <tbody>
                <tr>
                  <td>AI forecasting</td>
                  <td>Strong</td>
                  <td>Strong</td>
                  <td>Parity</td>
                  <td>Strong</td>
                  <td>Parity</td>
                </tr>
                <tr>
                  <td>Multi-entity consolidation</td>
                  <td>Parity</td>
                  <td>Strong</td>
                  <td>Strong</td>
                  <td>Strong</td>
                  <td>Parity</td>
                </tr>
                <tr>
                  <td>Embedded analytics</td>
                  <td>Strong</td>
                  <td>Parity</td>
                  <td>Parity</td>
                  <td>Strong</td>
                  <td>Strong</td>
                </tr>
                <tr>
                  <td>Manufacturing WMS</td>
                  <td>Lagging</td>
                  <td>Parity</td>
                  <td>Strong</td>
                  <td>Strong</td>
                  <td>Unknown</td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>

        <div className="intel-framework">
          <h3>Pricing intelligence</h3>
          <p className="intel-section-sub">
            Snapshot of pricing models, deal sizes, and discount behavior across competitors.
          </p>
          <div className="intel-pricing-grid">
            {watchlist.slice(0, 4).map((c) => (
              <div key={c.id} className="intel-pricing-card">
                <h4>{c.name}</h4>
                <p className="intel-pricing-sub">Indicative ranges based on surfaced intel.</p>
                <ul className="intel-pricing-list">
                  <li>
                    <span className="intel-metric-label">Typical deal size</span>
                    <span className="intel-metric-value">
                      {c.id === 'netsuite' && '$150k–$400k ARR'}
                      {c.id === 'sap' && '$500k+ ARR'}
                      {c.id === 'oracle' && '$300k–$800k ARR'}
                      {c.id === 'workday' && '$200k–$600k ARR'}
                      {!['netsuite', 'sap', 'oracle', 'workday'].includes(c.id) && 'Unknown'}
                    </span>
                  </li>
                  <li>
                    <span className="intel-metric-label">Pricing model</span>
                    <span className="intel-metric-value">
                      {c.id === 'netsuite' && 'Seat + module-based'}
                      {c.id === 'sap' && 'License + usage-based'}
                      {c.id === 'oracle' && 'Hybrid (seat + usage)'}
                      {c.id === 'workday' && 'Seat-based'}
                      {!['netsuite', 'sap', 'oracle', 'workday'].includes(c.id) && 'To be mapped'}
                    </span>
                  </li>
                  <li>
                    <span className="intel-metric-label">Discount practices</span>
                    <span className="intel-metric-value">
                      {c.id === 'netsuite' && 'Aggressive EoQ discounting; services bundled.'}
                      {c.id === 'sap' && 'Enterprise commit-focused; multi-year incentives.'}
                      {c.id === 'oracle' && 'High list, heavy discount patterns.'}
                      {c.id === 'workday' && 'Tighter guardrails; value-based framing.'}
                      {!['netsuite', 'sap', 'oracle', 'workday'].includes(c.id) &&
                        'Monitor RFPs and forums for patterns.'}
                    </span>
                  </li>
                  <li>
                    <span className="intel-metric-label">Risk flags</span>
                    <span className="intel-metric-value">
                      {c.id === 'netsuite' && 'Implementation overages; long SOW cycles.'}
                      {c.id === 'sap' && 'Complex scopes; multi-partner dependencies.'}
                      {c.id === 'oracle' && 'Audit and licensing exposure.'}
                      {c.id === 'workday' && 'Change management and adoption effort.'}
                      {!['netsuite', 'sap', 'oracle', 'workday'].includes(c.id) &&
                        'To be derived from win/loss notes.'}
                    </span>
                  </li>
                </ul>
              </div>
            ))}
          </div>
        </div>

        <div className="intel-framework">
          <h3>Sentiment tracking</h3>
          <p className="intel-section-sub">
            Rolling signal from reviews, forums, and social mentions pulled via You.com and your
            own notes.
          </p>
          <div className="intel-sentiment-grid">
            <div className="intel-sentiment-card">
              <h4>NetSuite</h4>
              <p className="intel-sentiment-score">Overall: Mixed</p>
              <ul className="intel-sentiment-list">
                <li>Strength: Reporting flexibility and mid-market fit.</li>
                <li>Risk: Increasing frustration with support response times.</li>
                <li>Watch: Implementation partner variability by region.</li>
              </ul>
            </div>
            <div className="intel-sentiment-card">
              <h4>Oracle</h4>
              <p className="intel-sentiment-score">Overall: Positive but cautious</p>
              <ul className="intel-sentiment-list">
                <li>Strength: Depth in financial controls and analytics.</li>
                <li>Risk: Configuration complexity and long ramp timelines.</li>
                <li>Watch: Pricing predictability in renewals.</li>
              </ul>
            </div>
            <div className="intel-sentiment-card">
              <h4>SAP</h4>
              <p className="intel-sentiment-score">Overall: Polarized</p>
              <ul className="intel-sentiment-list">
                <li>Strength: Enterprise-grade breadth and ecosystem.</li>
                <li>Risk: Heavy implementation burden for smaller teams.</li>
                <li>Watch: Perception of innovation pace in AI.</li>
              </ul>
            </div>
          </div>
        </div>
      </section>
    </div>
  )
}

function App() {
  const [health, setHealth] = useState(null)
  const [activePrimaryTab, setActivePrimaryTab] = useState('learn') // 'learn' | 'intel' | 'scenarios'

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
