import { useEffect, useMemo, useRef, useState } from 'react'
import axios from 'axios'

const API_URL = import.meta.env.VITE_API_URL || ''

// Local types (JS version of the spec)
export const VIEW_STATES = {
  DASHBOARD: 'DASHBOARD',
  AP_MODULE: 'AP_MODULE',
  REV_REC_MODULE: 'REV_REC_MODULE',
  GL_RECON_MODULE: 'GL_RECON_MODULE',
}

const INITIAL_GAME_STATE = {
  view: VIEW_STATES.DASHBOARD,
  periodStatus: 'OPEN',
  tasks: {
    apMismatch: true,
    revenueUnrecognized: true,
    suspenseBalance: true,
  },
}

// Helper: compute mentor sentiment + full message from game state + last action
function computeMentorMessage(gameState, lastEvent) {
  const { view, periodStatus, tasks } = gameState
  const { apMismatch, revenueUnrecognized, suspenseBalance } = tasks

  // Celebration on successful close
  if (periodStatus === 'CLOSED') {
    return {
      sentiment: 'celebrating',
      message:
        'You closed the period cleanly. All Validation Exceptions are cleared and the GL is ready for reporting. Nice work operating like a Controller.',
    }
  }

  // Validation failed from dashboard
  if (lastEvent === 'ATTEMPTED_CLOSE_WITH_ISSUES') {
    return {
      sentiment: 'warning',
      message:
        'You attempted to close with open Validation Exceptions. Let’s use the Validation Exceptions panel to jump into AP, Revenue Recognition, and GL Reconciliation to clear each item.',
    }
  }

  // Task-specific success messages when they flip to resolved (handled via lastEvent)
  if (lastEvent === 'AP_RESOLVED') {
    return {
      sentiment: 'happy',
      message:
        'Great job. Posting creates the immutable record in the ledger. Now Accounts Payable and the general ledger are aligned for this invoice.',
    }
  }
  if (lastEvent === 'REV_REC_RESOLVED') {
    return {
      sentiment: 'happy',
      message:
        'Perfect. Now the revenue is spread over 12 months — this is how we stay compliant with ASC 606 and avoid front-loading revenue.',
    }
  }
  if (lastEvent === 'GL_RECON_RESOLVED') {
    return {
      sentiment: 'happy',
      message:
        'Correct. We never leave items in Suspense at month-end. Reconciling to Office Supplies keeps the GL clean and ready for audit.',
    }
  }

  // Module-specific guidance
  if (view === VIEW_STATES.AP_MODULE) {
    if (apMismatch) {
      return {
        sentiment: 'warning',
        message:
          'Notice the Draft status? In an ERP, an invoice does not exist in the books until it is Posted to Ledger. Once posted, the AP sub-ledger and general ledger will agree.',
      }
    }
    return {
      sentiment: 'happy',
      message:
        'Your AP sub-ledger is now aligned with the GL for this invoice. This is a core control before attempting to close the period.',
    }
  }

  if (view === VIEW_STATES.REV_REC_MODULE) {
    if (revenueUnrecognized) {
      return {
        sentiment: 'warning',
        message:
          'We need to generate a schedule so revenue is recognized over time, not all at once. For a 12‑month contract, you should expect 12 monthly recognition entries.',
      }
    }
    return {
      sentiment: 'happy',
      message:
        'Your revenue schedule is now spreading the contract over time. This keeps reported ARR and GAAP revenue in sync with ASC 606.',
    }
  }

  if (view === VIEW_STATES.GL_RECON_MODULE) {
    if (suspenseBalance) {
      return {
        sentiment: 'warning',
        message:
          'There is a balance sitting in Suspense. At month-end, we must reconcile items into the correct account so the GL is ready for close.',
      }
    }
    return {
      sentiment: 'happy',
      message:
        'Good reconciliation work. Clearing Suspense into the proper account keeps your trial balance clean and reduces audit questions.',
    }
  }

  // Dashboard guidance
  if (view === VIEW_STATES.DASHBOARD) {
    if (apMismatch || revenueUnrecognized || suspenseBalance) {
      return {
        sentiment: 'warning',
        message:
          'I see open Validation Exceptions for this period. Before you Close Period, you need AP to match the GL, revenue to be scheduled, and Suspense cleared.',
      }
    }
    return {
      sentiment: 'neutral',
      message:
        'Nice work clearing the underlying issues. Once AP, revenue, and Suspense are clean, Controllers can confidently close the period.',
    }
  }

  // Fallback
  return {
    sentiment: 'neutral',
    message:
      'You are operating inside the month-end close workspace. Use AP, Revenue Recognition, and GL Reconciliation to clear Validation Exceptions before closing.',
  }
}

