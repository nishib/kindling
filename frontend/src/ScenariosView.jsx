import { useEffect, useState } from 'react'
import axios from 'axios'
import ScenarioRunner from './ScenarioRunner.jsx'
import ScenarioDebrief from './ScenarioDebrief.jsx'
import MonthEndGame from './MonthEndGame.jsx'

const API_URL = import.meta.env.VITE_API_URL || ''

const MONTH_END_SCENARIO = {
  id: 'month-end-close',
  title: 'Month-End Close: AI Mentor',
  description:
    'Play the Controller closing the books for a month-end period with guidance from an AI Mentor.',
  difficulty: 'Intermediate',
  estimated_minutes: 15,
}

function ScenariosView() {
  const [scenarios, setScenarios] = useState([])
  const [loadingScenarios, setLoadingScenarios] = useState(false)
  const [errorScenarios, setErrorScenarios] = useState(null)
  const [activeScenarioId, setActiveScenarioId] = useState(null)

  const [runId, setRunId] = useState(null)
  const [runState, setRunState] = useState(null)
  const [loadingRun, setLoadingRun] = useState(false)
  const [debrief, setDebrief] = useState(null)
  const [coachMessages, setCoachMessages] = useState([])
  const [runError, setRunError] = useState(null)

  useEffect(() => {
    const loadScenarios = async () => {
      setLoadingScenarios(true)
      setErrorScenarios(null)
      try {
        const base = API_URL || ''
        const res = await axios.get(`${base}/api/scenarios`)
        const data = Array.isArray(res.data) ? res.data : []
        setScenarios(data)
        if (!activeScenarioId) {
          // Default to the local Month-End Close game
          setActiveScenarioId(MONTH_END_SCENARIO.id)
        }
      } catch (err) {
        setErrorScenarios('Could not load scenarios. Is the backend running?')
      } finally {
        setLoadingScenarios(false)
      }
    }
    loadScenarios()
  }, [activeScenarioId])

  const isMonthEndScenario = activeScenarioId === MONTH_END_SCENARIO.id
  const activeScenario = isMonthEndScenario
    ? MONTH_END_SCENARIO
    : scenarios.find((s) => s.id === activeScenarioId) || null

  const startScenario = async (scenarioId) => {
    // Local Month-End Close game does not call the backend
    if (scenarioId === MONTH_END_SCENARIO.id) {
      setRunId(null)
      setRunState(null)
      setDebrief(null)
      setCoachMessages([])
      setRunError(null)
      return
    }
    setLoadingRun(true)
    setRunError(null)
    setDebrief(null)
    setCoachMessages([])
    try {
      const base = API_URL || ''
      const res = await axios.post(`${base}/api/scenarios/${scenarioId}/start`)
      const run = res.data
      setRunId(run.run_id)
      setRunState(run)
    } catch (err) {
      const msg =
        err?.response?.data?.detail ||
        err?.message ||
        'Could not start this scenario. Please check that the backend is running.'
      setRunError(msg)
      setRunId(null)
      setRunState(null)
    } finally {
      setLoadingRun(false)
    }
  }

  const handleDecision = async (choiceId) => {
    if (!runId || !choiceId) return
    setLoadingRun(true)
    try {
      const base = API_URL || ''
      const res = await axios.post(`${base}/api/scenarios/${runId}/decision`, { choice_id: choiceId })
      const data = res.data
      setRunState(data.run)
      if (data.coach_message) {
        setCoachMessages((prev) => [...prev, { type: 'coach', text: data.coach_message }])
      }
      if (data.run.state.status === 'COMPLETE') {
        const debriefRes = await axios.get(`${base}/api/scenarios/${runId}/debrief`)
        setDebrief(debriefRes.data)
      }
    } catch (err) {
      // In V1 just reset and let user restart
      setRunState(null)
      setDebrief(null)
    } finally {
      setLoadingRun(false)
    }
  }

  const handleAskCoach = async (question) => {
    if (!runId || !question) return
    setCoachMessages((prev) => [...prev, { type: 'user', text: question }])
    try {
      const base = API_URL || ''
      const res = await axios.post(`${base}/api/scenarios/${runId}/coach`, { question })
      setCoachMessages((prev) => [...prev, { type: 'coach', text: res.data.answer }])
    } catch (err) {
      setCoachMessages((prev) => [...prev, { type: 'coach', text: 'Coach is unavailable right now.' }])
    }
  }

  const isMonthEndActive = isMonthEndScenario && activeScenarioId === MONTH_END_SCENARIO.id

  return (
    <div className={`scenarios-root ${isMonthEndActive ? 'fullscreen' : ''}`}>
      {!isMonthEndActive && (
        <div className="scenarios-rail" role="tablist" aria-orientation="vertical">
          {loadingScenarios && <p className="scenarios-hint">Loading scenarios…</p>}
          {errorScenarios && <p className="scenarios-error">{errorScenarios}</p>}
          {!loadingScenarios && !errorScenarios && scenarios.length === 0 && (
            <p className="scenarios-hint">No scenarios available yet from the backend.</p>
          )}
          <button
            key={MONTH_END_SCENARIO.id}
            type="button"
            role="tab"
            aria-selected={activeScenarioId === MONTH_END_SCENARIO.id}
            className={`scenarios-rail-item ${
              activeScenarioId === MONTH_END_SCENARIO.id ? 'active' : ''
            }`}
            onClick={() => {
              setActiveScenarioId(MONTH_END_SCENARIO.id)
              setRunId(null)
              setRunState(null)
              setDebrief(null)
              setCoachMessages([])
            }}
          >
            <span className="scenarios-rail-title">{MONTH_END_SCENARIO.title}</span>
            <span className="scenarios-rail-meta">
              {MONTH_END_SCENARIO.difficulty} · {MONTH_END_SCENARIO.estimated_minutes} min
            </span>
          </button>
          {scenarios.map((scenario) => (
            <button
              key={scenario.id}
              type="button"
              role="tab"
              aria-selected={activeScenarioId === scenario.id}
              className={`scenarios-rail-item ${activeScenarioId === scenario.id ? 'active' : ''}`}
              onClick={() => {
                setActiveScenarioId(scenario.id)
                setRunId(null)
                setRunState(null)
                setDebrief(null)
                setCoachMessages([])
              }}
            >
              <span className="scenarios-rail-title">{scenario.title}</span>
              <span className="scenarios-rail-meta">
                {scenario.difficulty} · {scenario.estimated_minutes} min
              </span>
            </button>
          ))}
        </div>
      )}

      <div className="scenarios-panel">
        {!activeScenario && (
          <div className="scenarios-empty">
            <h3>Select a scenario</h3>
            <p>Choose a simulated ERP scenario from the left to get started.</p>
          </div>
        )}

        {isMonthEndScenario && (
          <MonthEndGame />
        )}

        {!isMonthEndScenario && activeScenario && !runState && !debrief && (
          <div className="scenarios-intro">
            <h3>{activeScenario.title}</h3>
            <p className="scenarios-intro-desc">{activeScenario.description}</p>
            <p className="scenarios-intro-meta">
              Difficulty: <strong>{activeScenario.difficulty}</strong> · Estimated{' '}
              <strong>{activeScenario.estimated_minutes} minutes</strong>
            </p>
            {runError && <p className="scenarios-error">{runError}</p>}
            <button
              type="button"
              className="scenarios-start-btn"
              onClick={() => startScenario(activeScenario.id)}
              disabled={loadingRun}
            >
              {loadingRun ? 'Starting…' : 'Start scenario'}
            </button>
          </div>
        )}

        {!isMonthEndScenario && runState && (
          <ScenarioRunner
            run={runState}
            loading={loadingRun}
            onDecision={handleDecision}
            onAskCoach={handleAskCoach}
            coachMessages={coachMessages}
          />
        )}

        {!isMonthEndScenario && debrief && (
          <ScenarioDebrief
            debrief={debrief}
            onRestart={() => {
              if (activeScenario) {
                startScenario(activeScenario.id)
              }
            }}
          />
        )}
      </div>
    </div>
  )
}

export default ScenariosView

