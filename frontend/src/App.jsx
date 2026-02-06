import { useState, useEffect } from 'react'
import axios from 'axios'
import { sampleQuestions } from './mockData'
import './App.css'

const API_URL = import.meta.env.VITE_API_URL || ''

function App() {
  const [health, setHealth] = useState(null)
  const [syncStatus, setSyncStatus] = useState(null)
  const [syncTriggering, setSyncTriggering] = useState(false)
  const [intelFeed, setIntelFeed] = useState([])
  const [renderUsage, setRenderUsage] = useState(null)
  const [intelRefreshing, setIntelRefreshing] = useState(false)
  const [question, setQuestion] = useState('')
  const [loading, setLoading] = useState(false)
  const [messages, setMessages] = useState([])

  useEffect(() => {
    axios.get(API_URL ? `${API_URL}/health` : '/health')
      .then(res => setHealth(res.data))
      .catch(() => setHealth({ status: 'disconnected', database: 'disconnected' }))
  }, [])

  useEffect(() => {
    axios.get(API_URL ? `${API_URL}/api/sync/status` : '/api/sync/status')
      .then(res => setSyncStatus(res.data))
      .catch(() => setSyncStatus(null))
  }, [])

  useEffect(() => {
    axios.get(API_URL ? `${API_URL}/api/intel/feed` : '/api/intel/feed')
      .then(res => setIntelFeed(Array.isArray(res.data) ? res.data : []))
      .catch(() => setIntelFeed([]))
  }, [])

  useEffect(() => {
    axios.get(API_URL ? `${API_URL}/api/render/usage` : '/api/render/usage')
      .then(res => setRenderUsage(res.data))
      .catch(() => setRenderUsage({ ok: false, error: 'Failed to load' }))
  }, [])

  const triggerSync = async () => {
    setSyncTriggering(true)
    try {
      const res = await axios.post(API_URL ? `${API_URL}/api/sync/trigger` : '/api/sync/trigger')
      setSyncStatus(prev => ({ ...prev, ...res.data, last_sync_at: res.data?.last_sync_at, next_sync_at: res.data?.next_sync_at }))
      const statusRes = await axios.get(API_URL ? `${API_URL}/api/sync/status` : '/api/sync/status')
      setSyncStatus(statusRes.data)
    } catch {
      setSyncStatus(prev => prev || {})
    } finally {
      setSyncTriggering(false)
    }
  }

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

  const handleAsk = async (q) => {
    const text = (typeof q === 'string' ? q : question).trim()
    if (!text) return
    setQuestion('')
    setMessages(prev => [...prev, { role: 'user', text }])
    setLoading(true)
    try {
      const res = await axios.post(API_URL ? `${API_URL}/api/ask` : '/api/ask', { question: text })
      setMessages(prev => [...prev, {
        role: 'assistant',
        text: res.data.answer,
        citations: res.data.citations || [],
      }])
    } catch (err) {
      setMessages(prev => [...prev, {
        role: 'assistant',
        text: 'Sorry, the backend could not answer. Check that the API is running and GEMINI_API_KEY is set.',
        citations: [],
      }])
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="App">
      <header>
        <h1>OnboardAI</h1>
        <p>AI-powered onboarding for Velora employees</p>
        {health && (
          <div className="status-badge" data-ok={health.status === 'healthy'}>
            Backend: {health.status} · DB: {health.database}
          </div>
        )}
        {syncStatus && (
          <div className="sync-status">
            {syncStatus.last_sync_at && (
              <span>Last sync (Composio): {new Date(syncStatus.last_sync_at).toLocaleString()}</span>
            )}
            {syncStatus.next_sync_at && (
              <strong>Next sync: {new Date(syncStatus.next_sync_at).toLocaleString()}</strong>
            )}
            <button type="button" className="sync-trigger-btn" onClick={triggerSync} disabled={syncTriggering}>
              {syncTriggering ? 'Syncing…' : 'Trigger sync'}
            </button>
          </div>
        )}
      </header>

      <section className="chat">
        <div className="chat-messages">
          {messages.length === 0 && (
            <div className="chat-placeholder">
              <p>Ask anything about Velora: product, team, competitors, roadmap.</p>
              <div className="sample-questions">
                {sampleQuestions.slice(0, 6).map((q, i) => (
                  <button
                    key={i}
                    type="button"
                    className="sample-q"
                    onClick={() => handleAsk(q)}
                  >
                    {q}
                  </button>
                ))}
              </div>
            </div>
          )}
          {messages.map((msg, i) => (
            <div key={i} className={`message message-${msg.role}`}>
              <div className="message-text">{msg.text}</div>
              {msg.citations && msg.citations.length > 0 && (
                <ul className="citations">
                  {msg.citations.map((c, j) => (
                    <li key={j} className="citation">
                      <span className="citation-source">{c.source}</span>
                      <span className="citation-title">{c.title}</span>
                      {c.snippet && <span className="citation-snippet">{c.snippet}</span>}
                    </li>
                  ))}
                </ul>
              )}
            </div>
          ))}
          {loading && <div className="message message-assistant loading">Thinking…</div>}
        </div>
        <form
          className="chat-form"
          onSubmit={(e) => { e.preventDefault(); handleAsk(); }}
        >
          <input
            type="text"
            className="chat-input"
            placeholder="Ask a question about Velora…"
            value={question}
            onChange={(e) => setQuestion(e.target.value)}
            disabled={loading}
          />
          <button type="submit" className="chat-submit" disabled={loading}>
            Ask
          </button>
        </form>
      </section>

      <section className="intel-feed">
        <h2>Competitive Intelligence Feed (You.com)</h2>
        <p className="intel-feed-sub">Phase 4 — Intercom, Zendesk, Gorgias. Set YOU_API_KEY to refresh.</p>
        <button type="button" className="intel-refresh-btn" onClick={refreshIntel} disabled={intelRefreshing}>
          {intelRefreshing ? 'Refreshing…' : 'Refresh intel'}
        </button>
        {intelFeed.length > 0 ? (
          <ul className="intel-list">
            {intelFeed.slice(0, 10).map((item) => (
              <li key={item.id} className="intel-item">
                <span className="intel-competitor">{item.competitor}</span>
                <span className="intel-type">{item.type}</span>
                <p className="intel-content">{item.content}</p>
                {item.timestamp && (
                  <span className="intel-time">{new Date(item.timestamp).toLocaleString()}</span>
                )}
                {item.source_url && (
                  <a href={item.source_url} target="_blank" rel="noopener noreferrer" className="intel-link">Source</a>
                )}
              </li>
            ))}
          </ul>
        ) : (
          <p className="intel-empty">No intel yet. Click Refresh to fetch from You.com (requires YOU_API_KEY in backend).</p>
        )}
      </section>

      {renderUsage && (
        <section className="render-usage">
          <h2>Render Usage (Phase 5)</h2>
          <p className="render-usage-sub">Services and bandwidth from Render API</p>
          {!renderUsage.ok ? (
            <div className="render-usage-error">
              {renderUsage.error || 'Render usage unavailable. Set RENDER_API_KEY in backend env.'}
            </div>
          ) : (
            <>
              {renderUsage.owners?.length > 0 && (
                <div className="render-usage-block">
                  <h3>Workspaces</h3>
                  <ul className="render-usage-list">
                    {renderUsage.owners.map((o) => (
                      <li key={o.id}><span className="render-usage-label">{o.name || o.id}</span></li>
                    ))}
                  </ul>
                </div>
              )}
              {renderUsage.services?.length > 0 && (
                <div className="render-usage-block">
                  <h3>Services</h3>
                  <ul className="render-usage-list">
                    {renderUsage.services.map((s) => (
                      <li key={s.id}>
                        <span className="render-usage-name">{s.name}</span>
                        <span className="render-usage-type">{s.type || '—'}</span>
                        {s.serviceDetails && (
                          <a href={s.serviceDetails} target="_blank" rel="noopener noreferrer" className="render-usage-link">Open</a>
                        )}
                      </li>
                    ))}
                  </ul>
                </div>
              )}
              {renderUsage.bandwidth?.length > 0 && (
                <div className="render-usage-block">
                  <h3>Bandwidth / metrics</h3>
                  <ul className="render-usage-list">
                    {renderUsage.bandwidth.map((b) => (
                      <li key={b.serviceId}>
                        <span className="render-usage-name">{b.serviceName}</span>
                        {b.error ? (
                          <span className="render-usage-muted">{b.error}</span>
                        ) : (
                          <span className="render-usage-muted">
                            {b.data ? `${Array.isArray(b.data) ? b.data.length : 0} data points` : '—'}
                          </span>
                        )}
                      </li>
                    ))}
                  </ul>
                </div>
              )}
              {renderUsage.ok && !renderUsage.owners?.length && !renderUsage.services?.length && (
                <p className="render-usage-muted">No workspaces or services returned.</p>
              )}
            </>
          )}
        </section>
      )}

      <footer className="sponsors">
        <span>Powered by</span>
        <a href="https://composio.dev" target="_blank" rel="noopener noreferrer">Composio</a>
        <span>·</span>
        <a href="https://you.com" target="_blank" rel="noopener noreferrer">You.com</a>
        <span>·</span>
        <a href="https://render.com" target="_blank" rel="noopener noreferrer">Render</a>
      </footer>
    </div>
  )
}

export default App
