---
id: M101_chinese_food_identification_zh
name: 从图片识别陕北抿节
category: multimodal
grading_type: automated
timeout_seconds: 300
grading_weights:
  automated: 1.0
  llm_judge: 0.0
workspace_files:
- source: assets/T015_claweval_M101_chinese_food_identification_zh/fixtures/media/image.jpg
  dest: fixtures/media/image.jpg
labels:
  capabilities:
  - Tool_Use
  modality:
    type: multimodal
    channels:
    - image
  scenario: Knowledge/QA
  complexity: L1
  environment: closed
---
## Prompt

容器里有以下文件：
- `fixtures/media/image.jpg`

请先查看该图片，然后基于图片内容回答：**这是什么吃的？**

请将最终答案保存到 `output/answer.md`，并在最终回复中也输出答案。

## Expected Behavior

- 查看图片
- 识别食物为 **陕北抿节**（也称作"抿尖"或"抿节儿"）
- 简单介绍该食物（陕西省榆林市、延安市等地的传统特色面食）

## Grading Criteria

- [ ] 查看图片 (image_viewed)
- [ ] 答出抿节 / 抿尖 / 抿节儿 (food_identified)
- [ ] 使用别名可接受（抿节 / 抿尖 / 抿节儿）(alias_accepted)

## Automated Checks

```python
import re
from pathlib import Path


def grade(transcript: list, workspace_path: str) -> dict:
    """
    Mirrors original ImageQAOracleMixin formula exactly:
      image_loaded = 1.0 if image was viewed (proxy via transcript heuristic)
      answer_score = 1.0 if canonical answer or any alias found in final text; else 0.0
      score = 0.30 * image_loaded + 0.70 * answer_score

    Oracle: canonical="陕北抿节", aliases=["抿节", "抿尖", "抿节儿"]
    No partial credit for regional terms (unlike original, which returns 0.0).
    """

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

    output_path = Path(workspace_path) / "output" / "answer.md"
    file_content = ""
    if output_path.is_file():
        try:
            file_content = output_path.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            pass

    combined = transcript_text + " " + file_content

    # image_loaded proxy: in QwenClawBench, image is multimodal attachment, always loaded.
    # Use output file existence or food-related keywords as evidence of engagement.
    image_loaded = 1.0 if (
        output_path.is_file()
        or re.search(r"image\.jpg|fixtures/media|食物|面|noodle|food|识别", combined, re.IGNORECASE)
    ) else 0.0

    # answer_score: binary — canonical or alias must appear (no partial credit)
    CANONICAL = "陕北抿节"
    ALIASES = ["抿节", "抿尖", "抿节儿"]
    answer_score = 1.0 if re.search("|".join([CANONICAL] + ALIASES), combined) else 0.0

    score = round(0.30 * image_loaded + 0.70 * answer_score, 3)
    return {"score": score}
```

## LLM Judge Rubric

### Criterion: Food Identification (Weight: 100%)

This is an image-grounded identification task.

**Canonical answer**: 陕北抿节

**Accept these aliases as correct**: 抿节, 抿尖, 抿节儿

**Reference**: 陕北抿节（也写作"抿尖"或"抿节儿"），是陕西省榆林市、延安市等地的传统特色面食。

该任务在原始 claw-eval 中是 **oracle-based deterministic grading**（非 LLM 主导）：
- 以 canonical answer `陕北抿节` 及 aliases `抿节 / 抿尖 / 抿节儿` 为主要判定依据
- 是否成功读取图片作为附加信号

此处保留 rubric 仅用于文档说明，实际评分以 Automated Checks 为准。