// Hook: typing effect + Gemini-backed mentor messages
function useAiMentor(gameState, lastEvent) {
  const [displayedMessage, setDisplayedMessage] = useState('')
  const [isTyping, setIsTyping] = useState(false)
  const [sentiment, setSentiment] = useState('neutral')

  const previousFullMessageRef = useRef('')
  const typingIntervalRef = useRef(null)

  // Local fallback if backend/Gemini is unavailable
  const { sentiment: scriptedSentiment, message: scriptedMessage } = useMemo(
    () => computeMentorMessage(gameState, lastEvent),
    [gameState, lastEvent]
  )

  useEffect(() => {
    let cancelled = false

    const run = async () => {
      setIsTyping(true)

      const payload = {
        view: gameState.view,
        periodStatus: gameState.periodStatus,
        tasks: gameState.tasks,
        lastEvent: lastEvent || null,
      }

      let full = ''
      let nextSentiment = scriptedSentiment

      try {
        const base = API_URL || ''
        const res = await axios.post(`${base}/api/mentor/month-end`, payload, {
          timeout: 12000,
        })
        const data = res.data || {}
        full = (data.message || '').trim()
        nextSentiment = data.sentiment || scriptedSentiment
      } catch {
        // Fallback to scripted guidance on any error
        full = scriptedMessage || ''
        nextSentiment = scriptedSentiment
      }

      if (cancelled) return

      if (!full || full === previousFullMessageRef.current) {
        setSentiment(nextSentiment)
        if (!full) {
          setDisplayedMessage('')
          setIsTyping(false)
        } else {
          setDisplayedMessage(full)
          setIsTyping(false)
        }
        return
      }

      if (typingIntervalRef.current) {
        clearInterval(typingIntervalRef.current)
      }

      previousFullMessageRef.current = full
      setSentiment(nextSentiment)
      setDisplayedMessage('')

      let index = 0
      const interval = setInterval(() => {
        index += 1
        setDisplayedMessage(full.slice(0, index))
        if (index >= full.length) {
          clearInterval(interval)
          typingIntervalRef.current = null
          setIsTyping(false)
        }
      }, 18)

      typingIntervalRef.current = interval
    }

    run()

    return () => {
      cancelled = true
      if (typingIntervalRef.current) {
        clearInterval(typingIntervalRef.current)
        typingIntervalRef.current = null
      }
    }
  }, [gameState, lastEvent, scriptedMessage, scriptedSentiment])

  return {
    sentiment,
    message: displayedMessage,
    isTyping,
  }
}

function AiMentorPanel({ mentorState }) {
  const { sentiment, message, isTyping } = mentorState

  const sentimentClass =
    sentiment === 'warning'
      ? 'mentor-card-warning'
      : sentiment === 'happy'
      ? 'mentor-card-happy'
      : sentiment === 'celebrating'
      ? 'mentor-card-celebrating'
      : 'mentor-card-neutral'

  return (
    <div className={`mentor-panel-horizontal ${sentimentClass}`}>
      <div className="mentor-header-horizontal">
        <div className="mentor-avatar-wrapper">
          <div className="mentor-avatar">
            <span className="mentor-avatar-initials">AI</span>
          </div>
          <span className="mentor-status-dot" />
        </div>
        <div className="mentor-header-text-horizontal">
          <h4 className="mentor-title-horizontal">AI Coach</h4>
        </div>
      </div>
      <div className="mentor-body-horizontal">
        <p className="mentor-message-horizontal">{message || 'Loading guidance…'}</p>
        {isTyping && (
          <div className="mentor-typing">
            <span className="mentor-dot" />
            <span className="mentor-dot" />
            <span className="mentor-dot" />
          </div>
        )}
      </div>
    </div>
  )
}

