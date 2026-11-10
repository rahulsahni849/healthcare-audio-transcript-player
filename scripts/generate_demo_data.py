"""Generate demo data: 5 ~1-minute MP3 parts of a consultation recording, each with a
word-level transcript (Whisper word_timestamps format), then build the manifest.

Usage: python scripts/generate_demo_data.py
"""
import json
import subprocess
import sys
import wave
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
sys.path.insert(0, str(BACKEND))

import lameenc  # noqa: E402
from mutagen.mp3 import MP3  # noqa: E402

from scripts.build_manifest import build_manifest  # noqa: E402

RECORDING_ID = "demo-consultation-001"
RECORDING_TITLE = "Consultation — Patient Intake"

PARTS = [
    (
        "Chief complaint",
        "Good morning, Ms. Sharma. I'm Doctor Mehta, and I'll be reviewing your intake today. "
        "Before we begin, let me confirm your details. You are fifty two years old, and this is "
        "your first visit to our clinic. How can I help you today? Thank you, doctor. For the "
        "past three weeks I've been experiencing shortness of breath, especially when I climb "
        "stairs or carry groceries. The tightness in my chest usually settles after a few "
        "minutes of rest, but last Tuesday it lasted almost twenty minutes. I also noticed some "
        "swelling around my ankles in the evenings. That sounds uncomfortable. Let's go through "
        "this carefully so we can understand what's happening. I'd like to ask about the pattern "
        "of your symptoms, your medical history, and the medications you currently take.",
    ),
    (
        "History of present illness",
        "Let's talk about the breathlessness in more detail. When did you first notice it? It "
        "started gradually, about three weeks ago. At first I felt it only after long walks, but "
        "now even one flight of stairs leaves me winded. Do you experience any pain along with "
        "the chest tightness? There is a dull pressure, right behind the breastbone, but no "
        "sharp pain. It never radiates to my arm or jaw. On a scale of one to ten, the pressure "
        "stays around three or four. Does it wake you at night? Sometimes, if I lie flat. I keep "
        "two pillows now, and that helps. Any coughing or wheezing? A dry cough at night, "
        "occasionally. Have you noticed palpitations, dizziness, or fainting spells? Some light "
        "headedness when I stand up quickly, but no fainting.",
    ),
    (
        "Medications and allergies",
        "Thank you. Now let's review your medications. What are you currently taking? I take "
        "metformin five hundred milligrams twice daily for diabetes, and lisinopril ten "
        "milligrams in the morning for blood pressure. I also use omeprazole sometimes for "
        "acidity. Any over the counter supplements? Yes, a calcium tablet with vitamin D, and "
        "occasionally paracetamol for headaches. That's all. Are you allergic to any "
        "medications? I had a rash with penicillin years ago, so my family doctor marked it as "
        "an allergy. Any food or environmental allergies? Dust gives me sneezing fits in the "
        "morning, but nothing serious otherwise. Do you smoke or drink alcohol? I used to smoke "
        "socially, but I stopped eight years ago. I have wine maybe twice a month. And any "
        "recent changes in weight or appetite? I've lost about three kilograms in two months "
        "without trying.",
    ),
    (
        "Physical examination",
        "I'd like to examine you now. Your blood pressure is one hundred forty five over ninety, "
        "pulse eighty eight and regular. Oxygen saturation is ninety four percent on room air. "
        "Let me listen to your heart and lungs. Taking a deep breath in, and out. There are fine "
        "crackles at both lung bases, no wheeze. Heart sounds are normal, no murmurs that I can "
        "hear. Your ankles show mild pitting oedema, about two plus, extending just above the "
        "ankle bone. The jugular veins are slightly raised. Abdomen is soft and non tender. I'm "
        "also noting that your breathing is a little laboured after walking to the examination "
        "table. Overall, the findings suggest some fluid retention. I want to correlate this "
        "with a few tests before we discuss treatment.",
    ),
    (
        "Assessment and plan",
        "Here is my assessment. Your symptoms and examination point towards early congestive "
        "heart failure, possibly related to long standing hypertension and diabetes. We need to "
        "confirm this. I'm ordering a chest X ray, an ECG, an echocardiogram, and basic blood "
        "work including kidney function and BNP. Until we meet again, I'd like you to reduce "
        "salt in your diet, monitor your weight every morning, and let me know if it rises by "
        "two kilograms in three days. Continue your current medications; I'm adding a low dose "
        "diuretic to relieve the fluid. Watch for warning signs: worsening breathlessness at "
        "rest, chest pain lasting more than fifteen minutes, or fainting. If any of these occur, "
        "go to the emergency department immediately. Shall we schedule a follow up in one week "
        "to review your reports? Take care.",
    ),
]

