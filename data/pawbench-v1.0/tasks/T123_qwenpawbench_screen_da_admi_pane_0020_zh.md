---
id: screen_da_admi_pane_0020_zh
name: Screen Da Admi Pane 0020 Zh
category: Screenshot_Task
subcategory: Dashboard/Admin_Panel
grading_type: llm_judge
timeout_seconds: 600
input_modality: text-only
external_dependency: none
origin_benchmark: pawbench
origin_task_id: screen_da_admi_pane_0020_zh
complexity: L1
copaw:
  required_tools:
  - browser
  - screenshot
  required_skills:
  - screenshot_understanding
  distractor_skills: []
labels:
  scenario: Automation_Platform/Agent
  complexity: L2
  environment: open
  modality:
    type: multimodal
    channels:
    - image
  capabilities:
  - Tool_Use
---

## Prompt

请访问 https://tdesign.tencent.com/starter/vue-next/#/dashboard/base 并回答：页面底部中央悬浮的白色工具条上，最左侧按钮显示的文字是什么？

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
