---
id: CTB_W05_backup_chain_repair
name: Incremental Backup Chain Repair
category: terminal
grading_type: hybrid
timeout_seconds: 600
grading_weights:
  automated: 0.8
  llm_judge: 0.2
workspace_files:
- source: assets/T051_claweval_CTB_W05_backup_chain_repair/project/backups/snapshot.index.json
  dest: project/backups/snapshot.index.json
- source: assets/T051_claweval_CTB_W05_backup_chain_repair/project/backups/snapshots/base_20260310/manifest.json
  dest: project/backups/snapshots/base_20260310/manifest.json
- source: assets/T051_claweval_CTB_W05_backup_chain_repair/project/backups/snapshots/base_20260310/payloads/app_config_v1.yml
  dest: project/backups/snapshots/base_20260310/payloads/app_config_v1.yml
- source: assets/T051_claweval_CTB_W05_backup_chain_repair/project/backups/snapshots/base_20260310/payloads/customers_base.csv
  dest: project/backups/snapshots/base_20260310/payloads/customers_base.csv
- source: assets/T051_claweval_CTB_W05_backup_chain_repair/project/backups/snapshots/inc_20260311/manifest.json
  dest: project/backups/snapshots/inc_20260311/manifest.json
- source: assets/T051_claweval_CTB_W05_backup_chain_repair/project/backups/snapshots/inc_20260311/payloads/app_config_v2.yml
  dest: project/backups/snapshots/inc_20260311/payloads/app_config_v2.yml
- source: assets/T051_claweval_CTB_W05_backup_chain_repair/project/backups/snapshots/inc_20260311/payloads/daily_20260311.csv
  dest: project/backups/snapshots/inc_20260311/payloads/daily_20260311.csv
- source: assets/T051_claweval_CTB_W05_backup_chain_repair/project/backups/snapshots/inc_20260312/manifest.json
  dest: project/backups/snapshots/inc_20260312/manifest.json
- source: assets/T051_claweval_CTB_W05_backup_chain_repair/project/backups/snapshots/inc_20260312/payloads/daily_20260312.csv
  dest: project/backups/snapshots/inc_20260312/payloads/daily_20260312.csv
- source: assets/T051_claweval_CTB_W05_backup_chain_repair/project/backups/snapshots/inc_20260312/payloads/latest_summary.txt
  dest: project/backups/snapshots/inc_20260312/payloads/latest_summary.txt
- source: assets/T051_claweval_CTB_W05_backup_chain_repair/project/scripts/chain_probe.py
  dest: project/scripts/chain_probe.py
labels:
  complexity: L3
  environment: open
  capabilities:
  - Logic_Reasoning
  - Tool_Use
  - Planning
  - Self_Verification
  scenario: Software_Engineering/DevOps
  modality:
    type: text
    channels: []
---
## Prompt

Workspace files:
- `project/backups/snapshot.index.json`
- `project/backups/snapshots/base_20260310/manifest.json`
- `project/backups/snapshots/inc_20260311/manifest.json`
- `project/backups/snapshots/inc_20260312/manifest.json`
- `project/scripts/chain_probe.py`

The most recent incremental backup verification has failed. Your tasks:
1. Start by inspecting the index, manifests, and payload files to determine the **true root cause** — do not just look at the last error message.
2. Fix only the necessary backup metadata so the latest snapshot chain is restorable again.
3. Do **not** modify any payload data files.
4. Do **not** modify `chain_probe.py`.
5. Run `python project/scripts/chain_probe.py` from the workspace root and make sure it outputs `CHAIN_OK` and writes `output/backup_restore_probe.json`.
6. Write a report at `BACKUP_REPAIR.md` (in the workspace root) explaining:
   - The true root cause.
   - Which errors were merely symptoms.
   - What index/metadata changes you made.
   - How you verified the fix.

Constraints:
- Limit your changes to `project/backups/snapshot.index.json` as much as possible.
- Do not modify any log files (if any exist).
- Do not fabricate recovery results.

## Expected Behavior

1. Inspect `snapshot.index.json` and observe that `inc_20260312.parent` is incorrectly set to `base_20260310`.
2. Restoring through that parent chain skips `inc_20260311` and therefore loses:
   - `app/config.yml` v2 revision (only present in `inc_20260311/payloads/app_config_v2.yml`).
   - `reports/daily_20260311.csv` (only present in `inc_20260311`).
3. Fix: change `inc_20260312.parent` from `base_20260310` to `inc_20260311`.
4. Run `python project/scripts/chain_probe.py` and verify it prints `CHAIN_OK` and writes `output/backup_restore_probe.json` with:
   ```json
   {
     "latest_snapshot_id": "inc_20260312",
     "restored_files": [
       "app/config.yml",
       "data/customers.csv",
       "exports/latest_summary.txt",
       "reports/daily_20260311.csv",
       "reports/daily_20260312.csv"
     ],
     "config_revision": "v2",
     "status": "healthy"
   }
   ```
5. Author `BACKUP_REPAIR.md` with the root cause, symptoms, fix, and verification.

## Grading Criteria

