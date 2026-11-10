# Healthcare Scribble — Segmented Audio Streaming Player

Production-grade plan for a multi-part audio streaming player with YouTube-style segmented
seek bar and word-level transcript sync.

**Stack:** Python (FastAPI) backend · React + TypeScript (Vite) frontend · local filesystem storage.

---

## 1. Goals

| # | Requirement |
|---|-------------|
| G1 | Recording is split into N parts (~1 min each). All parts play continuously as **one track**. |
| G2 | **Single unified seek bar** across all parts — seeking anywhere jumps to the correct part + offset. |
| G3 | **Streaming** — audio served via HTTP Range requests; parts pre-buffered, minimal gap at boundaries. |
| G4 | **Segmented seek bar** (YouTube-style): each part shown as a distinct segment with its own progress fill, boundary markers, hover states. |
| G5 | **Word-level transcript sync** — the word being spoken is highlighted in real time as audio plays. |
| G6 | Minimal, clean UI. Recordings + transcripts stored **locally in a folder** (no DB). |

Non-goals (future): auth, DB persistence, upload/ingestion pipeline, mobile app, waveform rendering, HLS.

---

## 2. Architecture

```
┌─────────────────────────────┐        ┌──────────────────────────────┐
│  React TS (Vite) SPA        │        │  FastAPI                     │
│                             │        │                              │
│  Player.tsx                 │        │  GET /recordings             │
│   ├─ SeekBar.tsx  (G2, G4)  │◄─HTTP─►│  GET /recordings/{id}        │
│   ├─ Controls.tsx           │        │  GET /recordings/{id}/       │
│   └─ TranscriptPanel.tsx(G5)│        │        transcript            │
│                             │        │  GET /recordings/{id}/       │
│  usePlayer.ts (engine)      │        │        parts/{n}/audio  ──► 206
│   - 2 × <audio> double buf  │        │       (Range streaming)      │
│  useTranscript.ts (sync)    │        │                              │
└─────────────────────────────┘        │  data/recordings/... (local) │
                                       └──────────────────────────────┘
```

### Core concept — Unified Virtual Timeline
Each part has a duration. The player concatenates part durations into one **virtual
timeline**:

```
globalTime = partOffset[partIndex] + timeInsidePart

parts:      [  P1 (61.2s)  ][ P2 (58.7s) ][ P3 (60.1s) ][ P4 (59.4s) ][ P5 (62.0s) ]
global:     0           61.2          119.9         180.0         239.4        301.4
```

- Master seek position = `globalTime` (0 → totalDuration).
- `seek(globalTime)` → binary-search part table → set `audio.src = part[i]`, `currentTime = offset`.
- Transcript words are re-based to global time by the **server** (part offset + word time),
  so the frontend does one O(log n) binary search per animation frame to find the active word.

### Playback engine — double-buffered `<audio>` elements
To eliminate cross-part gaps, `usePlayer` keeps **two** `<audio>` elements:

1. Part *N* plays on element A; part *N+1* is preloaded (`preload="auto"`) on element B.
2. When A nears its end (< 0.25s remaining), B is started and roles swap.
3. Play/pause/seek/volume control the "active" element; state machine normalizes it into
   a single `globalTime` stream (rAF-driven, ~10 fps updates for UI, transcript on every frame).

---

## 3. Data Model (local filesystem)

```
backend/data/
├── recordings.json                      # global manifest
└── recordings/
    └── demo-consultation-001/
        ├── parts/
        │   ├── part-1.mp3 … part-5.mp3
        └── transcripts/
            └── part-1.json … part-5.json   # word-level timestamps
```

**recordings.json** (manifest — single source of truth, avoids trusting client file probing):

```json
{
  "recordings": [
    {
      "id": "demo-consultation-001",
      "title": "Consultation — Patient Intake",
      "parts": [
        { "index": 1, "file": "parts/part-1.mp3", "duration": 61.2 },
        { "index": 2, "file": "parts/part-2.mp3", "duration": 58.7 }
      ]
    }
  ]
}
```

**part transcript JSON** (Whisper `word_timestamps=True` format):

