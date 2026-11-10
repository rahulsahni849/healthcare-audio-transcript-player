import { useMemo } from 'react'
import type { Word } from '../types'
import { findWordIndex } from '../utils/timeline'

export function useTranscript(words: Word[], globalTime: number): number {
  return useMemo(() => findWordIndex(words, globalTime), [words, globalTime])
}
