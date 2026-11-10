import { useState } from 'react'
import { api } from '../api/client'

interface DownloadButtonProps {
  recordingId: string
}

export function DownloadButton({ recordingId }: DownloadButtonProps) {
  const [state, setState] = useState<'idle' | 'preparing' | 'error'>('idle')

  const handleDownload = async () => {
    if (state === 'preparing') return
    setState('preparing')
    try {
      const meta = await api.mergeRecording(recordingId)
      const res = await fetch(api.downloadUrl(recordingId))
      if (!res.ok) throw new Error(`Download failed (${res.status})`)
      const blob = await res.blob()
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = meta.filename
      document.body.appendChild(a)
      a.click()
      a.remove()
      URL.revokeObjectURL(url)
      setState('idle')
    } catch {
      setState('error')
      setTimeout(() => setState('idle'), 3000)
    }
  }

  return (
    <button
      className={`download-btn${state === 'preparing' ? ' busy' : ''}${state === 'error' ? ' error' : ''}`}
      onClick={handleDownload}
      disabled={state === 'preparing'}
      title="Merge all parts and download as one MP3"
    >
      <svg viewBox="0 0 24 24" width="15" height="15" fill="currentColor">
        <path d="M5 20h14v-2H5v2zM19 9h-4V3H9v6H5l7 7 7-7z" />
      </svg>
      {state === 'preparing' ? 'Merging…' : state === 'error' ? 'Failed — retry' : 'Download'}
    </button>
  )
}
