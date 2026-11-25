import L from 'leaflet'
import { useEffect } from 'react'
import { Circle, MapContainer, Marker, Polyline, Popup, TileLayer, useMap, useMapEvents } from 'react-leaflet'
import { clock, TYPES, type Analysis, type Hypothesis } from './api'

export type Place = { lat: number; lon: number }

interface Props {
  analysis: Analysis | null
  selected: Hypothesis | undefined
  picking: boolean
  picked: Place | null
  onPick: (place: Place) => void
}

const ASSET_LETTER: Record<string, string> = {
  hospital: 'H',
  'fire station': 'F',
  'railway station': 'S',
  'major road': 'M',
}

const MUMBAI: L.LatLngTuple = [19.05, 72.86]

export function SignalMap({ analysis, selected, picking, picked, onPick }: Props) {
  return (
    <MapContainer center={MUMBAI} zoom={12} className={picking ? 'map picking' : 'map'}>
      <TileLayer
        attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
        url="https://tile.openstreetmap.org/{z}/{x}/{y}.png"
      />
      <Camera analysis={analysis} selected={selected} />
      {picking && <PickLocation onPick={onPick} />}
      {picked && <Marker position={[picked.lat, picked.lon]} icon={pin('picked', '+')} />}

      {analysis?.hypotheses.map((h) => (
        <Circle
          key={h.id}
          center={[h.lat, h.lon]}
          radius={analysis.radius_km * 1000}
          interactive={false}
          pathOptions={{
            color: '#38bdf8',
            dashArray: '6 6',
            weight: h === selected ? 2 : 1,
            opacity: selected && h !== selected ? 0.25 : 1,
            fillOpacity: h === selected ? 0.18 : 0.06,
          }}
        />
      ))}
      {selected &&
        analysis?.signals
          .filter((s) => s.hypothesis_id === selected.id)
          .map((s) => (
            <Polyline
              key={s.id}
              interactive={false}
              positions={[[s.lat, s.lon], [selected.lat, selected.lon]]}
              pathOptions={{ color: '#34d399', weight: 1.5, dashArray: '3 5' }}
            />
          ))}
      {selected?.assets.map((a) => (
        <Marker key={a.kind} position={[a.lat, a.lon]} icon={pin('asset', ASSET_LETTER[a.kind] ?? '?')} alt={`${a.kind}: ${a.name}`}>
          <Popup>
            <strong>{a.name}</strong>
            <br />
            {a.kind}, {a.distance_m} m from the event anchor
          </Popup>
        </Marker>
      ))}
      {analysis?.signals.map((s) => {
        const { label, letter, unit } = TYPES[s.type]
        const excluded = s.hypothesis_id === null
        const faded = selected && s.hypothesis_id !== selected.id
        const state = `${s.type} ${excluded ? 'excluded' : ''} ${faded ? 'faded' : ''}`
        return (
          <Marker
            key={s.id}
            position={[s.lat, s.lon]}
            icon={pin(state, letter)}
            alt={`${label}: ${s.description || s.source}`}
          >
            <Popup>
              <strong>{label}</strong>: {s.value} {unit}
              <br />
              {s.description && <>{s.description}<br /></>}
              {s.source}, {clock(s.observed_at)}
              <br />
              <em>{excluded ? 'Excluded' : 'Aligned'}: {s.reason}</em>
            </Popup>
          </Marker>
        )
      })}
    </MapContainer>
  )
}

function pin(state: string, letter: string) {
  return L.divIcon({ className: '', html: `<span class="pin ${state}">${letter}</span>`, iconSize: [26, 26] })
}

function Camera({ analysis, selected }: Pick<Props, 'analysis' | 'selected'>) {
  const map = useMap()
  // Keyed on content, so the 10-second refresh does not undo the operator's own panning
  const ids = analysis?.signals.map((s) => s.id).join() ?? ''
  const { lat, lon } = selected ?? {}
  useEffect(() => {
    if (lat !== undefined && lon !== undefined) {
      map.flyTo([lat, lon], 15, { duration: 0.8 })
    } else if (ids) {
      const points = analysis!.signals.map((s): L.LatLngTuple => [s.lat, s.lon])
      map.fitBounds(L.latLngBounds(points), { padding: [40, 40], maxZoom: 15 })
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps -- `ids` stands in for `analysis`
  }, [map, ids, lat, lon])
  return null
}

function PickLocation({ onPick }: Pick<Props, 'onPick'>) {
  useMapEvents({ click: ({ latlng }) => onPick({ lat: latlng.lat, lon: latlng.wrap().lng }) })
  return null
}
