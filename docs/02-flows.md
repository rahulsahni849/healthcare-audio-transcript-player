# 02 — Flows

End-to-end flow diagrams. All diagrams match the implemented code (function/variable
names are real).

---

## 1. Demo data generation (one-time, offline)

`scripts/generate_demo_data.py` — no network, no ffmpeg, entirely on-device.

```mermaid
flowchart TD
    A["5 healthcare consultation scripts<br/>(~130 words each)"] --> B["macOS say<br/>voice: Samantha<br/>--data-format=LEI16@22050"]
    B --> C["WAV per part<br/>(16-bit PCM mono 22.05 kHz)"]
    C --> D["stdlib wave module<br/>read PCM frames"]
    D --> E["lameenc<br/>128 kbps CBR, quality 2"]
    E --> F["part-N.mp3"]
    F --> G["mutagen MP3.info.length<br/>probe real duration"]
    A --> H["word_timings(text, duration)<br/>weight = max(len(word),2)+2<br/>+5 after sentence punctuation"]
    G --> H
    H --> I["scale weights to speakable window<br/>duration - 0.18s lead-in - 0.30s tail<br/>word span × 0.90 (micro-gaps)"]
    I --> J["transcripts/part-N.json<br/>{word, start, end} relative to part"]
    F --> K["backend/scripts/build_manifest.py"]
    J --> K
    K --> L["recordings.json<br/>real probed durations per part"]
```

Word timings are **synthetic** (deterministic distribution by word length). They align
perfectly with the generated speech because both derive from the same script and the same
measured duration. The production path — Whisper `word_timestamps=True` — produces the
identical JSON shape, so nothing downstream changes.

---

## 2. App boot & data loading

```mermaid
sequenceDiagram
    participant B as Browser
    participant V as Vite proxy (:5173/api)
    participant API as FastAPI (:8000)
    participant D as data/

    B->>V: GET /recordings
    V->>API: proxied
    API->>D: recordings.json (mtime-keyed cache)
    API-->>B: [{id, title, partCount, totalDuration}]
    Note over B: RecordingPicker selects first recording

    par Recording detail
        B->>V: GET /recordings/demo-consultation-001
        V->>API: proxied
        API->>D: manifest
        API-->>B: parts[] with cumulative start/end offsets
    and Transcript
        B->>V: GET /recordings/demo-consultation-001/transcript
        V->>API: proxied
        API->>D: part-1..5.json
        API-->>B: 665 words rebased to global time
    end

    Note over B: usePlayer effect fires:
    B->>V: GET /parts/1/audio (Audio element A, preload=auto)
    B->>V: GET /parts/2/audio (Audio element B, preload=auto)
    Note over B: UI ready — first segments already buffered
```

---

## 3. The rAF tick loop (heartbeat of the player)

Runs continuously while a recording is loaded. This is the **only** place global time is
read, so every UI surface agrees by construction.

```mermaid
flowchart TD
    A["requestAnimationFrame tick (~60 fps)"] --> B{"recording && activeEl?"}
    B -- no --> Z["reschedule tick"]
    B -- yes --> C["partTime = part.start + el.currentTime"]
    C --> D["update bufferedEnd<br/>(throttled, Δ > 0.05s)"]
    D --> E{"playing AND standby has src<br/>AND remaining ≤ 0.3s<br/>AND standby.readyState ≥ 3?"}
    E -- yes --> F["swapToStandby()"]
    E -- no --> G{"playing?"}
    G -- yes --> H["setGlobalTime partTime<br/>(throttled, Δ > 16ms)"]
    G -- no --> Z
    F --> Z
    H --> Z
```

Every state write is delta-throttled so React re-renders only when a value actually moved.

---

## 4. Seamless part transition (the swap)

The whole point of double-buffering: the next part is already loaded when the current one
runs out.

```mermaid
sequenceDiagram
    participant A as Audio A (active, part N)
    participant B as Audio B (standby, part N+1)
    participant E as usePlayer engine

    Note over A: remaining ≤ 0.3s
    E->>A: pause()
    E->>B: currentTime = 0, roles swap (B is now active)
    E->>E: activeIdx++ → setActivePart(N+1)
    E->>B: play() (already buffered → no gap)
    E->>A: src = part N+2, load()  ← old A becomes the new standby
```

Fallback path: if buffering is slow and the element fires `ended` before the swap, the
`ended` handler performs the same `swapToStandby()` (or stops the player if it was the
last part). The 0.3 s threshold + `readyState ≥ 3` check make the fallback rare in
practice since parts are small local MP3s.

---

## 5. Seeking (unified seek bar → correct part + offset)

