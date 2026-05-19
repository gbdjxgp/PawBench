---
id: 05_Creative_Synthesis_task_10_social_poster_multi_crop
name: Social Media Poster Smart Crop for Multi-Platform
category: 05_Creative_Synthesis
grading_type: hybrid
timeout_seconds: 600
grading_weights:
  automated: 0.7
  llm_judge: 0.3
workspace_files:
- source: assets/T146_wildclawbench_05_social_poster_multi_crop/poster_original.png
  dest: poster_original.png
labels:
  complexity: L2
  environment: closed
  modality:
    type: multimodal
    channels:
    - image
  scenario: Content_Creation/Design
  capabilities:
  - Code_Manipulation
  - Math_Computation
  - Tool_Use
  - Planning
  - Self_Verification
  - Logic_Reasoning
---
## Prompt

工作目录下有一张社交媒体宣传海报 `poster_original.png`。

请针对以下社交媒体平台的发布规范，对这张海报进行智能裁切，输出三个适配版本到 `output/` 目录：

| 文件名 | 适配平台 | 宽高比 |
|--------|----------|--------|
| `output/crop_ins_square.png` | Instagram 正方形信息流帖子 | 1:1 |
| `output/crop_tiktok.png` | TikTok / Instagram Reels 全屏竖版 | 9:16 |
| `output/crop_ins_portrait.png` | Instagram 竖版帖子（Portrait） | 4:5 |

要求：
1. 三个文件均须生成（> 1KB），宽高比与平台标准比例精确匹配（允许 2% 误差）
2. 主体视觉焦点应尽量保留在裁切窗口内
3. 边缘裁切自然，构图美观

如需图像理解能力，可调用多模态 API（base_url 通过环境变量 `JUDGE_BASE_URL` 获取，API Key 通过环境变量 `JUDGE_API_KEY` 获取，模型通过 `JUDGE_VLM_MODEL` 获取，默认 `qwen-vl-max`）。

## Expected Behavior

理想情况下，agent 会：

1. 用 PIL 加载海报（1200×1500），观察主体位置（橙色圆形居中、文字带在上下边缘）。
2. 自主确定各平台对应的标准宽高比，意识到不同比例需要不同裁切策略——尤其是 TikTok 全屏竖版（9:16），通常需要主动取舍。
3. 编写智能裁切脚本，针对每种比例选出相对最优、且观感自然的裁切窗口。
4. 确保所有输出文件比例精确（误差 ≤ 2%）、画质清晰。

## Grading Criteria

- [ ] 三个裁切文件均已生成（> 1KB），且宽高比与对应平台标准比例精确匹配（允许 2% 误差）
- [ ] 每个裁切版本中，原图主要视觉主体仍清晰可辨（VLM 对比原图评估）
- [ ] 每个裁切版本的画面构图美观、边缘裁切自然（VLM 评估）

## Automated Checks