- [ ] `snapshot.index.json` has `inc_20260312.parent == "inc_20260311"` (`parent_link_ok`).
- [ ] `inc_20260311.parent == "base_20260310"` (`middle_link_ok`).
- [ ] `base_20260310.parent` is null (`base_root_ok`).
- [ ] `latest_snapshot_id == "inc_20260312"` (`latest_snapshot_ok`).
- [ ] `output/backup_restore_probe.json` exists and matches the expected structure (`restore_probe_ok`).
- [ ] `BACKUP_REPAIR.md` exists with key root-cause keywords (`report_keywords_ok`).
- [ ] LLM judge grades the explanation quality.

## Automated Checks

```python
import json
import re
from pathlib import Path


def grade(transcript: list, workspace_path: str) -> dict:
    result = {
        "latest_snapshot_ok": 0.0,
        "parent_link_ok": 0.0,
        "middle_link_ok": 0.0,
        "base_root_ok": 0.0,
        "manifest_paths_ok": 0.0,
        "restore_probe_ok": 0.0,
        "report_exists": 0.0,
        "report_keywords_ok": 0.0,
    }

    workspace = Path(workspace_path)
    index_path = workspace / "project" / "backups" / "snapshot.index.json"
    probe_path = workspace / "output" / "backup_restore_probe.json"
    report_path = workspace / "BACKUP_REPAIR.md"

    try:
        index = json.loads(index_path.read_text())
    except Exception:
        index = {}

    snapshots = {snap.get("snapshot_id"): snap for snap in index.get("snapshots", [])}
    latest = index.get("latest_snapshot_id")

    if latest == "inc_20260312":
        result["latest_snapshot_ok"] = 1.0
    if (snapshots.get("inc_20260312") or {}).get("parent") == "inc_20260311":
        result["parent_link_ok"] = 1.0
    if (snapshots.get("inc_20260311") or {}).get("parent") == "base_20260310":
        result["middle_link_ok"] = 1.0
    if (snapshots.get("base_20260310") or {}).get("parent") is None:
        result["base_root_ok"] = 1.0
    if all(
        isinstance((snapshots.get(sid) or {}).get("manifest"), str)
        for sid in ["base_20260310", "inc_20260311", "inc_20260312"]
    ):
        result["manifest_paths_ok"] = 1.0

    if probe_path.is_file():
        try:
            probe = json.loads(probe_path.read_text())
            expected_files = {
                "app/config.yml",
                "data/customers.csv",
                "exports/latest_summary.txt",
                "reports/daily_20260311.csv",
                "reports/daily_20260312.csv",
            }
            # Order-independent comparison: chain_probe.py emits the file list
            # from its own internal ``required_files`` list, so any agent that
            # correctly fixes the chain will produce the same *set* of paths.
            # Comparing as a list (probe == expected) is brittle because the
            # script's hard-coded order and the upstream task author's expected
            # order diverged.
            files_ok = (
                isinstance(probe.get("restored_files"), list)
                and set(probe["restored_files"]) == expected_files
            )
            meta_ok = (
                probe.get("latest_snapshot_id") == "inc_20260312"
                and probe.get("config_revision") == "v2"
                and probe.get("status") == "healthy"
            )
            if files_ok and meta_ok:
                result["restore_probe_ok"] = 1.0
            elif files_ok or meta_ok:
                result["restore_probe_ok"] = 0.5
        except Exception:
            pass

    if report_path.is_file():
        try:
            text = report_path.read_text()
            result["report_exists"] = 1.0
            lower_text = text.lower()
            must_have = [
                "root cause", "根因",
                "snapshot.index.json",
                "inc_20260312", "inc_20260311",
                "daily_20260311",
                "hash mismatch",
                "表象", "验证",
            ]
            hits = sum(1 for kw in must_have if kw.lower() in lower_text)
            if hits >= 5 and len(text) >= 140:
                result["report_keywords_ok"] = 1.0
            elif hits >= 3:
                result["report_keywords_ok"] = 0.5
        except Exception:
            pass

    return result
```

## LLM Judge Rubric

### Criterion 1: Root-Cause Explanation Quality (Weight: 100%)

Evaluate the `BACKUP_REPAIR.md` write-up (or final assistant message if the file is missing).

**Expected content:**
- Identifies that the root cause is a broken `parent` reference in `snapshot.index.json` (specifically `inc_20260312.parent` was wrongly set to `base_20260310` instead of `inc_20260311`).
- Distinguishes the *symptoms* (missing `daily_20260311.csv`, "config hash mismatch" / old `revision: v1` restored) from the *root cause*.
- Clearly states the metadata change made (parent reference flip) and that no payload was modified.
- Mentions the verification step: rerunning `chain_probe.py` and seeing `CHAIN_OK`.

**Scoring bands:**
- **0.9-1.0**: All four points covered; root cause clearly distinguished from symptoms; concrete keys (`inc_20260312`, `inc_20260311`, `parent`, `daily_20260311`, `revision: v2`) cited; verification described.
- **0.7-0.8**: Root cause and fix clear; symptoms vs root cause separation present; minor omissions.
- **0.5-0.6**: Identifies the parent-link issue but missing the symptom-vs-cause distinction or the verification step.
- **0.3-0.4**: Vague description; mentions snapshot.index.json but does not explain the chain logic.
- **0.0-0.2**: Wrong root cause, fabricated fix, or no usable explanation.
