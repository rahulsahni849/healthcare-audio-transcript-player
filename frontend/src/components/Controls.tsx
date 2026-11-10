import { fmtTime } from '../utils/timeline'

const SPEEDS = [0.75, 1, 1.25, 1.5, 2]

interface ControlsProps {
  playing: boolean
  globalTime: number
  duration: number
  volume: number
  playbackRate: number
  muted: boolean
  onToggle: () => void
  onSeekBy: (delta: number) => void
  onSkipPart: (delta: number) => void
  onVolume: (v: number) => void
  onPlaybackRate: (rate: number) => void
  onToggleMute: () => void
}

export function Controls({
  playing,
  globalTime,
  duration,
  volume,
  playbackRate,
  muted,
  onToggle,
  onSeekBy,
  onSkipPart,
  onVolume,
  onPlaybackRate,
  onToggleMute,
}: ControlsProps) {
  return (
    <div className="controls">
      <button className="ctrl-btn" onClick={() => onSkipPart(-1)} aria-label="Previous part" title="Previous part (J)">
        <svg viewBox="0 0 24 24" width="18" height="18" fill="currentColor">
          <path d="M6 5h2v14H6zM20 5v14L9 12z" />
        </svg>
      </button>
      <button className="ctrl-btn" onClick={() => onSeekBy(-5)} aria-label="Back 5 seconds" title="Back 5s (←)">
        <svg viewBox="0 0 24 24" width="18" height="18" fill="currentColor">
          <path d="M12 5V1L7 6l5 5V7a6 6 0 1 1-6 6H4a8 8 0 1 0 8-8z" />
          <text x="12" y="16.5" fontSize="7" textAnchor="middle" fill="currentColor" stroke="none">5</text>
        </svg>
      </button>
      <button className="ctrl-btn play-btn" onClick={onToggle} aria-label={playing ? 'Pause' : 'Play'} title="Play/Pause (Space)">
        {playing ? (
          <svg viewBox="0 0 24 24" width="22" height="22" fill="currentColor">
            <path d="M7 5h4v14H7zM13 5h4v14h-4z" />
          </svg>
        ) : (
          <svg viewBox="0 0 24 24" width="22" height="22" fill="currentColor">
            <path d="M8 5v14l11-7z" />
          </svg>
        )}
      </button>
      <button className="ctrl-btn" onClick={() => onSeekBy(5)} aria-label="Forward 5 seconds" title="Forward 5s (→)">
        <svg viewBox="0 0 24 24" width="18" height="18" fill="currentColor">
          <path d="M12 5V1l5 5-5 5V7a6 6 0 1 0 6 6h2a8 8 0 1 1-8-8z" />
          <text x="12" y="16.5" fontSize="7" textAnchor="middle" fill="currentColor" stroke="none">5</text>
        </svg>
      </button>
      <button className="ctrl-btn" onClick={() => onSkipPart(1)} aria-label="Next part" title="Next part (L)">
        <svg viewBox="0 0 24 24" width="18" height="18" fill="currentColor">
          <path d="M16 5h2v14h-2zM4 5l11 7L4 19z" />
        </svg>
      </button>

      <span className="time-display">
        {fmtTime(globalTime)} / {fmtTime(duration)}
      </span>

      <div className="controls-right">
        <select
          className="speed-select"
          value={playbackRate}
          onChange={(e) => onPlaybackRate(Number(e.target.value))}
          aria-label="Playback speed"
          title="Playback speed"
        >
          {SPEEDS.map((s) => (
            <option key={s} value={s}>
              {s}×
            </option>
          ))}
        </select>
        <button className="ctrl-btn" onClick={onToggleMute} aria-label={muted ? 'Unmute' : 'Mute'} title={muted ? 'Unmute' : 'Mute'}>
          {muted ? (
            <svg viewBox="0 0 24 24" width="16" height="16" fill="currentColor">
              <path d="M16.5 12A4.5 4.5 0 0 0 14 8v2.2l2.5 2.5v-.7zM19 12c0 .9-.2 1.8-.5 2.6l1.5 1.5A9.4 9.4 0 0 0 21 12c0-4.1-2.9-7.6-6.7-8.6v2.1c2.9.9 4.7 3.5 4.7 6.5zM4.3 3L3 4.3 7.7 9H3v6h4l5 5v-6.7l4.3 4.3c-.7.5-1.4.9-2.3 1.2v2.1c1.4-.3 2.6-1 3.7-1.8l2 2L21 19.7 4.3 3zM12 4L9.9 6.1 12 8.2V4z" />
            </svg>
          ) : (
            <svg viewBox="0 0 24 24" width="16" height="16" fill="currentColor">
              <path d="M3 9v6h4l5 5V4L7 9H3zm13.5 3a4.5 4.5 0 0 0-2.5-4v8a4.5 4.5 0 0 0 2.5-4z" />
            </svg>
          )}
        </button>
        <input
          type="range"
          min={0}
          max={1}
          step={0.05}
          value={muted ? 0 : volume}
          onChange={(e) => onVolume(Number(e.target.value))}
          aria-label="Volume"
        />
      </div>
    </div>
  )
}
