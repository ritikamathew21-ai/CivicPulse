import { useState, type FormEvent } from 'react'
import { TYPES, type NewSignal, type SignalType } from './api'
import type { Place } from './SignalMap'

interface Props {
  place: Place | null
  busy: boolean
  onSubmit: (signal: Omit<NewSignal, 'dataset'>) => void
  onCancel: () => void
}

export function ReportForm({ place, busy, onSubmit, onCancel }: Props) {
  const [type, setType] = useState<SignalType>('incident')
  const [value, setValue] = useState(String(TYPES.incident.initial))
  const [description, setDescription] = useState('')
  const spec = TYPES[type]

  function changeType(next: SignalType) {
    setType(next)
    setValue(String(TYPES[next].initial))
  }

  function submit(event: FormEvent) {
    event.preventDefault()
    if (!place) return
    onSubmit({ type, value: Number(value), description, ...place, observed_at: new Date().toISOString() })
  }

  return (
    <form className="report" onSubmit={submit}>
      <h2>Report a signal</h2>
      <label>
        Type
        <select value={type} onChange={(e) => changeType(e.target.value as SignalType)}>
          {Object.entries(TYPES).map(([key, t]) => (
            <option key={key} value={key}>{t.label}</option>
          ))}
        </select>
      </label>
      <label>
        Value, {spec.unit}
        <input
          type="number" required step="any" min={spec.min} max={spec.max}
          value={value} onChange={(e) => setValue(e.target.value)}
        />
      </label>
      <label>
        Description (optional)
        <input maxLength={300} value={description} onChange={(e) => setDescription(e.target.value)} />
      </label>
      <p className={place ? 'place' : 'place empty'}>
        {place ? `Location: ${place.lat.toFixed(4)}, ${place.lon.toFixed(4)}` : 'Click the map to set the location.'}
      </p>
      <div className="actions">
        <button className="primary" disabled={!place || busy}>Submit</button>
        <button type="button" onClick={onCancel}>Cancel</button>
      </div>
    </form>
  )
}
