import { describe, expect, it } from 'vitest'
import { findWordIndex, fmtTime, partIndexAt } from './timeline'
import type { PartSummary, Word } from '../types'

const parts: PartSummary[] = [
  { index: 1, duration: 60, start: 0, end: 60 },
  { index: 2, duration: 58.7, start: 60, end: 118.7 },
  { index: 3, duration: 60.1, start: 118.7, end: 178.8 },
]

const words: Word[] = [
  { word: 'Good', start: 0.1, end: 0.5, part: 1 },
  { word: 'morning', start: 0.6, end: 1.2, part: 1 },
  { word: 'doctor', start: 60.0, end: 60.8, part: 2 },
  { word: 'thanks', start: 61.0, end: 61.6, part: 2 },
]

describe('partIndexAt', () => {
  it('maps times to correct parts', () => {
    expect(partIndexAt(parts, 0)).toBe(0)
    expect(partIndexAt(parts, 59.9)).toBe(0)
    expect(partIndexAt(parts, 60)).toBe(1)
    expect(partIndexAt(parts, 118.6)).toBe(1)
    expect(partIndexAt(parts, 118.7)).toBe(2)
    expect(partIndexAt(parts, 999)).toBe(2)
  })

  it('clamps times before start to first part', () => {
    expect(partIndexAt(parts, -5)).toBe(0)
  })
})

describe('findWordIndex', () => {
  it('finds the active word', () => {
    expect(findWordIndex(words, 0.3)).toBe(0)
    expect(findWordIndex(words, 0.8)).toBe(1)
    expect(findWordIndex(words, 60.4)).toBe(2)
  })

  it('returns -1 in gaps between words', () => {
    expect(findWordIndex(words, 0.55)).toBe(-1)
    expect(findWordIndex(words, 60.9)).toBe(-1)
  })

  it('returns -1 before first and after last word', () => {
    expect(findWordIndex(words, 0.05)).toBe(-1)
    expect(findWordIndex(words, 100)).toBe(-1)
  })

  it('handles empty word list', () => {
    expect(findWordIndex([], 1)).toBe(-1)
  })
})

describe('fmtTime', () => {
  it('formats m:ss', () => {
    expect(fmtTime(0)).toBe('0:00')
    expect(fmtTime(59)).toBe('0:59')
    expect(fmtTime(61)).toBe('1:01')
    expect(fmtTime(231.9)).toBe('3:51')
  })

  it('clamps negative values', () => {
    expect(fmtTime(-3)).toBe('0:00')
  })
})