```json
{
  "part": 1,
  "words": [
    { "word": "Good",    "start": 0.12, "end": 0.44 },
    { "word": "morning", "start": 0.50, "end": 0.98 }
  ]
}
```

**Server-computed merged transcript** (what the API returns — words re-based to global time):

```json
{
  "recordingId": "demo-consultation-001",
  "totalDuration": 301.4,
  "parts": [ { "index": 1, "start": 0.0, "end": 61.2 }, ... ],
  "words": [ { "word": "Good", "start": 0.12, "end": 0.44, "part": 1 }, ... ]
}
```

`duration` per part is measured once at manifest build time (via `mutagen`/`ffprobe`) and
cached — the API never probes files per-request.

---

## 4. API Specification

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/api/recordings` | List recordings (id, title, part count, total duration). |
| `GET` | `/api/recordings/{id}` | Recording detail: parts with durations + computed global offsets. |
| `GET` | `/api/recordings/{id}/transcript` | Merged transcript (global-time words) + part boundaries. |
| `GET` | `/api/recordings/{id}/parts/{index}/audio` | **MP3 with full HTTP Range support** → `206 Partial Content`, `Accept-Ranges: bytes`, `Content-Length`, `ETag`. Streams only requested byte ranges. |

**Range streaming implementation:** custom endpoint reading `Range` header, parsing
`bytes=start-end`, returning a chunked `StreamingResponse` (64 KB chunks) with status 206.
Correctly handles: open-ended ranges (`bytes=500-`), suffix ranges (`bytes=-500`),
unsatisfiable ranges → `416`, missing Range → `200` full stream. Explicit implementation
(chosen over relying on Starlette `FileResponse`) so behavior is deterministic and testable.

**Error contract:** consistent JSON `{"detail": {"code": "...", "message": "..."}}` —
`404 RECORDING_NOT_FOUND / PART_NOT_FOUND`, `416 RANGE_NOT_SATISFIABLE`, `400` validation.

---

## 5. Backend Design (FastAPI)

```
backend/
├── app/
│   ├── main.py                 # app factory, CORS, router mount
│   ├── core/config.py          # pydantic-settings: DATA_DIR, CHUNK_SIZE, host/port
│   ├── api/
│   │   ├── recordings.py       # list / detail / transcript
│   │   └── audio.py            # Range streaming endpoint
│   ├── services/
│   │   ├── manifest.py         # load + validate recordings.json (cached)
│   │   ├── transcript.py       # merge part transcripts → global timeline
│   │   └── media.py            # Range parsing, file streaming, ETag
│   └── models/schemas.py       # pydantic response models
├── data/                       # recordings.json + audio/transcripts
├── scripts/build_manifest.py   # (re)generate manifest: probe durations, write JSON
├── tests/                      # pytest: API + Range logic + transcript merge
└── requirements.txt
```

Key decisions:
- **pydantic-settings** for config; `DATA_DIR` env-overridable (prod-ready).
- **lru_cache** on manifest/transcript loads (filesystem is static during runtime).
- Path traversal protection: part index resolved via manifest only — never from URL path fragments.
- `uvicorn` with workers config in `run.sh`; CORS scoped to the Vite dev origin.

---

## 6. Frontend Design (React + TS)

```
frontend/src/
├── api/client.ts               # typed fetch wrappers
├── types.ts                    # Recording, Part, Word, PlayerState
├── hooks/
│   ├── usePlayer.ts            # double-buffer engine, state machine, rAF clock
│   └── useTranscript.ts        # active-word lookup (binary search, memoized)
└── components/
    ├── Player.tsx              # layout shell
    ├── SeekBar.tsx             # segmented YouTube-style bar (G4)
    ├── Controls.tsx            # play/pause, skip part ±1, time display, volume
    ├── TranscriptPanel.tsx     # scrollable words, auto-scroll to active word
    └── RecordingPicker.tsx     # minimal list of available recordings
