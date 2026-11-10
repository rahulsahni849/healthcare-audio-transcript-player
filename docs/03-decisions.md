# 03 — Decision Log

Every meaningful decision made while building this module: the options on the table, the
choice, and the reasoning. Ordered by impact.

---

## D1 — Unified virtual timeline instead of per-part players

**Options**
1. Five separate players/seek bars, one per part.
2. One player; hide part boundaries; treat durations as one continuous track.

**Decision:** Option 2 — a virtual timeline where `globalTime = part.start + el.currentTime`.

**Why:** The product requirement is "all parts play on one seek". A single number that
describes playback position makes every feature trivial: seek bar fills, time display,
transcript sync, keyboard seeking. Five players would need cross-player coordination for
every one of those. The cost is small mapping math (`partIndexAt`, binary search), which
is pure, tested, and O(log n).

---

## D2 — Double-buffered `<audio>` elements (A/B swap) for gapless playback

**Options**
1. Single `<audio>`, swap `src` on `ended` → guaranteed audible gap (network + decode
   latency at the worst moment).
2. Two `<audio>` elements: one plays, the other preloads the next part; swap ~0.3 s
   before the boundary.
3. Web Audio API with fully decoded AudioBuffers → sample-accurate, but must decode whole
   parts into memory and re-implement all transport logic.

**Decision:** Option 2.

**Why:** Parts are small (≈700 KB) local MP3s, so preloading is near-instant. The swap
happens while audio is still playing (0.3 s threshold + `readyState ≥ 3` check), so the
user hears no gap. Option 1's gap is a hard product failure; option 3's memory cost and
complexity buy nothing at 1-minute granularity. `ended` remains as a fallback safety net.

---

## D3 — HTTP Range streaming (206) instead of HLS/DASH

**Options**
1. HLS (`.m3u8` + segmented stream) — the "streaming video" answer.
2. Plain MP3 files + RFC 7233 Range requests.
3. No ranges — serve whole files, fetch all parts upfront as blobs.

**Decision:** Option 2.

**Why:** Parts are already ~1-minute segments — the app *is* the segmentation layer, so
the transport doesn't need to re-segment. Range requests give exact byte-level seeking,
work on every browser (Safari is strict here and was explicitly tested), need no
transcoding pipeline, and keep storage as plain files. HLS would add playlist generation,
segmenting tooling and latency for zero UX gain at this scale. Option 3 breaks
"streaming" and wastes bandwidth on long recordings.

**Sub-decision:** the Range parser is **hand-written and unit-tested** rather than
relying on Starlette's `FileResponse`. Behavior is deterministic and explicit: open-ended
(`bytes=500-`), suffix (`bytes=-500`), clamped, invalid-unit, and `416` paths are all
covered by tests, including byte-accuracy assertions comparing 206 bodies against the
full file.

---

## D4 — Manifest file (`recordings.json`) as source of truth, no DB

**Why:** Requirement was "keep audio and transcripts locally in a folder". A JSON
manifest written by a one-shot script (`build_manifest.py`) that probes real durations
with `mutagen` means: the API never trusts client-side duration guesses, never probes
files per-request, and deployment is copy-a-folder. Cache invalidation is keyed on the
manifest's `mtime_ns` — edits take effect immediately without server restart.

**Path safety corollary:** part files are resolved **only** through the manifest (never
from URL fragments), plus a belt-and-braces `Path.is_relative_to` containment check.

---

## D5 — Server-side word rebasing (part-relative → global time)

**Options**
1. Serve transcripts per part; frontend adds offsets while playing.
2. Serve one merged transcript with all words already on the global timeline.

**Decision:** Option 2 (`services/transcript.py::merge_transcript`).

**Why:** It removes an entire class of frontend bugs (forgetting offsets during seeks,
part transitions, or word clicks). The frontend's sync code becomes a single binary
search over one flat, pre-sorted array. Merging is O(words) at request time and trivially
cacheable; it also gives the API a clean contract for any future consumer (mobile,
highlight export, etc.).

---

## D6 — requestAnimationFrame clock, not `timeupdate` events

**Options**
1. `timeupdate` events (~4 Hz) — jumpy highlight, visible lag.
2. `setInterval` — drifts, stacks awkwardly with pause/resume.
3. One persistent rAF loop reading `activeEl.currentTime` each frame.

**Decision:** Option 3. One clock, one writer. Every UI value is a projection of it.
All state writes are delta-throttled (time updates >16 ms, buffered >50 ms) so React
doesn't churn on identical values. `playingRef` mirrors the playing flag so the loop
never suffers stale-closure bugs — the classic hazard of rAF + React.

---

## D7 — Custom div-based segmented seek bar, not `<input type=range>`

**Why:** The requirement is YouTube-chapter rendering: per-part fills, 2 px boundary
gaps, per-segment buffered overlays, hover tooltip with part label. A native range input
can't render any of that. Implementation is a flex row of segment divs + pointer capture,
so click-drag-share one code path and `touch-action: none` makes it work on trackpads and
touch alike. ARIA `role="slider"` attributes are set manually.

---

## D8 — `lameenc` + `say` for demo data (no ffmpeg on the machine)

**Constraint discovered during build:** the environment has no `ffmpeg`/`ffprobe`.