VOICE_CANDIDATES = ["Samantha", "Karen", "Moira", "Albert"]

LEAD_IN = 0.18
TAIL = 0.30
GAP_FACTOR = 0.90


def pick_voice() -> list[str]:
    try:
        installed = subprocess.run(["say", "-v", "?"], capture_output=True, text=True).stdout
        for voice in VOICE_CANDIDATES:
            if any(line.split()[0] == voice for line in installed.splitlines() if line.strip()):
                return ["-v", voice]
    except Exception:
        pass
    return []


def synth_to_wav(text: str, wav_path: Path, voice: list[str]) -> None:
    subprocess.run(["say", *voice, "-o", str(wav_path), "--data-format=LEI16@22050", text], check=True)


def wav_to_mp3(wav_path: Path, mp3_path: Path) -> None:
    with wave.open(str(wav_path)) as w:
        pcm = w.readframes(w.getnframes())
        sample_rate = w.getframerate()
    enc = lameenc.Encoder()
    enc.set_bit_rate(128)
    enc.set_in_sample_rate(sample_rate)
    enc.set_channels(1)
    enc.set_quality(2)
    mp3 = bytes(enc.encode(pcm)) + bytes(enc.flush())
    mp3_path.write_bytes(mp3)


def word_timings(text: str, duration: float) -> list[dict]:
    tokens = text.split()
    weights = []
    for tok in tokens:
        w = max(len(tok), 2) + 2
        if tok[-1] in ".?!,":
            w += 5
        weights.append(w)
    total = sum(weights)
    speakable = max(duration - LEAD_IN - TAIL, 1.0)

    words, cursor = [], LEAD_IN
    for tok, w in zip(tokens, weights):
        span = w / total * speakable
        end = min(cursor + span * GAP_FACTOR, duration - 0.05)
        words.append({"word": tok, "start": round(cursor, 3), "end": round(end, 3)})
        cursor += span
    return words


def main() -> None:
    rec_dir = ROOT / "backend" / "data" / "recordings" / RECORDING_ID
    parts_dir = rec_dir / "parts"
    transcripts_dir = rec_dir / "transcripts"
    for d in (parts_dir, transcripts_dir):
        d.mkdir(parents=True, exist_ok=True)

    voice = pick_voice()
    print(f"voice: {voice[1] if voice else 'system default'}")

    import tempfile

    for i, (_, text) in enumerate(PARTS, start=1):
        wav_path = Path(tempfile.mkstemp(suffix=".wav")[1])
        try:
            synth_to_wav(text, wav_path, voice)
            mp3_path = parts_dir / f"part-{i}.mp3"
            wav_to_mp3(wav_path, mp3_path)
        finally:
            wav_path.unlink(missing_ok=True)

        duration = MP3(str(mp3_path)).info.length
        words = word_timings(text, duration)
        out = {"part": i, "duration": round(duration, 3), "words": words}
        (transcripts_dir / f"part-{i}.json").write_text(
            json.dumps(out, indent=2) + "\n", encoding="utf-8"
        )
        print(f"part-{i}.mp3  {duration:6.2f}s  {len(words)} words")

    build_manifest()

    manifest = json.loads((ROOT / "backend" / "data" / "recordings.json").read_text())
    manifest["recordings"][0]["title"] = RECORDING_TITLE
    (ROOT / "backend" / "data" / "recordings.json").write_text(
        json.dumps(manifest, indent=2) + "\n"
    )
    print(f"demo recording '{RECORDING_ID}' ready")


if __name__ == "__main__":
    main()
