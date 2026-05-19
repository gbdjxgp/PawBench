---
id: M099_su7_price_from_image_zh
name: 从图片判断小米SU7价格
category: multimodal
grading_type: hybrid
timeout_seconds: 600
grading_weights:
  automated: 0.3
  llm_judge: 0.7
workspace_files:
- source: assets/T013_claweval_M099_su7_price_from_image_zh/fixtures/media/su7_image_old.jpg
  dest: fixtures/media/su7_image_old.jpg
labels:
  capabilities:
  - Logic_Reasoning
  - Tool_Use
  modality:
    type: multimodal
    channels:
    - image
  scenario: Knowledge/QA
  complexity: L3
  environment: closed
---
## Prompt

容器里有以下文件：
- `fixtures/media/su7_image_old.jpg` — 一张汽车图片

请先查看该图片，然后回答：**现在这车卖多少钱？**

请基于图片内容回答。如果无法确定精确价格，请给出**合理价格区间**并说明**不确定性来源**。

请将最终答案保存到 `output/answer.md`，并在最终回复中也输出。

## Expected Behavior

- 查看图片
- 识别车辆为**小米SU7**（图片为老款 / 上市时期版本）
- 给出价格区间：
  - 标准版约 21.59 万元
  - Pro 版约 24.59 万元
  - Max 版约 29.99 万元
- 说明不确定性（配置、年份、二手市场差异）

## Grading Criteria

- [ ] 查看图片 (image_viewed)
- [ ] 识别为小米 SU7 (su7_identified)
- [ ] 提供价格区间 (price_range)
- [ ] 提到三个版本 (versions_mentioned)
- [ ] 说明不确定性 (uncertainty_explained)
- [ ] 输出文件存在 (output_file_exists)

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
    # Original used media_events to detect actual image load.
    # In QwenClawBench, the image is embedded as multimodal attachment in the initial message,
    # so the agent always "sees" it — image_loaded = 1.0 if agent engaged with the task.
    image_loaded = 1.0 if (
        output_path.is_file()
        or re.search(r"su7|小米|xiaomi|价格|万元|price|SU7", combined, re.IGNORECASE)
    ) else 0.0

    return {"image_loaded": image_loaded}
```

## LLM Judge Rubric

### Criterion: Identification + Price Plausibility (Weight: 100%)

Evaluate whether the assistant correctly identified the car and provided a plausible price range.

**Correct answer**: image shows a **Xiaomi SU7** (老款 / launch era).

**Key facts the response should contain:**
- 车型: Xiaomi SU7 (小米SU7)
- 价格区间: 约 21.59 万元 (Standard) / 24.59 万元 (Pro) / 29.99 万元 (Max)
- 不确定性: 承认配置/版本/年份模糊，避免仅凭图片就报精确价格

**Scoring bands:**
- **0.90–1.00**: Correctly identifies Xiaomi SU7, gives realistic price range, explains uncertainty
- **0.70–0.89**: Correct model and approximate price with minor gaps
- **0.40–0.69**: Identifies car but price range is vague or no uncertainty handling
- **0.00–0.39**: Wrong model, wildly incorrect price, or no meaningful answer