function DashboardView({ gameState, onCloseAttempt, onNavigate }) {
  const { periodStatus, tasks } = gameState
  const hasOpenIssues =
    tasks.apMismatch || tasks.revenueUnrecognized || tasks.suspenseBalance

  const openIssuesCount = [tasks.apMismatch, tasks.revenueUnrecognized, tasks.suspenseBalance].filter(Boolean).length

  return (
    <section className="monthend-dashboard">
      {/* Step-by-step instructions banner */}
      {hasOpenIssues && (
        <div className="monthend-instructions-banner">
          <div className="monthend-instructions-header">
            <span className="monthend-instructions-badge">Getting Started</span>
            <h4>How to close the period ({openIssuesCount} issues remaining)</h4>
          </div>
          <div className="monthend-instructions-steps">
            <div className="monthend-instruction-step">
              <span className="monthend-step-number">1</span>
              <div>
                <strong>Review Exceptions</strong>
                <p>Check the 3 validation exceptions below that are blocking the close</p>
              </div>
            </div>
            <div className="monthend-instruction-step">
              <span className="monthend-step-number">2</span>
              <div>
                <strong>Navigate to Module</strong>
                <p>Click on a module button to jump into the ERP workspace</p>
              </div>
            </div>
            <div className="monthend-instruction-step">
              <span className="monthend-step-number">3</span>
              <div>
                <strong>Fix & Return</strong>
                <p>Complete the action in each module, then return to dashboard</p>
              </div>
            </div>
            <div className="monthend-instruction-step">
              <span className="monthend-step-number">4</span>
              <div>
                <strong>Close Period</strong>
                <p>Once all exceptions are cleared, click "Close Period" button</p>
              </div>
            </div>
          </div>
        </div>
      )}

      <header className="monthend-dashboard-header">
        <div>
          <h3>Month-End Close: Oct 2024</h3>
          <p className="monthend-dashboard-sub">
            {periodStatus === 'CLOSED'
              ? '✓ Period successfully closed! All validation exceptions resolved.'
              : `${openIssuesCount} validation exception${openIssuesCount !== 1 ? 's' : ''} must be cleared before closing.`
            }
          </p>
        </div>
        <div className="monthend-dashboard-meta">
          <span
            className="monthend-status-pill"
            data-status={periodStatus === 'CLOSED' ? 'closed' : 'open'}
          >
            Period status: <strong>{periodStatus}</strong>
          </span>
          <button
            type="button"
            className="monthend-close-btn"
            onClick={onCloseAttempt}
            disabled={periodStatus === 'CLOSED'}
          >
            {hasOpenIssues ? `Close Period (${openIssuesCount} issues)` : 'Close Period'}
          </button>
        </div>
      </header>

      {/* Horizontal layout for exceptions and modules */}
      <div className="monthend-dashboard-horizontal">
        <div className="monthend-exceptions-list">
          <h4>Validation Exceptions {!hasOpenIssues && '✓'}</h4>
          <div className="monthend-exception-cards">
            <div className={`monthend-exception-card ${!tasks.apMismatch ? 'cleared' : ''}`}>
              <div className="monthend-exception-header">
                <span className={`monthend-exception-status ${!tasks.apMismatch ? 'cleared' : 'open'}`}>
                  {tasks.apMismatch ? '!' : '✓'}
                </span>
                <strong>AP Sub-ledger Mismatch</strong>
              </div>
              <p>AP doesn't match general ledger</p>
              <button
                type="button"
                className="monthend-exception-btn"
                onClick={() => onNavigate(VIEW_STATES.AP_MODULE)}
                disabled={!tasks.apMismatch}
              >
                {tasks.apMismatch ? 'Fix in AP Module →' : 'Resolved'}
              </button>
            </div>

            <div className={`monthend-exception-card ${!tasks.revenueUnrecognized ? 'cleared' : ''}`}>
              <div className="monthend-exception-header">
                <span className={`monthend-exception-status ${!tasks.revenueUnrecognized ? 'cleared' : 'open'}`}>
                  {tasks.revenueUnrecognized ? '!' : '✓'}
                </span>
                <strong>Revenue Unrecognized</strong>
              </div>
              <p>Revenue schedule not generated</p>
              <button
                type="button"
                className="monthend-exception-btn"
                onClick={() => onNavigate(VIEW_STATES.REV_REC_MODULE)}
                disabled={!tasks.revenueUnrecognized}
              >
                {tasks.revenueUnrecognized ? 'Fix in Rev Rec →' : 'Resolved'}
              </button>
            </div>

            <div className={`monthend-exception-card ${!tasks.suspenseBalance ? 'cleared' : ''}`}>
              <div className="monthend-exception-header">
                <span className={`monthend-exception-status ${!tasks.suspenseBalance ? 'cleared' : 'open'}`}>
                  {tasks.suspenseBalance ? '!' : '✓'}
                </span>
                <strong>Suspense Balance</strong>
              </div>
              <p>Unreconciled items in Suspense</p>
              <button
                type="button"
                className="monthend-exception-btn"
                onClick={() => onNavigate(VIEW_STATES.GL_RECON_MODULE)}
                disabled={!tasks.suspenseBalance}
              >
                {tasks.suspenseBalance ? 'Fix in GL Recon →' : 'Resolved'}
              </button>
            </div>
          </div>
        </div>
      </div>
    </section>
  )
}

