---
id: gui_002_zh
name: Gui 002 Zh
category: gui
grading_type: llm_judge
timeout_seconds: 300
input_modality: multimodal
external_dependency: none
origin_benchmark: pawbench
origin_task_id: gui_002_zh
complexity: L1
copaw:
  required_tools: []
  required_skills: []
  distractor_skills: []
labels:
  scenario: Automation_Platform/Agent
  complexity: L1
  environment: open
  modality:
    type: multimodal
    channels:
    - image
  capabilities:
  - Tool_Use
---

## Prompt

请打开浏览器当前窗口并截一张完整截图。

## Expected Behavior

The agent should fulfil the user request above using only appropriate tools and skills, and produce the requested artefact / answer.

## Grading Criteria

- Task is fully completed as requested
- Tool / skill usage is appropriate and efficient
- Final response is clear, accurate, and in the requested format

## LLM Judge Rubric

### task_completion (Weight: 50%)
- 1.0: Fully accomplishes the user's request (correct artefact, correct answer, correct preference recorded), no missing piece.
- 0.75: Mostly accomplishes the goal; minor omissions or imprecision.
- 0.5: Partial completion or correct intent but flawed execution.
- 0.25: Tries but fails most acceptance criteria.
- 0.0: Does not address the request.

### tool_skill_use (Weight: 30%)
- 1.0: Uses appropriate tools/skills with valid arguments and reacts to results.
- 0.75: Mostly appropriate with one wrong call or minor inefficiency.
- 0.5: Several wrong choices or wasted calls.
- 0.25: Tool use mostly incorrect or absent.
- 0.0: No meaningful tool interaction.

### output_quality (Weight: 20%)
- 1.0: Final response is clear, well-structured, in the requested language/format, and accurate.
- 0.75: Mostly clear with minor formatting or content gaps.
- 0.5: Understandable but incomplete or partially incorrect.
- 0.25: Confusing or off-topic response.
- 0.0: No usable final response.

Pass threshold: `total >= 0.6`.
