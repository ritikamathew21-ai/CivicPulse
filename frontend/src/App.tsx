import { useEffect, useState } from 'react'
import { api, clock, TYPES, type Analysis, type Dataset } from './api'
import { InsightPanel } from './InsightPanel'
import { ReportForm } from './ReportForm'
import { SignalMap, type Place } from './SignalMap'

const REFRESH_MS = 10_000

export default function App() {
  const [dataset, setDataset] = useState<Dataset>('demo')
  const [radiusKm, setRadiusKm] = useState(1)
  const [windowMin, setWindowMin] = useState(15)
  const [analysis, setAnalysis] = useState<Analysis | null>(null)
  const [selectedId, setSelectedId] = useState<string | null>(null)
  const [reporting, setReporting] = useState(false)
  const [place, setPlace] = useState<Place | null>(null)
  const [busy, setBusy] = useState(false)
  const [actionError, setActionError] = useState('')
  const [loadError, setLoadError] = useState('')
  const [version, setVersion] = useState(0)

  useEffect(() => {
    const controller = new AbortController()
    const load = () =>
      api
        .analysis(dataset, radiusKm, windowMin, controller.signal)
        .then((data) => {
          setAnalysis(data)
          setLoadError('')
        })
        .catch((e: Error) => {
          if (!controller.signal.aborted) setLoadError(e.message)
        })
    load()
    const timer = setInterval(load, REFRESH_MS)
    return () => {
      controller.abort()
      clearInterval(timer)
    }
  }, [dataset, radiusKm, windowMin, version])

  async function run(action: () => Promise<unknown>) {
    setBusy(true)
    setActionError('')
    try {
      await action()
      setVersion((v) => v + 1)
      return true
    } catch (e) {
      setActionError((e as Error).message)
      return false
    } finally {
      setBusy(false)
    }
  }

  function closeReport() {
    setReporting(false)
    setPlace(null)
  }

  function switchDataset(next: Dataset) {
    setDataset(next)
    setAnalysis(null)
    setSelectedId(null)
    closeReport()
  }

  const selected = analysis?.hypotheses.find((h) => h.id === selectedId)
  const stats = analysis?.stats
  const error = actionError || loadError

  return (
    <div className="app">
      <header>
        <div>
          <h1>CivicPulse</h1>
          <p>Cross-signal urban incident intelligence · Mumbai</p>
        </div>
        <div className="toggle" role="group" aria-label="Data source">
          <button aria-pressed={dataset === 'demo'} onClick={() => switchDataset('demo')}>Demo</button>
          <button aria-pressed={dataset === 'live'} onClick={() => switchDataset('live')}>Live</button>
        </div>
        <div className="actions">
          {dataset === 'demo' ? (
            <>
              <button disabled={busy} onClick={() => run(() => api.loadDemo('single'))}>Load one event</button>
              <button disabled={busy} onClick={() => run(() => api.loadDemo('multi'))}>Load several events</button>
            </>
          ) : (
            <button disabled={busy} onClick={() => run(api.refreshRainfall)}>Fetch rainfall now</button>
          )}
          <button className="primary" onClick={() => setReporting(true)}>Report signal</button>
        </div>
      </header>

      <p className="banner">
        {dataset === 'demo'
          ? 'Demo: simulated signals, real reasoning. Loading a scenario replaces all demo signals.'
          : 'Live: Open-Meteo rainfall plus reported signals from the last 24 hours. No live traffic feed is connected.'}
      </p>
      {error && <p className="error" role="alert">{error}</p>}

      <section className="stats" aria-label="Current result">
        <Stat label="signals received" value={stats?.received} />
        <Stat label="relevant / aligned" value={stats?.aligned} tone="good" />
        <Stat label="unrelated, excluded" value={stats?.excluded} tone="muted" />
        <Stat label="aligned signal pairs" value={stats?.aligned_pairs} />
      </section>

      <main>
        <div className="map-wrap">
          <SignalMap analysis={analysis} selected={selected} picking={reporting} picked={place} onPick={setPlace} />
          <div className="controls">
            <label>
              Spatial radius <b>{radiusKm} km</b>
              <input
                type="range" min="0.2" max="5" step="0.1" value={radiusKm}
                onChange={(e) => setRadiusKm(Number(e.target.value))}
              />
            </label>
            <label>
              Time window <b>{windowMin} min</b>
              <input
                type="range" min="5" max="120" step="5" value={windowMin}
                onChange={(e) => setWindowMin(Number(e.target.value))}
              />
            </label>
            <ul className="legend">
              {Object.entries(TYPES).map(([type, t]) => (
                <li key={type}><span className={`pin ${type}`}>{t.letter}</span>{t.label}</li>
              ))}
              <li><span className="pin excluded">–</span>Excluded</li>
              {selected && selected.assets.length > 0 && (
                <li><span className="pin asset">+</span>H hospital, F fire, S station, M major road</li>
              )}
            </ul>
          </div>
        </div>
        <aside>
          {reporting && (
            <ReportForm
              place={place}
              busy={busy}
              onCancel={closeReport}
              onSubmit={async (signal) => {
                if (await run(() => api.report({ ...signal, dataset }))) closeReport()
              }}
            />
          )}
          <InsightPanel
            hypotheses={analysis?.hypotheses}
            selectedId={selectedId}
            busy={busy}
            onSelect={setSelectedId}
            onDecide={(h, status) => run(() => api.decide(dataset, status, h.signal_ids))}
          />
        </aside>
      </main>

      <section className="table-wrap">
        <h2>Every signal, and why it was used or not</h2>
        <table>
          <thead>
            <tr><th>Time</th><th>Type</th><th>Value</th><th>What and where from</th><th>Result</th></tr>
          </thead>
          <tbody>
            {analysis?.signals.map((s) => (
              <tr key={s.id} className={selected && s.hypothesis_id !== selected.id ? 'faded' : ''}>
                <td>{clock(s.observed_at)}</td>
                <td>{TYPES[s.type].label}</td>
                <td>{s.value} {s.type === 'incident' ? '/ 5' : TYPES[s.type].unit}</td>
                <td>{s.description}<small>{s.source}</small></td>
                <td>
                  <b className={s.hypothesis_id ? 'good' : 'muted'}>{s.hypothesis_id ? 'Aligned' : 'Excluded'}</b>
                  <small>{s.reason}</small>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        {analysis?.signals.length === 0 && (
          <p className="empty">
            No signals yet. {dataset === 'demo' ? 'Load a scenario to begin.' : 'Fetch rainfall or report a signal.'}
          </p>
        )}
      </section>
    </div>
  )
}

function Stat({ label, value, tone = '' }: { label: string; value?: number; tone?: string }) {
  return (
    <div className="stat">
      <b className={tone}>{value ?? '–'}</b>
      <span>{label}</span>
    </div>
  )
}