function ValidationModal({ gameState, onClose, onNavigate }) {
  const { tasks } = gameState

  const rows = [
    tasks.apMismatch && {
      key: 'ap',
      label: 'AP Mismatch',
      description: 'Accounts Payable sub-ledger does not match the general ledger.',
      target: VIEW_STATES.AP_MODULE,
    },
    tasks.revenueUnrecognized && {
      key: 'rev',
      label: 'Revenue Unrecognized',
      description: 'Revenue schedule not generated for the contract.',
      target: VIEW_STATES.REV_REC_MODULE,
    },
    tasks.suspenseBalance && {
      key: 'gl',
      label: 'Suspense Balance',
      description: 'Suspense account contains unreconciled items.',
      target: VIEW_STATES.GL_RECON_MODULE,
    },
  ].filter(Boolean)

  if (rows.length === 0) return null

  return (
    <div className="monthend-modal-backdrop" role="dialog" aria-modal="true">
      <div className="monthend-modal">
        <header className="monthend-modal-header">
          <h4>Validation Exceptions</h4>
          <button
            type="button"
            className="monthend-modal-close"
            onClick={onClose}
            aria-label="Close"
          >
            ×
          </button>
        </header>
        <p className="monthend-modal-sub">
          These Validation Exceptions are currently blocking the period from closing.
          Use Fix Issue to navigate directly into the right ERP module.
        </p>
        <ul className="monthend-modal-list">
          {rows.map((row) => (
            <li key={row.key} className="monthend-modal-row">
              <div className="monthend-modal-text">
                <span className="monthend-modal-label">{row.label}</span>
                <span className="monthend-modal-desc">{row.description}</span>
              </div>
              <button
                type="button"
                className="monthend-modal-btn"
                onClick={() => {
                  onNavigate(row.target)
                  onClose()
                }}
              >
                Fix Issue
              </button>
            </li>
          ))}
        </ul>
      </div>
    </div>
  )
}

function ApModule({ resolved, onPost, onBack }) {
  return (
    <section className="monthend-module">
      <button type="button" className="monthend-back-btn" onClick={onBack}>
        ← Back to Dashboard
      </button>
      <header className="monthend-module-header">
        <div>
          <span className="monthend-module-breadcrumb">Step 1 of 3</span>
          <h3>Accounts Payable module</h3>
          <p className="monthend-module-sub">
            Clear the variance between the AP sub-ledger and general ledger by posting a Draft invoice.
          </p>
        </div>
      </header>
      <div className="monthend-module-body">
        <div className="monthend-card">
          <h4>Invoice workspace</h4>
          <p className="monthend-card-sub">
            This is a single example invoice coming from a procurement system into the
            ERP.
          </p>
          <table className="monthend-table">
            <thead>
              <tr>
                <th>Vendor</th>
                <th>Invoice</th>
                <th>Amount</th>
                <th>Status</th>
              </tr>
            </thead>
            <tbody>
              <tr>
                <td>Acme Office Supply</td>
                <td>INV-2048</td>
                <td>$8,250.00</td>
                <td>{resolved ? 'Posted' : 'Draft'}</td>
              </tr>
            </tbody>
          </table>
          {!resolved && (
            <button type="button" className="monthend-primary-btn" onClick={onPost}>
              Post to Ledger
            </button>
          )}
          {resolved && (
            <p className="monthend-success-hint">
              This invoice is now Posted to Ledger. The AP balance for this document
              agrees with the GL.
            </p>
          )}
        </div>
      </div>
    </section>
  )
}

