import type { PartSummary, Word } from '../types'

export function partIndexAt(parts: PartSummary[], t: number): number {
  let lo = 0
  let hi = parts.length - 1
  while (lo < hi) {
    const mid = (lo + hi + 1) >> 1
    if (parts[mid].start <= t) lo = mid
    else hi = mid - 1
  }
  return lo
}

export function findWordIndex(words: Word[], t: number): number {
  let lo = 0
  let hi = words.length - 1
  let ans = -1
  while (lo <= hi) {
    const mid = (lo + hi) >> 1
    if (words[mid].start <= t) {
      ans = mid
      lo = mid + 1
    } else {
      hi = mid - 1
    }
  }
  if (ans >= 0 && t <= words[ans].end) return ans
  return -1
}

export function fmtTime(seconds: number): string {
  const s = Math.max(0, Math.floor(seconds))
  const m = Math.floor(s / 60)
  return `${m}:${String(s % 60).padStart(2, '0')}`
}
