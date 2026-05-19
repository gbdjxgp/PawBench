---
id: M010_score_canon_animated
name: Animated Sheet Music - Canon in D
category: multimodal
grading_type: hybrid
timeout_seconds: 1200
grading_weights:
  automated: 0.3
  llm_judge: 0.7
workspace_files:
- source: assets/T005_claweval_M010_score_canon_animated/fixtures/Canon1.png
  dest: fixtures/Canon1.png
labels:
  capabilities:
  - Tool_Use
  - Code_Manipulation
  modality:
    type: multimodal
    channels:
    - image
  scenario: Content_Creation/Design
  complexity: L3
  environment: closed
---
## Prompt

The workspace contains a sheet music image of **Canon in D** by Pachelbel:
- `fixtures/Canon1.png`

Please first view the image, then generate `output/output.html` — an **interactive playback page** with:

1. **Score** reproduced using inline SVG (staves, notes, clefs, key signature 2 sharps, time 4/4)
   - 8 measures, M1–4 bass solo (treble rests), M5–8 melody enters
   - Bass varying arpeggio: M1 (D-A), M2 (Bm-F#m), M3 (G-D), M4 (G-A) — **note positions vary per measure**
   - Treble M5–M8 melody half notes: F#5, E5, D5, C#5, B4, A4, B4, C#5
2. **Piano keyboard** drawn below the score
3. **Play button** that, when clicked:
   - Highlights notes sequentially left-to-right
   - Lights up corresponding piano keys in sync
   - Plays sound via the **Web Audio API** at the correct pitches
4. Smooth animation; reasonable playback speed
5. Title (`Canon in D`), composer (`Pachelbel`), tempo (`quarter = 100`)

Save the result to `output/output.html` (a single self-contained HTML file with inline SVG, JS, and CSS).

## Expected Behavior

- Read `fixtures/Canon1.png` first
- Build a single HTML file with SVG score, SVG piano, JS playback logic
- Click handler on a button highlights notes in sequence, plays Web Audio tones
- Save to `output/output.html`

## Grading Criteria

- [ ] Reads reference PNG (file_read)
- [ ] Output exists with inline SVG (output_file_exists, has_svg)
- [ ] Title/composer present (metadata_present)
- [ ] Piano keyboard SVG element present (piano_present)
- [ ] Play button present (play_button)
- [ ] Web Audio API used (web_audio)
- [ ] Highlight/animation logic referenced (animation_logic)
- [ ] Bass arpeggio note positions present (bass_pitches)
- [ ] Treble melody pitches present (melody_pitches)
- [ ] Substantial output (>6KB) (substantial_output)

## Automated Checks

```python
import re
from pathlib import Path


def grade(transcript: list, workspace_path: str) -> dict:
    result = {
        "file_read": 0.0,
        "output_file_exists": 0.0,
        "has_svg": 0.0,
        "metadata_present": 0.0,
        "piano_present": 0.0,
        "play_button": 0.0,
        "web_audio": 0.0,
        "animation_logic": 0.0,
        "bass_pitches": 0.0,
        "melody_pitches": 0.0,
        "substantial_output": 0.0,
    }

    def _all_text(msgs: list) -> str:
        parts = []
        for m in msgs:
            actual = m.get("message", m)
            if actual.get("role") not in ("assistant",):
                continue
            content = actual.get("content", "")
            if isinstance(content, str):
                parts.append(content)
            elif isinstance(content, list):
                for block in content:
                    if isinstance(block, dict):
                        parts.append(block.get("text", ""))
        return " ".join(parts)

    transcript_text = _all_text(transcript)

    output_path = Path(workspace_path) / "output" / "output.html"
    file_content = ""
    if output_path.is_file():
        result["output_file_exists"] = 1.0
        try:
            file_content = output_path.read_text(encoding="utf-8", errors="ignore")
            if len(file_content) > 6000:
                result["substantial_output"] = 1.0
            elif len(file_content) > 2500:
                result["substantial_output"] = 0.5
        except Exception:
            pass

    combined = transcript_text + " " + file_content

    if re.search(r"Canon1\.png|read_image|view_image|fixtures/Canon", combined, re.IGNORECASE):
        result["file_read"] = 1.0

    if re.search(r"<svg\b", file_content, re.IGNORECASE):
        result["has_svg"] = 1.0

    has_title = bool(re.search(r"Canon\s*in\s*D", file_content, re.IGNORECASE))
    has_composer = bool(re.search(r"Pachelbel", file_content, re.IGNORECASE))
    if has_title and has_composer:
        result["metadata_present"] = 1.0
    elif has_title or has_composer:
        result["metadata_present"] = 0.5

    if re.search(r"piano|keyboard|key.{0,4}white|key.{0,4}black|class\s*=\s*[\"']?(?:white|black)-?key", file_content, re.IGNORECASE):
        result["piano_present"] = 1.0

    if re.search(r"<button|class\s*=\s*[\"']play|id\s*=\s*[\"']play|>\s*Play\s*<", file_content, re.IGNORECASE):
        result["play_button"] = 1.0

    if re.search(r"AudioContext|webkitAudioContext|OscillatorNode|createOscillator|Web\s*Audio", file_content, re.IGNORECASE):
        result["web_audio"] = 1.0

    if re.search(r"setInterval|setTimeout|requestAnimationFrame|highlight|animate|@keyframes", file_content, re.IGNORECASE):
        result["animation_logic"] = 1.0

    bass_pitches = set(re.findall(r"\b[A-G][#b]?[2-4]\b", file_content))
    bass_target = {"D3", "F#3", "A3", "B2", "G2", "C#3", "E3"}
    overlap = bass_pitches & bass_target
    if len(overlap) >= 4:
        result["bass_pitches"] = 1.0
    elif len(overlap) >= 2:
        result["bass_pitches"] = 0.5

    melody_pitches = set(re.findall(r"\b[A-G][#b]?[4-5]\b", file_content))
    melody_target = {"F#5", "E5", "D5", "C#5", "B4", "A4"}
    overlap_m = melody_pitches & melody_target
    if len(overlap_m) >= 4:
        result["melody_pitches"] = 1.0
    elif len(overlap_m) >= 2:
        result["melody_pitches"] = 0.5

    return result
```

## LLM Judge Rubric

### Criterion 1: Score Visual Quality (Weight: 75%)

**Reference content:**
- Title: `Canon in D`, Key: D Major (2 sharps), Time: 4/4, Tempo: 100
- 8 measures: M1–4 bass solo (treble rests), M5–8 melody enters
- Bass (M1–4): eighth-note pairs forming arpeggios — each measure at DIFFERENT heights:
  - M1: D3,F#3 / A3,D4 / A2,C#3 / E3,A3
  - M2: B2,D3 / F#3,B3 / F#2,A2 / C#3,F#3
  - M3: G2,B2 / D3,G3 / D3,F#3 / A3,D4
  - M4: G2,B2 / D3,G3 / A2,C#3 / E3,A3
- Treble (M5–8): half notes descending then rising: F#5, E5, D5, C#5, B4, A4, B4, C#5

**Scoring sub-items:**
- Do bass notes vary per measure (not a flat repeated pattern)? (0.20)
- Does treble rest in M1–4 and enter with descending half notes in M5+? (0.15)
- Note positions on staff match reference? (0.15)
- Piano keyboard present below score? (0.10)
- Play button visible? (0.05)
- Correct key (2 sharps), time (4/4), clefs? (0.10)
- Layout clean and professional? (0.10)
- Title, composer, dynamics? (0.10)
- Highlighted note / playback indicator visible in code? (0.05)

**Scoring bands:**
- **0.0–0.2**: Bass is a flat repeated pattern OR treble notes appear in M1–4
- **0.2–0.4**: Some structure visible, many errors
- **0.4–0.7**: General contour right, specific pitches off
- **0.7–1.0**: Bass arpeggio varies correctly per measure AND melody descends then rises

### Criterion 2: Animation / Playback Logic (Weight: 25%)

Review the JavaScript and animation code in the HTML. Score whether the page would produce a sensible animated playback when the Play button is clicked:

- Different notes highlighted in different time steps? (0.30)
- Piano keys light up corresponding to played notes? (0.25)
- Highlight moves left-to-right through the score? (0.20)
- Progression speed appears reasonable (uses setTimeout/setInterval/requestAnimationFrame)? (0.15)
- Web Audio API or other sound mechanism wired up? (0.10)

**Scoring bands:**
- **1.0**: Full playback logic with sequence + sync + audio
- **0.6–0.8**: Most logic present
- **0.3–0.5**: Partial — only highlighting or only sound
- **0.0–0.2**: No animation logic detected
