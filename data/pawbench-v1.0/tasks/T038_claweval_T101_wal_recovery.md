---
id: T101_wal_recovery
name: SQLite WAL File Recovery
category: terminal
grading_type: automated
timeout_seconds: 1200
workspace_files:
- source: assets/T038_claweval_T101_wal_recovery/fixtures/test.db
  dest: fixtures/test.db
- source: assets/T038_claweval_T101_wal_recovery/fixtures/test.db-wal
  dest: fixtures/test.db-wal
labels:
  capabilities:
  - Logic_Reasoning
  - Tool_Use
  - Planning
  - Self_Verification
  modality:
    type: text
  scenario: Software_Engineering/Database
  complexity: L3
  environment: closed
---
## Prompt

Workspace files:
- `fixtures/test.db` — SQLite database in WAL mode
- `fixtures/test.db-wal` — WAL (Write-Ahead Logging) file, appears corrupted

The database **should** contain 11 records total, but a normal `SELECT * FROM items` on `test.db` returns only 5 base records. The WAL file contains updates to 2 existing records and 6 new inserts, but SQLite refuses to apply the WAL frames because of a salt mismatch (likely XOR'd corruption of frame salts).

Your task is to:
1. Diagnose why SQLite ignores the WAL frames
2. Fix the WAL file (`fixtures/test.db-wal`) so SQLite can read all frames
3. Verify the database now returns all 11 records
4. Write `output/recovered.json` containing all 11 records, format:
   ```json
   [{"id": 1, "name": "...", "value": N.N}, ...]
   ```
   sorted by `id`. Records 1 and 2 should reflect the **updated** values from the WAL.

5. Save a brief explanation of the corruption and your fix to `output/recovery_writeup.md`.

## Expected Behavior

- The WAL header has salt1/salt2 at bytes 16-23
- Each frame header has salt1/salt2 at bytes 8-15
- Frame salts should match WAL header salts (corruption: frame salts XOR'd with `0xDEADBEEF`)
- Fix: copy WAL-header salts into each frame header's salt fields (no checksum recalc needed)
- After fix, querying `items` returns 11 rows; records 1 & 2 have updated values

## Grading Criteria

- [ ] `output/recovered.json` exists (output_file_exists)
- [ ] Contains 11 records (record_count_correct)
- [ ] Records sorted by id (sorted)
- [ ] DB now returns 11 rows when queried directly (wal_fixed)
- [ ] Records 1, 2 reflect updated values (records_1_2_updated)
- [ ] Write-up `output/recovery_writeup.md` exists (writeup_exists)

## Automated Checks

```python
import json
import sqlite3
from pathlib import Path


def grade(transcript: list, workspace_path: str) -> dict:
    result = {
        "output_file_exists": 0.0,
        "record_count_correct": 0.0,
        "sorted": 0.0,
        "wal_fixed": 0.0,
        "records_1_2_updated": 0.0,
        "writeup_exists": 0.0,
    }

    workspace = Path(workspace_path)
    recovered = workspace / "output" / "recovered.json"
    db_path = workspace / "fixtures" / "test.db"
    writeup = workspace / "output" / "recovery_writeup.md"

    if writeup.is_file():
        result["writeup_exists"] = 1.0

    records = None
    if recovered.is_file():
        result["output_file_exists"] = 1.0
        try:
            records = json.loads(recovered.read_text(encoding="utf-8"))
        except Exception:
            pass

    record_count = 0
    if isinstance(records, list):
        record_count = len(records)
        if record_count == 11:
            result["record_count_correct"] = 1.0
        elif record_count >= 8:
            result["record_count_correct"] = 0.7
        elif record_count >= 5:
            result["record_count_correct"] = 0.4

        ids = [r.get("id") for r in records if isinstance(r, dict)]
        if ids and ids == sorted([i for i in ids if isinstance(i, int)]):
            result["sorted"] = 1.0

        for r in records:
            if not isinstance(r, dict):
                continue
            if r.get("id") == 1 and abs(float(r.get("value", 0)) - 99.9) < 0.01:
                result["records_1_2_updated"] += 0.5
            if r.get("id") == 2 and abs(float(r.get("value", 0)) - 88.8) < 0.01:
                result["records_1_2_updated"] += 0.5

    if db_path.is_file():
        try:
            conn = sqlite3.connect(str(db_path))
            row_count_db = len(conn.execute("SELECT * FROM items").fetchall())
            conn.close()
            if row_count_db == 11:
                result["wal_fixed"] = 1.0
            elif row_count_db > 5:
                result["wal_fixed"] = (row_count_db - 5) / 6
        except Exception:
            pass

    # Cap: if record count in recovered.json < 8, WAL was not meaningfully fixed
    # → zero out wal_fixed and updated-values scores (same logic as original cap at 0.40)
    if record_count < 8:
        result["wal_fixed"] = 0.0
        result["records_1_2_updated"] = 0.0

    return result
```

## Reference: Write-up Quality Criteria (for human review only)

The `output/recovery_writeup.md` should ideally:
- Identify the SQLite WAL header / frame header structure (32-byte header + 24-byte frame headers)
- Explain the salt mismatch (frame salts vs header salts) as the root cause
- Mention the XOR / corruption pattern (`0xDEADBEEF`)
- Describe the fix (copy header salts into each frame's salt fields)
- Confirm the resulting 11-row recovery, including the two updates (id=1 → 99.9, id=2 → 88.8)

*(This section is documentation only — scoring is 100% automated via the grade() function above.)*
