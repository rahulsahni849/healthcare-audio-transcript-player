import { useEffect, useRef } from 'react'
import type { Word } from '../types'

interface TranscriptPanelProps {
  words: Word[]
  activeIndex: number
  onSeekWord: (t: number) => void
}

export function TranscriptPanel({ words, activeIndex, onSeekWord }: TranscriptPanelProps) {
  const activeRef = useRef<HTMLSpanElement>(null)

  useEffect(() => {
    activeRef.current?.scrollIntoView({ block: 'nearest', behavior: 'smooth' })
  }, [activeIndex])

  const lines: Word[][] = []
  let current: Word[] = []
  let currentPart = -1
  for (const w of words) {
    if (w.part !== currentPart) {
      if (current.length > 0) lines.push(current)
      current = []
      currentPart = w.part
    }
    current.push(w)
    if (/[.?!]$/.test(w.word)) {
      lines.push(current)
      current = []
    }
  }
  if (current.length > 0) lines.push(current)

  let wordCursor = 0
  let lastPart = -1

  return (
    <div className="transcript" aria-label="Transcript">
      {lines.map((line, li) => {
        const partLabel = line[0].part !== lastPart ? line[0].part : null
        lastPart = line[0].part
        const spans = line.map((w) => {
          const idx = wordCursor++
          const isActive = idx === activeIndex
          const isPast = idx < activeIndex
          return (
            <span
              key={idx}
              ref={isActive ? activeRef : undefined}
              className={`word${isActive ? ' active' : ''}${isPast ? ' past' : ''}`}
              onClick={() => onSeekWord(w.start + 0.01)}
            >
              {w.word}{' '}
            </span>
          )
        })
        return (
          <p key={li} className="transcript-line">
            {partLabel && <span className="part-chip">Part {partLabel}</span>}
            {spans}
          </p>
        )
      })}
    </div>
  )
}
