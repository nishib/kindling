function ScenarioDebrief({ debrief, onRestart }) {
  const { outcome_title: outcomeTitle, metrics, strengths, weaknesses, concepts_to_review: conceptsToReview, recommended_next_scenarios: recommended } = debrief

  return (
    <div className="scenario-debrief">
      <header className="scenario-debrief-header">
        <h3>{outcomeTitle}</h3>
        <div className="scenario-debrief-metrics">
          <div>
            <span className="scenario-metric-label">Simulated hours</span>
            <span className="scenario-metric-value">{metrics.simulated_hours.toFixed(1)}</span>
          </div>
          <div>
            <span className="scenario-metric-label">Revenue error %</span>
            <span className="scenario-metric-value">{metrics.revenue_error_pct.toFixed(1)}%</span>
          </div>
          <div>
            <span className="scenario-metric-label">Open recon issues</span>
            <span className="scenario-metric-value">{metrics.open_recon_issues}</span>
          </div>
          <div>
            <span className="scenario-metric-label">Audit risk</span>
            <span className="scenario-metric-value">{metrics.audit_risk_score}/100</span>
          </div>
        </div>
      </header>

      <section className="scenario-debrief-section">
        <h4>Strengths</h4>
        <ul>
          {strengths.map((s, idx) => (
            <li key={idx}>{s}</li>
          ))}
        </ul>
      </section>

      <section className="scenario-debrief-section">
        <h4>Opportunities</h4>
        <ul>
          {weaknesses.map((w, idx) => (
            <li key={idx}>{w}</li>
          ))}
        </ul>
      </section>

      <section className="scenario-debrief-section">
        <h4>Concepts to review</h4>
        <ul>
          {conceptsToReview.map((c, idx) => (
            <li key={idx}>{c}</li>
          ))}
        </ul>
      </section>

      <section className="scenario-debrief-section">
        <h4>Recommended next scenarios</h4>
        <ul>
          {recommended.map((s) => (
            <li key={s.id}>
              <span className="scenario-debrief-next-title">{s.title}</span>{' '}
              <span className="scenario-debrief-next-meta">
                {s.difficulty} · {s.estimated_minutes} min
              </span>
            </li>
          ))}
        </ul>
      </section>

      <button type="button" className="scenarios-start-btn" onClick={onRestart}>
        Run again
      </button>
    </div>
  )
}

export default ScenarioDebrief

