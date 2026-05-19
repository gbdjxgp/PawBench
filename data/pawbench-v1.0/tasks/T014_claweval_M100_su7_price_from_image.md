---
id: M100_su7_price_from_image
name: Estimate Xiaomi SU7 Price From Image
category: multimodal
grading_type: hybrid
timeout_seconds: 600
grading_weights:
  automated: 0.3
  llm_judge: 0.7
workspace_files:
- source: assets/T014_claweval_M100_su7_price_from_image/fixtures/media/su7_image_old.jpg
  dest: fixtures/media/su7_image_old.jpg
labels:
  capabilities:
  - Tool_Use
  - Logic_Reasoning
  modality:
    type: multimodal
    channels:
    - image
  scenario: Knowledge/QA
  complexity: L2
  environment: closed
---
## Prompt

The workspace contains:
- `fixtures/media/su7_image_old.jpg` — a car photo

Please first view the image, then answer: **How much does this car sell for now?**

If exact pricing is uncertain, provide a **plausible range** and explain why.

Save the final answer to `output/answer.md` and also state it in your final reply.

## Expected Behavior

- View the image
- Identify the car as **Xiaomi SU7** (launch era / old model)
- Give plausible launch trim prices:
  - Standard ≈ 215,900 CNY (¥21.59万)
  - Pro ≈ 245,900 CNY (¥24.59万)
  - Max ≈ 299,900 CNY (¥29.99万)
- Explain uncertainty from trim/year/used vs new market

## Grading Criteria

- [ ] Image viewed (image_viewed)
- [ ] Identified as Xiaomi SU7 (su7_identified)
- [ ] Provides price range (price_range)
- [ ] Mentions multiple trims (versions_mentioned)
- [ ] Acknowledges uncertainty (uncertainty_explained)
- [ ] Output file exists (output_file_exists)

## Automated Checks

```python
import re
from pathlib import Path


def grade(transcript: list, workspace_path: str) -> dict:
    """
    Mirrors original SU7PriceFromImageGrader formula exactly:
      score = 0.70 * judge + 0.30 * image_loaded
    The automated check is ONLY image_loaded (binary: did the agent view the image?).
    All content evaluation (car identification, price range, etc.) is handled by the LLM judge.
    """

    def _all_text(msgs):
        parts = []
        for m in msgs:
            actual = m.get("message", m)
            if actual.get("role") not in ("assistant",):
                continue
            c = actual.get("content", "")
            if isinstance(c, str):
                parts.append(c)
            elif isinstance(c, list):
                for b in c:
                    if isinstance(b, dict):
                        parts.append(b.get("text", ""))
        return " ".join(parts)

    transcript_text = _all_text(transcript)

    output_path = Path(workspace_path) / "output" / "answer.md"
    file_content = ""
    if output_path.is_file():
        try:
            file_content = output_path.read_text(encoding="utf-8")
        except Exception:
            pass

    combined = transcript_text + " " + file_content

    # image_loaded proxy:
    # Original used media_events; in QwenClawBench the image is a multimodal attachment.
    # Agent engagement is evidenced by output file existence or SU7-related content.
    image_loaded = 1.0 if (
        output_path.is_file()
        or re.search(r"su7|xiaomi|price|price range|万元|SU7", combined, re.IGNORECASE)
    ) else 0.0

    return {"image_loaded": image_loaded}
```

## LLM Judge Rubric

### Criterion: Car Identification + Price Plausibility (Weight: 100%)

Evaluate whether the assistant correctly identified the car and provided a plausible price range.

**Correct answer**: image shows a **Xiaomi SU7** (launch era / old model).

**Key facts the response should contain:**
- Car model: Xiaomi SU7
- Price range: approximately 215,900 CNY (Standard) / 245,900 CNY (Pro) / 299,900 CNY (Max)
- Uncertainty handling: acknowledges trim/version/year ambiguity, avoids overclaiming exact price from image alone

**Scoring bands:**
- **0.90–1.00**: Correctly identifies Xiaomi SU7, gives realistic price range, explains uncertainty
- **0.70–0.89**: Correct model and approximate price with minor gaps
- **0.40–0.69**: Identifies car but price range is vague or no uncertainty
- **0.00–0.39**: Wrong model, wildly incorrect price, or no meaningful answer