```mermaid
flowchart TD
    A["User clicks/drags at fraction x of the bar<br/>(SeekBar pointer capture)"] --> B["target = x × totalDuration"]
    B --> C["partIndexAt(parts, target)<br/>binary search → idx"]
    C --> D{"idx == activeIdx?"}
    D -- "yes (same part)" --> E["el.currentTime = target - part.start<br/>instant, no reload"]
    D -- "no (different part)" --> F["el.src = part idx+1, load()"]
    F --> G{"readyState ≥ 1?"}
    G -- yes --> H["set currentTime immediately"]
    G -- no --> I["wait loadedmetadata → set currentTime"]
    H --> J{"was playing?"}
    I --> J
    J -- yes --> K["play()"]
    J -- no --> L["stay paused"]
    E --> M["preloadIntoStandby(idx)<br/>standby loads part idx+2"]
    K --> M
    L --> M
    M --> N["setGlobalTime(target) — UI updates immediately"]
```

Keyboard: `←`/`→` = seek ±5 s · `J`/`L` = previous/next part (`skipPart` → `seek(part.start)`).

---

## 6. Word-level transcript sync

```mermaid
flowchart LR
    A["API serves words already<br/>rebased to GLOBAL time"] --> B["useTranscript(words, globalTime)"]
    B --> C["findWordIndex — binary search<br/>last word with start ≤ t, active while t ≤ end"]
    C --> D{"hit?"}
    D -- yes --> E["span.active<br/>accent background<br/>scrollIntoView nearest"]
    D -- "no (gap between words)" --> F["no highlight this frame"]
```

Why no drift: `globalTime` comes from the audio element's own clock via the rAF loop —
there is exactly one clock in the system. Word timestamps from the server are absolute on
that same timeline, so highlight accuracy equals timestamp accuracy (~±50 ms here).

Bonus: words are clickable — `onClick → seek(word.start + 0.01)`.

---

## 7. Seek bar rendering (per animation frame)

```mermaid
flowchart TD
    A["parts[] + globalTime + bufferedEnd + activePart"] --> B["for each part:<br/>width% = part.duration / totalDuration"]
    B --> C["played fill % = clamp((globalTime - p.start) / p.duration)"]
    B --> D["buffered fill % (active part only) =<br/>clamp((bufferedEnd - p.start) / p.duration)"]
    C --> E["segment div: track + buffered + played layers"]
    D --> E
    A --> F["playhead cursor at globalTime / totalDuration %"]
    A --> G["hover tooltip: Part N · m:ss"]
```

Segments are 2 px apart (`flex` + `gap`) — the "YouTube chapters" look. A single
`onPointerDown` + `setPointerCapture` handles click **and** drag scrubbing with one code
path; dragging calls `seek()` on every pointermove (cheap: same-part seeks only set
`currentTime`).

---

## 8. HTTP Range request lifecycle

```mermaid
sequenceDiagram
    participant Br as Browser (Audio element)
    participant API as GET /api/recordings/{id}/parts/N/audio
    participant FS as parts/part-N.mp3

    Br->>API: Range: bytes=1048576-
    API->>API: manifest lookup (cached) → part file
    API->>API: parse_range() → ByteRange(1048576, size-1)
    API->>FS: seek(1048576), read 64 KB chunks
    API-->>Br: 206 Partial Content<br/>Content-Range: bytes 1048576-1831679/1831680<br/>Accept-Ranges, ETag, Cache-Control
    FS-->>API: chunks stream until request satisfied
    Note over Br: element buffers ahead,<br/>playback continues

    Br->>API: Range: bytes=99999999-
    API-->>Br: 416 + Content-Range: bytes */1831680
```

---

## 9. Merge & download (full-audio export)

```mermaid
sequenceDiagram
    participant U as User
    participant DB as DownloadButton
    participant API as FastAPI
    participant FS as data/recordings/<id>/

    U->>DB: click Download
    DB->>API: POST /api/recordings/{id}/merge
    API->>FS: merged.mp3 exists AND newer than every part?
    alt cache is fresh
        API-->>DB: {filename, size, partCount} (no rebuild)
    else missing or stale
        API->>FS: write merged.mp3.tmp (1 MB copy chunks per part)
        API->>FS: atomic rename → merged.mp3
        API-->>DB: {filename, size, partCount}
    end
    DB->>API: GET /api/recordings/{id}/download
    API-->>DB: MP3 bytes, Content-Disposition: attachment
    DB->>U: triggers browser save (blob object URL)
```

Staleness rule: any `part-N.mp3` with `mtime > merged.mp3` mtime forces a rebuild, so
swapping a part's file automatically refreshes the next download. Concurrency-safe via
temp-file + atomic rename.

---

## 10. Error paths

| Scenario | Behaviour |
|----------|-----------|
| `recordings.json` missing | backend returns `503 MANIFEST_UNAVAILABLE`; UI shows the fix (`run generate_demo_data.py`) |
| Unknown recording / part id | `404 RECORDING_NOT_FOUND` / `PART_NOT_FOUND`; UI surfaces message |
| Malformed Range header | silently served as full `200` (spec-compliant leniency) |
| Unsatisfiable Range | `416` with `Content-Range: bytes */size` |
| Audio element fails to play (autoplay policy) | `play()` promise rejection swallowed; state stays paused, user gesture retries |
