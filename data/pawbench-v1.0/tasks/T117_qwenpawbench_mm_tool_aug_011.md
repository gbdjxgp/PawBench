---
id: mm_tool_aug_011
name: Mm Tool Aug 011
category: Information_Retrieval
subcategory: Product_Research/Product_Comparison
grading_type: llm_judge
timeout_seconds: 1200
input_modality: text-only
external_dependency: none
workspace_files:
- source: assets/T117_qwenpawbench_mm_tool_aug_011/local_files/11.jpg
  dest: local_files/11.jpg
origin_benchmark: pawbench
origin_task_id: mm_tool_aug_011
complexity: L2
copaw:
  required_tools:
  - web_search
  - web_fetch
  required_skills: []
  distractor_skills: []
labels:
  scenario: Information_Retrieval/Market
  complexity: L2
  environment: open
  modality:
    type: multimodal
    channels:
    - image
  capabilities:
  - Tool_Use
  - Planning
---

## Prompt

请查看工作区里的图片 `local_files/11.jpg`，判断图片里这款车是什么型号？2025款落地价大概多少？油耗怎么样？

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