```python
import base64
import json
import os
import re
import time
from pathlib import Path


def grade(transcript: list, workspace_path: str) -> dict:
    EXPECTED = {
        "crop_ins_square.png": {"ratio": 1.0, "tol": 0.02},
        "crop_tiktok.png": {"ratio": 9 / 16, "tol": 0.02},
        "crop_ins_portrait.png": {"ratio": 4 / 5, "tol": 0.02},
    }

    output_dir = Path(workspace_path) / "output"
    original_poster = Path(workspace_path) / "poster_original.png"

    try:
        from PIL import Image
    except ImportError:
        return {"overall_score": 0.0}

    found = {}
    ratio_ok = 0
    for fname, spec in EXPECTED.items():
        base = fname.rsplit(".", 1)[0]
        for ext in ("png", "jpg", "jpeg", "webp"):
            p = output_dir / f"{base}.{ext}"
            if p.exists() and p.stat().st_size > 1000:
                found[fname] = p
                try:
                    with Image.open(p) as img:
                        w, h = img.size
                        if h > 0 and abs((w / h) - spec["ratio"]) <= spec["tol"]:
                            ratio_ok += 1
                except Exception:
                    pass
                break

    files_ok = 1.0 if len(found) == 3 else 0.0
    ratios_ok = 1.0 if ratio_ok == 3 else 0.0
    basic_requirements = 1.0 if files_ok and ratios_ok else round((files_ok + ratios_ok) / 2, 2)
    if basic_requirements < 1.0:
        return {"overall_score": 0.0}

    # Prefer JUDGE_* env vars (DashScope-compatible), fall back to OPENROUTER_*.
    api_key = (
        os.environ.get("JUDGE_API_KEY", "")
        or os.environ.get("OPENROUTER_API_KEY", "")
    )
    api_base = (
        os.environ.get("JUDGE_BASE_URL", "")
        or os.environ.get("OPENROUTER_BASE_URL", "")
    )
    # Use a dedicated VLM model env var; JUDGE_MODEL may be a text-only model.
    vlm_model = os.environ.get("JUDGE_VLM_MODEL") or os.environ.get("JUDGE_MODEL", "qwen-vl-max")
    if not api_key or not api_base:
        # Keep objective checks if VLM env is unavailable.
        return {"overall_score": 0.5}

    try:
        from openai import OpenAI
    except Exception:
        return {"overall_score": 0.5}

    client = OpenAI(api_key=api_key, base_url=api_base)

    def _call_vlm(messages, retries=2):
        for attempt in range(retries + 1):
            try:
                resp = client.chat.completions.create(
                    model=vlm_model,
                    messages=messages,
                    max_tokens=512,
                    temperature=0,
                )
                return (resp.choices[0].message.content or "").strip()
            except Exception:
                if attempt < retries:
                    time.sleep(2 ** attempt)
                else:
                    return ""

    def _extract_json(text):
        if not text:
            return None
        m = re.search(r"`{3}(?:json)?\s*\n?(.*?)\n?`{3}", text, re.DOTALL)
        if m:
            text = m.group(1)
        try:
            return json.loads(text)
        except Exception:
            m2 = re.search(r"\{.*\}", text, re.DOTALL)
            if not m2:
                return None
            try:
                return json.loads(m2.group(0))
            except Exception:
                return None

    def _img_b64(path):
        try:
            return base64.b64encode(path.read_bytes()).decode("utf-8")
        except Exception:
            return None

    def _mime(path):
        ext = path.suffix.lower()
        return {
            ".png": "image/png",
            ".jpg": "image/jpeg",
            ".jpeg": "image/jpeg",
            ".webp": "image/webp",
        }.get(ext, "image/png")

    orig_b64 = _img_b64(original_poster) if original_poster.exists() else None
    if not orig_b64:
        return {"overall_score": 0.5}

    subject_scores = []
    quality_scores = []
    for fname in EXPECTED:
        crop = found.get(fname)
        crop_b64 = _img_b64(crop) if crop else None
        if not crop_b64:
            subject_scores.append(0.0)
            quality_scores.append(0.0)
            continue

        subject_prompt = [
            {"role": "user", "content": [
                {"type": "text", "text": "Image1 is original poster, Image2 is cropped version. Score whether the main visual subject is preserved. Return JSON only: {\"subject_score\": 0.0-1.0}"},
                {"type": "image_url", "image_url": {"url": f"data:{_mime(original_poster)};base64,{orig_b64}"}},
                {"type": "image_url", "image_url": {"url": f"data:{_mime(crop)};base64,{crop_b64}"}},
            ]}
        ]
        subject_data = _extract_json(_call_vlm(subject_prompt)) or {}
        subject_scores.append(float(subject_data.get("subject_score", 0.0) or 0.0))

        quality_prompt = [
            {"role": "user", "content": [
                {"type": "text", "text": "Rate composition and crop naturalness for this social poster crop. Return JSON only: {\"aesthetic_score\": 0.0-1.0}"},
                {"type": "image_url", "image_url": {"url": f"data:{_mime(crop)};base64,{crop_b64}"}},
            ]}
        ]
        quality_data = _extract_json(_call_vlm(quality_prompt)) or {}
        quality_scores.append(float(quality_data.get("aesthetic_score", 0.0) or 0.0))

    subject_preserved = max(0.0, min(1.0, sum(subject_scores) / 3))
    visual_quality = max(0.0, min(1.0, sum(quality_scores) / 3))
    overall = round((subject_preserved + 2 * visual_quality) / 3, 4)
    return {"overall_score": overall}
```

## LLM Judge Rubric

### Criterion 1: Crop Strategy Quality (Weight: 60%)

Evaluate whether the agent demonstrated thoughtful crop strategy:

**Scoring:**
- **1.0**: Used PIL to inspect the poster, computed center-based crop windows, used resampling for quality, and produced exact-ratio outputs (1:1, 9:16, 4:5) with the central subject preserved.
- **0.7–0.8**: Produced 2–3 valid crops but used naive crop (e.g., just resize) for some.
- **0.4–0.6**: Only 1 valid crop, or all crops have wrong aspect ratio.
- **0.0–0.3**: No outputs or all outputs malformed.

### Criterion 2: Output File Quality (Weight: 40%)

Evaluate the agent's reasoning about per-platform requirements:

**Scoring:**
- **1.0**: Explicitly identified each platform's standard ratio (Instagram 1:1, TikTok/Reels 9:16, Instagram Portrait 4:5) and explained crop choice for each.
- **0.6–0.8**: Mentioned ratios but no per-platform reasoning.
- **0.0–0.4**: No reasoning about ratios.
