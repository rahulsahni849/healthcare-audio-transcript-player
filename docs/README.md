# Documentation Index

Reference documentation for the Segmented Audio Streaming Player module.

| Doc | Contents |
|-----|----------|
| [01-architecture.md](01-architecture.md) | System overview, component diagrams, data model, API contract, file map |
| [02-flows.md](02-flows.md) | End-to-end flow diagrams: demo data generation, app boot, streaming, playback, part transitions, seeking, word sync |
| [03-decisions.md](03-decisions.md) | Every technical decision made while building, the options considered, and why each choice won |

## Quick orientation

```
You are here: demo-consultation-001 (5 MP3 parts, ~4 min total)

Browser (React) ──► Vite dev proxy (:5173/api) ──► FastAPI (:8000) ──► backend/data/ (local folder)
     │                                                                      │
     ├─ GET /api/recordings                     ──► recordings.json (manifest)
     ├─ GET /api/recordings/{id}/transcript     ──► part-N.json (words rebased to global time)
     └─ GET /api/recordings/{id}/parts/N/audio  ──► 206 Partial Content byte ranges (streaming)
```

Run everything: `./run.sh` → open http://localhost:5173
