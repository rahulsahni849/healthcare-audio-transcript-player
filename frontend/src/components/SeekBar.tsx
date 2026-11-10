import { useRef, useState } from 'react'
import type { PartSummary } from '../types'
import { fmtTime } from '../utils/timeline'

interface SeekBarProps {
  parts: PartSummary[]
  duration: number
  globalTime: number
  bufferedEnd: number
  activePart: number
  onSeek: (t: number) => void
}

export function SeekBar({ parts, duration, globalTime, bufferedEnd, activePart, onSeek }: SeekBarProps) {
  const trackRef = useRef<HTMLDivElement>(null)
  const draggingRef = useRef(false)
  const [hover, setHover] = useState<{ x: number; t: number } | null>(null)

  const timeFromEvent = (clientX: number): number => {
    const rect = trackRef.current!.getBoundingClientRect()
    const frac = Math.min(Math.max((clientX - rect.left) / rect.width, 0), 1)
    return frac * duration
  }

  const handlePointerDown = (e: React.PointerEvent<HTMLDivElement>) => {
    e.currentTarget.setPointerCapture(e.pointerId)
    draggingRef.current = true
    onSeek(timeFromEvent(e.clientX))
  }

  const handlePointerMove = (e: React.PointerEvent<HTMLDivElement>) => {
    const rect = trackRef.current!.getBoundingClientRect()
    setHover({ x: e.clientX - rect.left, t: timeFromEvent(e.clientX) })
    if (draggingRef.current) onSeek(timeFromEvent(e.clientX))
  }

  const handlePointerUp = (e: React.PointerEvent<HTMLDivElement>) => {
    draggingRef.current = false
    e.currentTarget.releasePointerCapture(e.pointerId)
  }

  return (
    <div className="seekbar">
      <div
        ref={trackRef}
        className="seek-track"
        role="slider"
        aria-label="Audio position"
        aria-valuemin={0}
        aria-valuemax={Math.round(duration)}
        aria-valuenow={Math.round(globalTime)}
        tabIndex={0}
        onPointerDown={handlePointerDown}
        onPointerMove={handlePointerMove}
        onPointerUp={handlePointerUp}
        onPointerLeave={() => setHover(null)}
      >
        {parts.map((p) => {
          const widthPct = (p.duration / duration) * 100
          const played = Math.min(Math.max((globalTime - p.start) / p.duration, 0), 1)
          const buffered =
            p.index === activePart
              ? Math.min(Math.max((bufferedEnd - p.start) / p.duration, 0), 1)
              : 0
          return (
            <div key={p.index} className="seek-segment" style={{ width: `${widthPct}%` }}>
              <div className="seek-buffer" style={{ width: `${buffered * 100}%` }} />
              <div className="seek-played" style={{ width: `${played * 100}%` }} />
            </div>
          )
        })}
        <div
          className="seek-cursor"
          style={{ left: `${duration > 0 ? (globalTime / duration) * 100 : 0}%` }}
        />
      </div>
      {hover && (
        <div className="seek-tooltip" style={{ left: hover.x }}>
          <span className="seek-tooltip-part">Part {partIndexAtTime(parts, hover.t)}</span>
          <span>{fmtTime(hover.t)}</span>
        </div>
      )}
    </div>
  )
}

function partIndexAtTime(parts: PartSummary[], t: number): number {
  for (const p of parts) {
    if (t < p.end) return p.index
  }
  return parts[parts.length - 1].index
}
