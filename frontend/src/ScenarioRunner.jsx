function ScenarioRunner({ run, loading, onDecision, onAskCoach, coachMessages }) {
  const { template, state, current_step: currentStep, synthetic_data: syntheticData } = run

  const datasets = syntheticData?.datasets || {}
  const company = syntheticData?.company_profile || {}
  const artifactsByStep = syntheticData?.artifacts_by_step || {}
  const currentArtifacts = artifactsByStep[currentStep.id] || []

  const isRevenueScenario = template.id === 'rev-rec-001'

  const handleAsk = (e) => {
    e.preventDefault()
    const value = e.target.question.value.trim()
    if (!value) return
    onAskCoach(value)
    e.target.reset()
  }

  const renderTable = (title, rows, columns) => {
    if (!rows || rows.length === 0) return null
    return (
      <div className="scenario-table">
        <h4>{title}</h4>
        <div className="scenario-table-scroll">
          <table>
            <thead>
              <tr>
                {columns.map((col) => (
                  <th key={col.key}>{col.label}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {rows.slice(0, 6).map((row, idx) => (
                <tr key={idx}>
                  {columns.map((col) => (
                    <td key={col.key}>{row[col.key]}</td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    )
  }

  const renderArtifacts = (artifacts) => {
    if (!artifacts || artifacts.length === 0) return null

    return (
      <div className="scenario-artifacts">
        {artifacts.map((artifact) => {
          if (artifact.type === 'invoice') {
            const c = artifact.content || {}
            const lines = c.lines || []
            return (
              <div key={artifact.id} className="scenario-artifact-card scenario-artifact-invoice">
                <h4>{artifact.title}</h4>
                <p className="scenario-artifact-meta">
                  Customer: <strong>{c.customer}</strong> · Date: <strong>{c.date}</strong> · Total:{' '}
                  <strong>${c.total?.toLocaleString?.() ?? c.total}</strong>
                </p>
                {lines.length > 0 && (
                  <table className="scenario-artifact-table">
                    <thead>
                      <tr>
                        <th>Item</th>
                        <th>Amount</th>
                        <th>Rev rule</th>
                      </tr>
                    </thead>
                    <tbody>
                      {lines.map((line, idx) => (
                        <tr key={idx}>
                          <td>{line.item}</td>
                          <td>${line.amount?.toLocaleString?.() ?? line.amount}</td>
                          <td>{line.rev_rule}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                )}
              </div>
            )
          }

          if (artifact.type === 'config_form') {
            const c = artifact.content || {}
            return (
              <div key={artifact.id} className="scenario-artifact-card scenario-artifact-config">
                <h4>{artifact.title}</h4>
                <dl>
                  {Object.entries(c).map(([key, value]) => {
                    const isMissing = value === null || value === undefined || value === ''
                    return (
                      <div key={key} className="scenario-artifact-row">
                        <dt>{key}</dt>
                        <dd className={isMissing ? 'scenario-artifact-missing' : ''}>
                          {isMissing ? 'Not configured' : String(value)}
                        </dd>
                      </div>
                    )
                  })}
                </dl>
              </div>
            )
          }

          if (artifact.type === 'waterfall_table') {
            const rows = artifact.content || []
            return (
              <div key={artifact.id} className="scenario-artifact-card scenario-artifact-waterfall">
                <h4>{artifact.title}</h4>
                <table className="scenario-artifact-table scenario-artifact-table-mono">
                  <thead>
                    <tr>
                      <th>Period</th>
                      <th>Amount</th>
                    </tr>
                  </thead>
                  <tbody>
                    {rows.slice(0, 12).map((row, idx) => (
                      <tr key={idx}>
                        <td>{row.period}</td>
                        <td>${row.amount?.toLocaleString?.() ?? row.amount}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )
          }

          return null
        })}
      </div>
    )
  }

  return (
    <div className="scenario-runner">
      <div className="scenario-runner-shell">
        <header className="scenario-runner-header">
          <div className="scenario-runner-header-main">
            <h3>{isRevenueScenario ? 'Campfire ERP Onboarding' : template.title}</h3>
            <p className="scenario-runner-sub">
              {isRevenueScenario
                ? 'Learn revenue recognition by debugging real ERP issues.'
                : template.description}
            </p>
            <p className="scenario-runner-meta">
              Difficulty: <strong>{template.difficulty}</strong> ·{' '}
              <strong>{template.estimated_minutes} min</strong> · Status:{' '}
              <strong>{state.status}</strong>
            </p>
          </div>
          <div className="scenario-runner-header-right">
            <div className="scenario-status-pill">
              <span className="scenario-status-dot" />
              <span className="scenario-status-text">Backend: healthy · DB: disconnected</span>
            </div>
            <div className="scenario-metrics">
              <div>
                <span className="scenario-metric-label">Simulated hours</span>
                <span className="scenario-metric-value">
                  {state.metrics.simulated_hours.toFixed(1)}
                </span>
              </div>
              <div>
                <span className="scenario-metric-label">Revenue error %</span>
                <span className="scenario-metric-value">
                  {state.metrics.revenue_error_pct.toFixed(1)}%
                </span>
              </div>
              <div>
                <span className="scenario-metric-label">Open recon issues</span>
                <span className="scenario-metric-value">{state.metrics.open_recon_issues}</span>
              </div>
              <div>
                <span className="scenario-metric-label">Audit risk</span>
                <span className="scenario-metric-value">
                  {state.metrics.audit_risk_score}/100
                </span>
              </div>
            </div>
          </div>
        </header>

        <div className="scenario-columns">
          <div className="scenario-column-left">
            <section className="scenario-step">
              <h4 className="scenario-step-title">{currentStep.title}</h4>
              <p className="scenario-step-desc">{currentStep.description}</p>
              <div className="scenario-choices">
                {currentStep.choices?.map((choice) => (
                  <button
                    key={choice.id}
                    type="button"
                    className="scenario-choice-btn"
                    onClick={() => onDecision(choice.id)}
                    disabled={loading || state.status === 'COMPLETE'}
                  >
                    <span className="scenario-choice-label">{choice.label}</span>
                    <span className="scenario-choice-desc">{choice.description}</span>
                  </button>
                ))}
              </div>
            </section>

            <section className="scenario-company">
              <h4>Company snapshot</h4>
              <p className="scenario-company-name">
                {company.name || 'Synthetic Company'} · {company.business_model}{' '}
                · ARR ${company.arr?.toLocaleString?.() ?? company.arr}
              </p>
              <p className="scenario-company-meta">
                Entities: {(company.entities || []).map((e) => e.code).join(', ') || '—'} · Tools:{' '}
                {(company.tools || []).join(', ') || '—'}
              </p>
            </section>

            <section className="scenario-datasets">
              {renderTable('Invoices', datasets.invoices, [
                { key: 'invoice_id', label: 'Invoice' },
                { key: 'customer_name', label: 'Customer' },
                { key: 'amount', label: 'Amount' },
                { key: 'status', label: 'Status' },
              ])}
              {renderTable('Integration events', datasets.integration_events, [
                { key: 'event_id', label: 'Event' },
                { key: 'source_system', label: 'Source' },
                { key: 'event_type', label: 'Type' },
                { key: 'status', label: 'Status' },
              ])}
              {renderTable('Failed webhooks', datasets.failed_webhooks, [
                { key: 'id', label: 'ID' },
                { key: 'provider', label: 'Provider' },
                { key: 'status_code', label: 'Status' },
                { key: 'error_summary', label: 'Error' },
              ])}
              {renderTable('Journal entries', datasets.journal_entries, [
                { key: 'entry_id', label: 'Entry' },
                { key: 'date', label: 'Date' },
                { key: 'description', label: 'Description' },
                { key: 'amount', label: 'Amount' },
              ])}
            </section>
          </div>

          <div className="scenario-column-right">
            {isRevenueScenario && currentArtifacts.length > 0 && (
              <section className="scenario-workspace">
                {renderArtifacts(currentArtifacts)}
              </section>
            )}
          </div>
        </div>
      </div>

      <aside className="scenario-coach">
        <h4>AI Coach</h4>
        <p className="scenario-coach-sub">
          Ask how to think about this step, tradeoffs, or what a senior teammate might do.
        </p>
        <div className="scenario-coach-messages">
          {coachMessages.length === 0 && (
            <p className="scenario-coach-empty">
              No questions yet. Ask something like “How would you approach this anomaly?”
            </p>
          )}
          {coachMessages.map((m, idx) => (
            <div
              key={idx}
              className={`scenario-coach-message scenario-coach-message-${m.type}`}
            >
              <span>{m.text}</span>
            </div>
          ))}
        </div>
        <form className="scenario-coach-form" onSubmit={handleAsk}>
          <input
            type="text"
            name="question"
            className="scenario-coach-input"
            placeholder="Ask the coach a question…"
            disabled={loading}
          />
          <button type="submit" className="scenario-coach-send" disabled={loading}>
            Ask
          </button>
        </form>
      </aside>
    </div>
  )
}

export default ScenarioRunner

