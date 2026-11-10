import { useEffect, useState } from 'react'
import { api } from '../api/client'
import type { MergedTranscript, RecordingDetail, RecordingSummary } from '../types'
import { Player } from './Player'

export function RecordingPicker() {
  const [recordings, setRecordings] = useState<RecordingSummary[] | null>(null)
  const [selected, setSelected] = useState<string | null>(null)
  const [detail, setDetail] = useState<RecordingDetail | null>(null)
  const [transcript, setTranscript] = useState<MergedTranscript | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    api
      .listRecordings()
      .then((list) => {
        setRecordings(list)
        if (list.length > 0) setSelected(list[0].id)
      })
      .catch((e) => setError(e.message))
  }, [])

  useEffect(() => {
    if (!selected) return
    setDetail(null)
    setTranscript(null)
    Promise.all([api.getRecording(selected), api.getTranscript(selected)])
      .then(([d, t]) => {
        setDetail(d)
        setTranscript(t)
      })
      .catch((e) => setError(e.message))
  }, [selected])

  if (error) return <div className="app-error">Error: {error}</div>
  if (!recordings || (recordings.length > 0 && (!detail || !transcript))) {
    return <div className="app-loading">Loading…</div>
  }
  if (recordings.length === 0) {
    return (
      <div className="app-error">
        No recordings found. Run <code>python scripts/generate_demo_data.py</code> first.
      </div>
    )
  }

  return (
    <div className="app">
      {recordings.length > 1 && (
        <nav className="picker">
          {recordings.map((r) => (
            <button
              key={r.id}
              className={`picker-btn${r.id === selected ? ' selected' : ''}`}
              onClick={() => setSelected(r.id)}
            >
              {r.title}
            </button>
          ))}
        </nav>
      )}
      {detail && <Player recording={detail} transcript={transcript} />}
    </div>
  )
}
