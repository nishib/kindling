import { useState, useEffect } from 'react'
import axios from 'axios'
import { sampleQuestions } from './mockData'
import './App.css'

const API_URL = import.meta.env.VITE_API_URL || ''

function App() {
  const [health, setHealth] = useState(null)
  const [syncStatus, setSyncStatus] = useState(null)
  const [intelFeed, setIntelFeed] = useState([])
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
        {syncStatus && (syncStatus.next_sync_at || syncStatus.last_sync_at) && (
          <div className="sync-status">
            {syncStatus.last_sync_at && (
              <span>Last sync: {new Date(syncStatus.last_sync_at).toLocaleString()}</span>
            )}
            {syncStatus.next_sync_at && (
              <strong>Next sync: {new Date(syncStatus.next_sync_at).toLocaleString()}</strong>
            )}
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

      {intelFeed.length > 0 && (
        <section className="intel-feed">
          <h2>Competitive Intelligence Feed</h2>
          <p className="intel-feed-sub">You.com research — Intercom, Zendesk, Gorgias</p>
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
