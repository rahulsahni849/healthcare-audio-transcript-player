export interface PartSummary {
  index: number
  duration: number
  start: number
  end: number
}

export interface RecordingSummary {
  id: string
  title: string
  partCount: number
  totalDuration: number
}

export interface RecordingDetail {
  id: string
  title: string
  parts: PartSummary[]
  totalDuration: number
}

export interface Word {
  word: string
  start: number
  end: number
  part: number
}

export interface MergedTranscript {
  recordingId: string
  totalDuration: number
  parts: PartSummary[]
  words: Word[]
}
