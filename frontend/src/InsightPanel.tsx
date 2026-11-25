import { clock, percent, type AlertStatus, type Hypothesis } from './api'

interface Props {
  hypotheses: Hypothesis[] | undefined
  selectedId: string | null
  busy: boolean
  onSelect: (id: string | null) => void
  onDecide: (hypothesis: Hypothesis, status: AlertStatus) => void
}

const STATUS_LABEL: Record<AlertStatus, string> = {
  new: 'New alert',
  acknowledged: 'Acknowledged',
  resolved: 'Resolved',
}

export function InsightPanel({ hypotheses, selectedId, busy, onSelect, onDecide }: Props) {
  return (
    <section className="insights" aria-label="Incident hypotheses">
      <h2>CivicPulse insight</h2>
      {hypotheses?.length === 0 && (
        <p className="empty">
          No incident hypothesis. At least two different signal types must line up in space and time.
        </p>
      )}
      {hypotheses?.map((h, index) => {
        const open = h.id === selectedId
        return (
          <article key={h.id} className={open ? 'card open' : 'card'}>
            <button className="card-head" aria-expanded={open} onClick={() => onSelect(open ? null : h.id)}>
              <span className={`status ${h.status}`}>{STATUS_LABEL[h.status]}</span>
              <span className="rank">
                #{index + 1} <b className={`priority ${h.priority.level}`}>{h.priority.level} priority</b>
              </span>
              <span className="title">{h.title}</span>
              <span className="score">{percent(h.score)}</span>
              <span className="meta">
                {h.signal_ids.length} signals · {h.aligned_pairs} aligned {h.aligned_pairs === 1 ? 'pair' : 'pairs'} · {clock(h.started_at)}–
                {clock(h.ended_at)}
              </span>
            </button>
            {h.rain_anomaly && <p className="fresh">Rainfall is {h.rain_anomaly} for this month</p>}
            {h.new_signals > 0 && (
              <p className="fresh">
                +{h.new_signals} new since this alert was {h.status === 'new' ? 'reopened' : h.status}
              </p>
            )}
            {open && (
              <div className="card-body">
                <h3>Why this hypothesis</h3>
                <ul className="evidence">
                  {h.evidence.map((e) => (
                    <li key={e.factor} className={e.points ? '' : 'missing'}>
                      <span>{e.factor}</span>
                      <b>+{e.points.toFixed(2)}</b>
                      <i style={{ '--fill': e.points / e.weight } as React.CSSProperties} />
                      <small>{e.detail}</small>
                    </li>
                  ))}
                </ul>
                <p className="note">
                  Engineering score out of a maximum of 95%. It is not a probability or a machine-learning output.
                </p>
                <h3>Why {h.priority.level} priority ({h.priority.value.toFixed(2)})</h3>
                <ul className="reasons">
                  {h.priority.reasons.map((r) => <li key={r}>{r}</li>)}
                </ul>
                <p className="note">
                  Priority adds context to the score: OpenStreetMap infrastructure within 500 m, and rain compared
                  with gridded hourly history from Open-Meteo. It does not change the score.
                </p>
                <div className="actions">
                  {h.status !== 'acknowledged' && h.status !== 'resolved' && (
                    <button disabled={busy} onClick={() => onDecide(h, 'acknowledged')}>Acknowledge</button>
                  )}
                  {h.status !== 'resolved' ? (
                    <button disabled={busy} onClick={() => onDecide(h, 'resolved')}>Resolve</button>
                  ) : (
                    <button disabled={busy} onClick={() => onDecide(h, 'new')}>Reopen</button>
                  )}
                </div>
              </div>
            )}
          </article>
        )
      })}
    </section>
  )
}