function RevRecModule({ resolved, onGenerate, onBack }) {
  const scheduleRows = useMemo(() => {
    if (!resolved) return []
    // Simple 12-month straight-line schedule for $120k
    const amount = 10000
    return Array.from({ length: 12 }).map((_, idx) => ({
      month: idx + 1,
      label: `Month ${idx + 1}`,
      amount,
    }))
  }, [resolved])

  return (
    <section className="monthend-module">
      <button type="button" className="monthend-back-btn" onClick={onBack}>
        ← Back to Dashboard
      </button>
      <header className="monthend-module-header">
        <div>
          <span className="monthend-module-breadcrumb">Step 2 of 3</span>
          <h3>Revenue Recognition module</h3>
          <p className="monthend-module-sub">
            Turn a single $120k contract into a time-based revenue schedule that is compliant with ASC 606.
          </p>
        </div>
      </header>
      <div className="monthend-module-body">
        <div className="monthend-card">
          <h4>Contract overview</h4>
          <p className="monthend-card-sub">
            Customer: <strong>Northern Lights Analytics</strong> · Total value:{' '}
            <strong>$120,000</strong> · Term: <strong>12 months</strong>
          </p>
          {!resolved && (
            <button
              type="button"
              className="monthend-primary-btn"
              onClick={onGenerate}
            >
              Generate Schedule
            </button>
          )}
          {resolved && (
            <>
              <p className="monthend-success-hint">
                Schedule generated. Revenue is now recognized evenly across the contract
                term instead of all at once.
              </p>
              <table className="monthend-table monthend-table-compact">
                <thead>
                  <tr>
                    <th>Period</th>
                    <th>Recognized revenue</th>
                  </tr>
                </thead>
                <tbody>
                  {scheduleRows.map((row) => (
                    <tr key={row.month}>
                      <td>{row.label}</td>
                      <td>${row.amount.toLocaleString()}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </>
          )}
        </div>
      </div>
    </section>
  )
}

function GlReconModule({ resolved, onReconcile, onBack }) {
  const [selectedAccount, setSelectedAccount] = useState('Suspense')

  const handleReconcile = () => {
    if (selectedAccount === 'Office Supplies') {
      onReconcile()
    }
  }

  return (
    <section className="monthend-module">
      <button type="button" className="monthend-back-btn" onClick={onBack}>
        ← Back to Dashboard
      </button>
      <header className="monthend-module-header">
        <div>
          <span className="monthend-module-breadcrumb">Step 3 of 3</span>
          <h3>GL Reconciliation module</h3>
          <p className="monthend-module-sub">
            Clear the Suspense account by reconciling this transaction to the correct GL account.
          </p>
        </div>
      </header>
      <div className="monthend-module-body">
        <div className="monthend-card">
          <h4>Transaction in Suspense</h4>
          <p className="monthend-card-sub">
            A transaction is temporarily parked in <strong>Suspense</strong> until
            Controllers decide on the right account.
          </p>
          <table className="monthend-table">
            <thead>
              <tr>
                <th>Date</th>
                <th>Description</th>
                <th>Current account</th>
                <th>Amount</th>
              </tr>
            </thead>
            <tbody>
              <tr>
                <td>10/18/2024</td>
                <td>Corporate credit card purchase</td>
                <td>{resolved ? 'Office Supplies' : 'Suspense'}</td>
                <td>$2,450.00</td>
              </tr>
            </tbody>
          </table>

          {!resolved && (
            <>
              <label className="monthend-field">
                <span>Reclassify to account</span>
                <select
                  value={selectedAccount}
                  onChange={(e) => setSelectedAccount(e.target.value)}
                >
                  <option value="Suspense">Suspense</option>
                  <option value="Office Supplies">Office Supplies</option>
                  <option value="Travel & Entertainment">Travel &amp; Entertainment</option>
                  <option value="Software & Subscriptions">Software &amp; Subscriptions</option>
                </select>
              </label>
              <button
                type="button"
                className="monthend-primary-btn"
                onClick={handleReconcile}
              >
                Reconcile
              </button>
              {selectedAccount !== 'Office Supplies' && selectedAccount !== 'Suspense' && (
                <p className="monthend-warning-hint">
                  Only Office Supplies is appropriate given the description. Suspense is
                  temporary; Controllers clear it at month-end.
                </p>
              )}
            </>
          )}

          {resolved && (
            <p className="monthend-success-hint">
              The Suspense item is now reconciled into Office Supplies. Your GL is cleaner
              and easier to review at close.
            </p>
          )}
        </div>
      </div>
    </section>
  )
}

function MonthEndGame() {
  const [gameState, setGameState] = useState(INITIAL_GAME_STATE)
  const [showValidation, setShowValidation] = useState(false)
  const [lastEvent, setLastEvent] = useState(null)

  const mentorState = useAiMentor(gameState, lastEvent)

  const goToView = (view) => {
    setGameState((prev) => ({
      ...prev,
      view,
    }))
  }

  const handleCloseAttempt = () => {
    const { tasks } = gameState
    const hasOpenIssues =
      tasks.apMismatch || tasks.revenueUnrecognized || tasks.suspenseBalance

    if (hasOpenIssues) {
      setShowValidation(true)
      setLastEvent('ATTEMPTED_CLOSE_WITH_ISSUES')
      return
    }

    setGameState((prev) => ({
      ...prev,
      periodStatus: 'CLOSED',
    }))
    setLastEvent('PERIOD_CLOSED')
  }

  const handlePostInvoice = () => {
    setGameState((prev) => ({
      ...prev,
      tasks: {
        ...prev.tasks,
        apMismatch: false,
      },
    }))
    setLastEvent('AP_RESOLVED')
  }

  const handleGenerateSchedule = () => {
    setGameState((prev) => ({
      ...prev,
      tasks: {
        ...prev.tasks,
        revenueUnrecognized: false,
      },
    }))
    setLastEvent('REV_REC_RESOLVED')
  }

  const handleReconcile = () => {
    setGameState((prev) => ({
      ...prev,
      tasks: {
        ...prev.tasks,
        suspenseBalance: false,
      },
    }))
    setLastEvent('GL_RECON_RESOLVED')
  }

  const handleReset = () => {
    setGameState(INITIAL_GAME_STATE)
    setShowValidation(false)
    setLastEvent(null)
  }

  return (
    <div className="monthend-root-fullscreen">
      {/* AI Mentor at top - horizontal */}
      <AiMentorPanel mentorState={mentorState} />

      {/* Main content full-width */}
      <div className="monthend-main-fullscreen">
        <div className="monthend-header-row">
          <div>
            <h2 className="monthend-title">Month-End Close game</h2>
            <p className="monthend-sub">
              Practice closing the books across AP, Revenue Recognition, and GL
              Reconciliation with a Controller-style AI Mentor.
            </p>
          </div>
          <button type="button" className="monthend-reset-btn" onClick={handleReset}>
            Restart scenario
          </button>
        </div>

        {gameState.view === VIEW_STATES.DASHBOARD && (
          <DashboardView
            gameState={gameState}
            onCloseAttempt={handleCloseAttempt}
            onNavigate={goToView}
          />
        )}

        {gameState.view === VIEW_STATES.AP_MODULE && (
          <ApModule
            resolved={!gameState.tasks.apMismatch}
            onPost={handlePostInvoice}
            onBack={() => goToView(VIEW_STATES.DASHBOARD)}
          />
        )}

        {gameState.view === VIEW_STATES.REV_REC_MODULE && (
          <RevRecModule
            resolved={!gameState.tasks.revenueUnrecognized}
            onGenerate={handleGenerateSchedule}
            onBack={() => goToView(VIEW_STATES.DASHBOARD)}
          />
        )}

        {gameState.view === VIEW_STATES.GL_RECON_MODULE && (
          <GlReconModule
            resolved={!gameState.tasks.suspenseBalance}
            onReconcile={handleReconcile}
            onBack={() => goToView(VIEW_STATES.DASHBOARD)}
          />
        )}
      </div>

      {showValidation && (
        <ValidationModal
          gameState={gameState}
          onClose={() => setShowValidation(false)}
          onNavigate={goToView}
        />
      )}
    </div>
  )
}

export default MonthEndGame