**Options**
1. Ask user to `brew install ffmpeg`.
2. `afconvert` → M4A/AAC (native, but not MP3 as requested).
3. `pip install lameenc` (LAME bindings, prebuilt wheels) + macOS `say` → WAV via
   `--data-format=LEI16@22050` → encode → probe duration with `mutagen`.

**Decision:** Option 3. Zero native dependencies, reproduces anywhere with Python 3.13,
stays MP3 as requested. `wave` (stdlib) reads the PCM; `lameenc` encodes; `mutagen`
probes real durations for the manifest. The pipeline (`say` → WAV → MP3) is verified
end-to-end and takes seconds for all five parts.

---

## D9 — Synthetic word timestamps for the demo; Whisper shape for production

`say` cannot emit timings, so the generator distributes words across the **measured MP3
duration**: each word weighted by `max(len(word), 2) + 2`, +5 after sentence punctuation,
scaled into a speakable window (0.18 s lead-in, 0.30 s tail), 10 % micro-gaps between
words. Because transcript and audio derive from the same script and duration, alignment
is consistent by construction.

Crucially, the JSON shape is exactly Whisper's `word_timestamps=True` output
(`{word, start, end}`), and the loader accepts it unchanged — swapping in real ASR later
is a file drop, not a refactor.

---

## D10 — FastAPI + pydantic v2, camelCase at the boundary

FastAPI for async endpoints, automatic OpenAPI, and pydantic validation. Response models
use `alias_generator=to_camel` so the wire format is `partCount`, `totalDuration` —
idiomatic JSON for the TypeScript side, while Python stays snake_case. Config via
`pydantic-settings` (`SCRIBBLE_*` env vars) so data dir / CORS / chunk size are
environment-overridable without code changes.

**Error contract:** every failure is `{"detail": {"code": ..., "message": ...}}` —
`404 RECORDING_NOT_FOUND`, `404 PART_NOT_FOUND`, `416 RANGE_NOT_SATISFIABLE`,
`503 MANIFEST_UNAVAILABLE`. The frontend surfaces `detail.message` directly.

---

## D11 — Vite dev proxy + scoped CORS

In dev the browser only ever sees same-origin `/api` (proxy → `:8000`), so no CORS
headaches and audio URLs are relative. The backend still ships an explicit CORS
allow-list (`localhost:5173`, GET/HEAD/OPTIONS, exposing `Content-Range`/`ETag`) so the
built frontend can be served from anywhere without code changes.

---

## D12 — What was deliberately left out (and the escalation path)

| Left out | Why | Production path |
|----------|-----|-----------------|
| Auth | out of scope for the module | FastAPI dependency in front of routers |
| DB persistence | folders + manifest satisfy "local storage" | SQLite/Postgres replacing `manifest.py` reads |
| Real ASR | demo data needed self-contained generation | `whisper audio.mp3 --word_timestamps True --output_format json` — same JSON shape |
| Waveform rendering | not required; seek bar carries the UX | peaks.js or precomputed peaks JSON per part |
| Service Worker / offline caching | dev-stage tool | Cache Storage API keyed on ETag |
| Mobile autoplay-resume handling | desktop-focused demo | visibility/interruption event listeners in `usePlayer` |

---

## D13 — Testing strategy

- **Backend (30 pytest tests):** Range parser table-tests (all header forms); API tests
  spin up `TestClient` against a temp data dir with **real tiny MP3s encoded by
  lameenc in the fixture** — so 206 byte-accuracy is asserted by comparing against the
  actual full-file bytes, not mocked streams. Cumulative offsets, global word rebasing,
  merge byte-identity, cache reuse and staleness are all asserted exactly.
- **Frontend (8 vitest tests):** the pure math layer only — `partIndexAt` boundary cases
  (exactly at a boundary belongs to the next part), `findWordIndex` gaps/before/after,
  `fmtTime`. Components stay thin projections, so math coverage ≈ behaviour coverage.
- **E2E manual checklist** (run through after every change): play unattended across all
  5 parts; seek to every boundary ±1 s; seek while paused; rapid J/L skipping;
  pause/resume across a boundary; word-click seeking.

---

## D14 — Full-audio merge via byte concatenation, with stale-aware cache

**Options**
1. Decode + re-encode parts into one MP3 — needs an MP3 decoder; none exists in pure
   Python without ffmpeg (pydub, librosa all wrap ffmpeg).
2. Byte-concatenate the part files.
3. No merging — stream parts sequentially into a MediaRecorder — hacky, lossy, slow.

**Decision:** Option 2. All parts share identical encoder settings (same lameenc CBR
128 kbps, 22.05 kHz mono), and MP3 is a frame stream — concatenated frames decode as one
continuous file. Verified: the merged file plays for exactly the summed duration
(231.91 s) and mutagen parses it cleanly.

**Guarantees shipped with it:**
- **Stale-aware cache:** `merged.mp3` is rebuilt only when any `part-N.mp3` has a newer
  mtime — repeated downloads are O(1), and replacing a part refreshes the next export.
- **Atomic writes:** temp file + `Path.replace()`, so a download never observes a
  half-written merge, even with concurrent requests.
- **Honest limitation:** for parts encoded with *different* settings (real-world
  recordings from multiple sources), a decoder pass is required — production path is
  spawning `ffmpeg -f concat` in `merge.py`; the service interface (path in, path out)
  is already shaped for that swap.
