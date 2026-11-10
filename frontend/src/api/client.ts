import type { MergedTranscript, RecordingDetail, RecordingSummary } from '../types'

const API_BASE: string = import.meta.env.VITE_API_BASE ?? '/api'

export interface MergeResult {
  filename: string
  size: number
  partCount: number
}

async function fetchJson<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, init)
  if (!res.ok) {
    let message = `Request failed (${res.status})`
    try {
      const body = await res.json()
      if (body?.detail?.message) message = body.detail.message
    } catch {
      /* keep default */
    }
    throw new Error(message)
  }
  return res.json() as Promise<T>
}

export const api = {
  listRecordings: () => fetchJson<RecordingSummary[]>('/recordings'),
  getRecording: (id: string) => fetchJson<RecordingDetail>(`/recordings/${id}`),
  getTranscript: (id: string) => fetchJson<MergedTranscript>(`/recordings/${id}/transcript`),
  mergeRecording: (id: string) =>
    fetchJson<MergeResult>(`/recordings/${id}/merge`, { method: 'POST' }),
  downloadUrl: (id: string) => `${API_BASE}/recordings/${id}/download`,
}

export function partAudioUrl(recordingId: string, partIndex: number): string {
  return `${API_BASE}/recordings/${recordingId}/parts/${partIndex}/audio`
}
