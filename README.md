# Healthcare Scribble — Segmented Audio Streaming Player

Multi-part audio streaming player for consultation recordings. Audio parts (1..N, ~1 min
each) play continuously as **one track** on a single unified seek bar with YouTube-style
**segmented chapters**, streaming via HTTP Range requests, with **word-level transcript
sync** — the spoken word highlights in real time.

Backend: Python FastAPI · Frontend: React + TypeScript (Vite) · Storage: local folder.

## Quickstart

```bash
./run.sh          # bootstraps venv + deps + demo data, starts both servers
```

Then open **http://localhost:5173**.

First run generates 5 demo MP3 parts (~4 min total, healthcare consultation script) with
word-level timestamps, entirely on-device (`say` + `lameenc` — no ffmpeg needed).

## How it works

```
Unified virtual timeline:  [ P1 44s ][ P2 45s ][ P3 52s ][ P4 43s ][ P5 48s ]
global time = partOffset[partIndex] + timeInsidePart
```

- **Double-buffered playback** — two `<audio>` elements; part N+1 preloads while N plays
  and is swapped in ~0.3s before the boundary, eliminating gaps.
- **Range streaming** — `/parts/{n}/audio` serves `206 Partial Content` with correct
  `Content-Range`/`ETag`; frontend seeks map to (part, byte-offset) transparently.
- **Word sync** — the API re-bases all word timestamps to global time; the frontend does
  one binary search per animation frame to find the active word.

## Structure

```
backend/
  app/                    FastAPI app (api/, services/, models/, core/)
  data/recordings/        local audio parts + per-part word transcripts
  data/recordings.json    manifest (single source of truth, durations probed)
  scripts/build_manifest.py   rescan folder -> rebuild manifest
  tests/                  pytest (Range logic, API, transcript merge)
frontend/
  src/hooks/usePlayer.ts      double-buffer playback engine
  src/components/SeekBar.tsx  segmented seek bar (click / drag / hover tooltip)
  src/components/TranscriptPanel.tsx  word-level synced transcript
scripts/generate_demo_data.py   creates demo audio + transcripts + manifest
run.sh
```

## API

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/recordings` | list recordings |
| GET | `/api/recordings/{id}` | parts with cumulative offsets |
| GET | `/api/recordings/{id}/transcript` | words re-based to global time |
| GET | `/api/recordings/{id}/parts/{n}/audio` | MP3, full HTTP Range support |
| POST | `/api/recordings/{id}/merge` | concatenate all parts into one MP3 (cached until parts change) |
| GET | `/api/recordings/{id}/download` | merged MP3 as attachment (builds on demand) |

## Using your own recordings

1. Drop MP3s named `part-1.mp3 … part-N.mp3` into
   `backend/data/recordings/<your-id>/parts/`
2. Put per-part Whisper word-level transcripts (`{"part": n, "words": [{"word", "start", "end"}]}`,
   times relative to the part) into `backend/data/recordings/<your-id>/transcripts/`
3. `python backend/scripts/build_manifest.py`

Generating word timestamps: `whisper audio.mp3 --word_timestamps True --output_format json`.

## Tests

```bash
.venv/bin/python -m pytest backend/tests      # backend (30 tests)
cd frontend && npx vitest run                 # frontend timeline math (8 tests)
```

## Controls

Space play/pause · ←/→ seek ∓5s · J/L previous/next part · click any word to jump there ·
speed 0.75×–2× · mute · volume · Download merges all parts into one MP3.
