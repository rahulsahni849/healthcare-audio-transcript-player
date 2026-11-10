import { useEffect } from 'react'
import { usePlayer } from '../hooks/usePlayer'
import { useTranscript } from '../hooks/useTranscript'
import type { MergedTranscript, RecordingDetail } from '../types'
import { Controls } from './Controls'
import { DownloadButton } from './DownloadButton'
import { SeekBar } from './SeekBar'
import { TranscriptPanel } from './TranscriptPanel'

interface PlayerProps {
  recording: RecordingDetail
  transcript: MergedTranscript | null
}

export function Player({ recording, transcript }: PlayerProps) {
  const player = usePlayer(recording)
  const activeWordIndex = useTranscript(transcript?.words ?? [], player.globalTime)

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      const target = e.target as HTMLElement
      if (target.tagName === 'INPUT' || target.tagName === 'TEXTAREA' || target.tagName === 'SELECT') return
      switch (e.code) {
        case 'Space':
          e.preventDefault()
          player.toggle()
          break
        case 'ArrowRight':
          e.preventDefault()
          player.seekBy(5)
          break
        case 'ArrowLeft':
          e.preventDefault()
          player.seekBy(-5)
          break
        case 'KeyL':
          player.skipPart(1)
          break
        case 'KeyJ':
          player.skipPart(-1)
          break
      }
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [player])

  return (
    <div className="player">
      <header className="player-header">
        <div>
          <h1>{recording.title}</h1>
          <span className="part-count">
            {recording.parts.length} parts · {Math.round(recording.totalDuration / 60)} min
          </span>
        </div>
        <DownloadButton recordingId={recording.id} />
      </header>

      {transcript ? (
        <TranscriptPanel
          words={transcript.words}
          activeIndex={activeWordIndex}
          onSeekWord={player.seek}
        />
      ) : (
        <div className="transcript-loading">Loading transcript…</div>
      )}

      <div className="player-bar">
        <SeekBar
          parts={recording.parts}
          duration={player.duration}
          globalTime={player.globalTime}
          bufferedEnd={player.bufferedEnd}
          activePart={player.activePart}
          onSeek={player.seek}
        />
        <Controls
          playing={player.playing}
          globalTime={player.globalTime}
          duration={player.duration}
          volume={player.volume}
          playbackRate={player.playbackRate}
          muted={player.muted}
          onToggle={player.toggle}
          onSeekBy={player.seekBy}
          onSkipPart={player.skipPart}
          onVolume={player.setVolume}
          onPlaybackRate={player.setPlaybackRate}
          onToggleMute={player.toggleMute}
        />
      </div>
    </div>
  )
}