```

### SeekBar (G2 + G4)
- Pure div/SVG (no lib): container split into `flex` segments, each segment width =
  `partDuration / totalDuration × 100%`.
- Per segment: played fill (linear-gradient sized by %), hover highlight, 2px boundary gap
  (the "YouTube chapters" look).
- Interactions: click → seek; drag → scrub (pointer events, `setPointerCapture`);
  hover tooltip with `mm:ss` + part label ("Part 2 · 0:47").
- Buffered ranges rendered as translucent overlay per segment.

### Word sync (G5)
- `useTranscript(words, globalTime)` → binary search (`O(log n)`) for last word with
  `start <= t`, active while `t < word.end`; returns active word id.
- `TranscriptPanel` renders words as `<span>`s; active word gets highlight class;
  auto-scrolls (block: nearest) when the active word moves out of view.
- Clock source: single `requestAnimationFrame` loop in `usePlayer` reading
  `activeAudio.currentTime + partOffset` — no drift, no timers.

### State machine
`idle → loading → playing ⇄ paused`, with `seeking` transitional state; part transitions
handled internally (`onEnded`/prebuffer swap). Exposed API:

```ts
const { state, globalTime, duration, activePart, play, pause, seek, skipPart, setVolume } = usePlayer(recording);
```

---

## 7. Demo Data Strategy

`scripts/generate_demo_data.py`:
1. 5 clinically-plausible consultation scripts (~1 min each, healthcare context).
2. Generate audio on macOS: `say -o part.aiff` → convert to MP3 via `ffmpeg`
   (fallback: `afconvert` to M4A if ffmpeg absent; plan documents both).
3. Generate word timestamps: distribute word durations by character length across the
   measured audio duration (deterministic synthetic alignment — sufficient for demo;
   production would use Whisper `word_timestamps=True`).
4. Probe real durations → write per-part transcript JSONs + `recordings.json` manifest.

---

## 8. Implementation Phases

| Phase | Deliverable | Exit criteria |
|-------|-------------|---------------|
| **P1 — Scaffold & demo data** | Repo layout, FastAPI skeleton, Vite React TS app, demo generator script | `run.sh` starts both servers; demo files + manifest generated; `curl /api/recordings` returns manifest |
| **P2 — Streaming API** | Range streaming endpoint, transcript merge endpoint, pytest suite | `curl -H "Range: bytes=0-1023"` → 206; all tests green |
| **P3 — Player engine** | `usePlayer` double-buffer engine, unified timeline math, Controls | Continuous playback across all 5 parts with no manual interaction; seeks map correctly |
| **P4 — Segmented seek bar** | `SeekBar` segments, drag/click/hover/tooltip, buffered overlay | Visual segments match part boundaries; scrubbing accurate ±0.2s |
| **P5 — Transcript sync** | Transcript panel, active-word highlight, auto-scroll | Highlighted word tracks audio within ~50 ms |
| **P6 — Polish & hardening** | Error/loading states, keyboard shortcuts (space, ←/→ part skip), README, final tests | Clean pass through full user flow; lint/typecheck clean |

---

## 9. Testing Strategy

- **Backend (pytest):** Range parser unit tests (all Range forms, invalid, 416);
  streaming endpoint tests via `TestClient` (206 headers, byte-accuracy, ETag);
  transcript merge correctness (offsets, part boundaries); manifest validation.
- **Frontend (vitest):** timeline math (`globalToPart`, `partToGlobal`, boundary cases);
  active-word binary search; SeekBar segment width/progress calculations.
- **Manual E2E checklist:** play through all parts unattended; seek to every boundary
  (±1s around each); seek while paused; rapid part skipping; pause/resume across boundary.

---

## 10. Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| Gap between parts on `src` swap | Double-buffered audio elements + prebuffer threshold; parts are local/streamed so load is fast |
| Browser auto-play policies | Engine only plays after explicit user gesture |
| Word highlight drift | Server re-bases words to global time; single rAF clock as sole time source |
| Range request bugs (Safari strictness) | Dedicated tested Range implementation; ETag + `Content-Range` correctness |
| File changes while cached in memory | `build_manifest.py` is the only writer; cache keyed on file mtime |

---

## 11. Deliverables & Run

```
./run.sh          # starts backend (uvicorn :8000) + frontend (vite :5173)
./scripts/generate_demo_data.py   # creates demo audio + transcripts + manifest
```

Final UX: pick recording → segmented seek bar with 5 visible chapters → press play →
audio streams seamlessly across parts while the transcript highlights the spoken word in real time.
