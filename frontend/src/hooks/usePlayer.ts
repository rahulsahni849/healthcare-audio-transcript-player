import { useCallback, useEffect, useRef, useState } from 'react'
import { partAudioUrl } from '../api/client'
import type { RecordingDetail } from '../types'
import { partIndexAt } from '../utils/timeline'

const PREBUFFER_THRESHOLD = 0.3

export interface PlayerController {
  playing: boolean
  globalTime: number
  activePart: number
  duration: number
  volume: number
  bufferedEnd: number
  playbackRate: number
  muted: boolean
  play: () => void
  pause: () => void
  toggle: () => void
  seek: (globalSeconds: number) => void
  seekBy: (deltaSeconds: number) => void
  skipPart: (delta: number) => void
  setVolume: (v: number) => void
  setPlaybackRate: (rate: number) => void
  toggleMute: () => void
}

export function usePlayer(recording: RecordingDetail | null): PlayerController {
  const [playing, setPlaying] = useState(false)
  const [globalTime, setGlobalTime] = useState(0)
  const [activePart, setActivePart] = useState(1)
  const [volume, setVolumeState] = useState(1)
  const [bufferedEnd, setBufferedEnd] = useState(0)
  const [playbackRate, setRateState] = useState(1)
  const [muted, setMutedState] = useState(false)

  const audioA = useRef<HTMLAudioElement | null>(null)
  const audioB = useRef<HTMLAudioElement | null>(null)
  const activeEl = useRef<HTMLAudioElement | null>(null)
  const standbyEl = useRef<HTMLAudioElement | null>(null)
  const activeIdx = useRef(0)
  const playingRef = useRef(false)
  const recordingRef = useRef<RecordingDetail | null>(recording)
  const volumeRef = useRef(1)
  const rateRef = useRef(1)
  const mutedRef = useRef(false)

  useEffect(() => {
    recordingRef.current = recording
  }, [recording])

  useEffect(() => {
    volumeRef.current = volume
  }, [volume])

  useEffect(() => {
    rateRef.current = playbackRate
  }, [playbackRate])

  useEffect(() => {
    mutedRef.current = muted
  }, [muted])

  const startPlayback = useCallback((el: HTMLAudioElement) => {
    el.volume = volumeRef.current
    el.play().catch(() => {})
  }, [])

  const preloadIntoStandby = useCallback((fromIdx: number) => {
    const rec = recordingRef.current
    const standby = standbyEl.current
    if (!rec || !standby) return
    const nextIdx = fromIdx + 1
    if (nextIdx < rec.parts.length) {
      standby.src = partAudioUrl(rec.id, nextIdx + 1)
      standby.currentTime = 0
      standby.load()
    } else {
      standby.removeAttribute('src')
    }
  }, [])

  const swapToStandby = useCallback(() => {
    const prev = activeEl.current
    const next = standbyEl.current
    if (!prev || !next || !next.src) return
    prev.pause()
    activeEl.current = next
    standbyEl.current = prev
    activeIdx.current += 1
    next.currentTime = 0
    setActivePart(activeIdx.current + 1)
    if (playingRef.current) startPlayback(next)
    preloadIntoStandby(activeIdx.current)
  }, [preloadIntoStandby, startPlayback])

  useEffect(() => {
    const a = new Audio()
    const b = new Audio()
    a.preload = 'auto'
    b.preload = 'auto'
    a.playbackRate = rateRef.current
    b.playbackRate = rateRef.current
    a.muted = mutedRef.current
    b.muted = mutedRef.current
    audioA.current = a
    audioB.current = b
    activeEl.current = a
    standbyEl.current = b
    activeIdx.current = 0
    playingRef.current = false
    setPlaying(false)
    setActivePart(1)
    setGlobalTime(0)
    setBufferedEnd(0)

    if (recording) {
      a.src = partAudioUrl(recording.id, 1)
      if (recording.parts.length > 1) b.src = partAudioUrl(recording.id, 2)
      a.load()
    }

    let raf = 0
    const tick = () => {
      const rec = recordingRef.current
      const el = activeEl.current
      if (rec && el) {
        const part = rec.parts[activeIdx.current]
        const partTime = part.start + el.currentTime
        if (el.buffered.length > 0) {
          const end = part.start + el.buffered.end(el.buffered.length - 1)
          setBufferedEnd((prev) => (Math.abs(prev - end) > 0.05 ? end : prev))
        }
        const remaining = part.end - partTime
        const standby = standbyEl.current
        if (
          playingRef.current &&
          standby &&
          standby.src &&
          remaining <= PREBUFFER_THRESHOLD &&
          standby.readyState >= 3
        ) {
          swapToStandby()
        } else if (playingRef.current) {
          setGlobalTime((prev) => (Math.abs(prev - partTime) > 0.016 ? partTime : prev))
        }
      }
      raf = requestAnimationFrame(tick)
    }
    raf = requestAnimationFrame(tick)

    const handleEnded = () => {
      const rec = recordingRef.current
      const standby = standbyEl.current
      if (!rec) return
      if (standby && standby.src && activeIdx.current + 1 < rec.parts.length) {
        swapToStandby()
      } else {
        playingRef.current = false
        setPlaying(false)
        setGlobalTime(rec.totalDuration)
      }
    }
    a.addEventListener('ended', handleEnded)
    b.addEventListener('ended', handleEnded)

    return () => {
      cancelAnimationFrame(raf)
      a.removeEventListener('ended', handleEnded)
      b.removeEventListener('ended', handleEnded)
      for (const el of [a, b]) {
        el.pause()
        el.removeAttribute('src')
        el.load()
      }
      activeEl.current = null
      standbyEl.current = null
    }
  }, [recording, swapToStandby])

  const play = useCallback(() => {
    const el = activeEl.current
    if (!el || !el.src) return
    playingRef.current = true
    setPlaying(true)
    startPlayback(el)
  }, [startPlayback])

  const pause = useCallback(() => {
    playingRef.current = false
    setPlaying(false)
    activeEl.current?.pause()
  }, [])

  const toggle = useCallback(() => {
    if (playingRef.current) pause()
    else play()
  }, [pause, play])

  const seek = useCallback(
    (target: number) => {
      const rec = recordingRef.current
      const el = activeEl.current
      if (!rec || !el) return
      const t = Math.min(Math.max(target, 0), rec.totalDuration)
      const idx = partIndexAt(rec.parts, t)
      const offset = t - rec.parts[idx].start

      if (idx !== activeIdx.current) {
        activeIdx.current = idx
        setActivePart(idx + 1)
        el.src = partAudioUrl(rec.id, idx + 1)
        el.load()
        const apply = () => {
          el.currentTime = offset
          if (playingRef.current) startPlayback(el)
        }
        if (el.readyState >= 1) apply()
        else el.addEventListener('loadedmetadata', apply, { once: true })
        preloadIntoStandby(idx)
      } else {
        el.currentTime = offset
      }
      setGlobalTime(t)
    },
    [preloadIntoStandby, startPlayback],
  )

  const skipPart = useCallback(
    (delta: number) => {
      const rec = recordingRef.current
      if (!rec) return
      const target = Math.min(Math.max(activeIdx.current + delta, 0), rec.parts.length - 1)
      seek(rec.parts[target].start + 0.001)
    },
    [seek],
  )

  const setVolume = useCallback((v: number) => {
    setVolumeState(v)
    volumeRef.current = v
    for (const el of [audioA.current, audioB.current]) {
      if (el) el.volume = v
    }
  }, [])

  const setPlaybackRate = useCallback((r: number) => {
    setRateState(r)
    for (const el of [audioA.current, audioB.current]) {
      if (el) el.playbackRate = r
    }
  }, [])

  const toggleMute = useCallback(() => {
    setMutedState((prev) => {
      for (const el of [audioA.current, audioB.current]) {
        if (el) el.muted = !prev
      }
      return !prev
    })
  }, [])

  const seekBy = useCallback(
    (delta: number) => {
      const rec = recordingRef.current
      const el = activeEl.current
      if (!rec || !el) return
      seek(rec.parts[activeIdx.current].start + el.currentTime + delta)
    },
    [seek],
  )

  return {
    playing,
    globalTime,
    activePart,
    duration: recording?.totalDuration ?? 0,
    volume,
    bufferedEnd,
    playbackRate,
    muted,
    play,
    pause,
    toggle,
    seek,
    seekBy,
    skipPart,
    setVolume,
    setPlaybackRate,
    toggleMute,
  }
}
