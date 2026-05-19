---
id: T103_schema_migration
name: SQLite Schema Migration
category: terminal
grading_type: automated
timeout_seconds: 600
workspace_files:
- source: assets/T039_claweval_T103_schema_migration/fixtures/old_schema.sql
  dest: fixtures/old_schema.sql
- source: assets/T039_claweval_T103_schema_migration/fixtures/new_schema.sql
  dest: fixtures/new_schema.sql
- source: assets/T039_claweval_T103_schema_migration/fixtures/test_data.db
  dest: fixtures/test_data.db
labels:
  capabilities:
  - Code_Manipulation
  - Tool_Use
  - Logic_Reasoning
  - Self_Verification
  modality:
    type: text
    channels: []
  scenario: Software_Engineering/Database
  complexity: L3
  environment: closed
---
## Prompt

Workspace files:
- `fixtures/old_schema.sql` — current (legacy) database schema
- `fixtures/new_schema.sql` — target schema
- `fixtures/test_data.db` — SQLite database with legacy data

Write `output/migrate_data.py` that transforms `fixtures/test_data.db` from the old schema to the new schema (write the migrated database to `output/migrated.db`). The migrated database must:

- Match the new schema exactly
- Preserve all data correctly
- Handle data quality issues to satisfy the new schema constraints

Then **execute** your migration so that `output/migrated.db` exists.

Also save a short write-up to `output/migration_writeup.md` describing each data-quality fix you applied.

## Expected Behavior

The agent must discover and handle these edge cases:
1. Case-insensitive email dedup (e.g. users 1, 3, 9 → same `alice@example.com`)
2. Whitespace in emails (trim)
3. Inconsistent role casing → normalize to lowercase
4. NULL/empty `full_name` → `Anonymous` for profiles
5. NULL `created_at` → provide valid value
6. Sub-cent / NULL prices → 0
7. Whitespace in category names → trim
8. Negative / zero quantities → 1
9. NULL `ordered_at` → valid value
10. Mixed-case status → normalize before mapping
11. Out-of-range ratings → clamp to [1,5]
12. NULL ratings → default 3; NULL `reviewed_at` → valid value
13. FK remapping for deduped users (orders/reviews/audit_log)
14. Table split: `users` → `accounts` + `profiles`
15. Table rename: `audit_log` → `activity_log`

## Grading Criteria

- [ ] `output/migrate_data.py` exists and is valid Python (script_valid)
- [ ] `output/migrated.db` exists (migrated_db_exists)
- [ ] New tables present: `accounts`, `profiles`, `activity_log` (schema_score)
- [ ] Data integrity checks pass (data_score)
- [ ] Write-up `output/migration_writeup.md` exists (writeup_exists)

## Automated Checks

```python
import sqlite3
import py_compile
from pathlib import Path


def grade(transcript: list, workspace_path: str) -> dict:
    result = {
        "script_valid": 0.0,
        "migrated_db_exists": 0.0,
        "schema_score": 0.0,
        "data_score": 0.0,
        "writeup_exists": 0.0,
    }

    workspace = Path(workspace_path)
    script = workspace / "output" / "migrate_data.py"
    migrated = workspace / "output" / "migrated.db"
    writeup = workspace / "output" / "migration_writeup.md"

    if writeup.is_file():
        result["writeup_exists"] = 1.0

    script_valid = False
    if script.is_file():
        try:
            py_compile.compile(str(script), doraise=True)
            result["script_valid"] = 1.0
            script_valid = True
        except Exception:
            result["script_valid"] = 0.5

    # Cap: if script has syntax errors, migrated DB cannot be trustworthy
    if not script_valid:
        return result

    if not migrated.is_file():
        return result
    result["migrated_db_exists"] = 1.0

    data_passed = 0
    data_total = 5
    try:
        conn = sqlite3.connect(str(migrated))
        cur = conn.cursor()
        tables = {r[0] for r in cur.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()}

        expected_tables = {"accounts", "profiles", "activity_log"}
        schema_hits = len(expected_tables & tables)
        result["schema_score"] = schema_hits / len(expected_tables)

        data_checks = []
        try:
            row = cur.execute("SELECT COUNT(*) FROM accounts").fetchone()
            data_checks.append(bool(row and row[0] > 0))
        except Exception:
            data_checks.append(False)
        try:
            rows = cur.execute("SELECT email FROM accounts").fetchall()
            emails = [r[0] for r in rows if r[0] is not None]
            distinct_lower = {e.strip().lower() for e in emails}
            data_checks.append(len(emails) == len(distinct_lower))
        except Exception:
            data_checks.append(False)
        try:
            rows = cur.execute("SELECT email FROM accounts").fetchall()
            data_checks.append(all(e[0] == e[0].strip() for e in rows if e[0]))
        except Exception:
            data_checks.append(False)
        try:
            row = cur.execute("SELECT COUNT(*) FROM profiles WHERE full_name IS NULL OR full_name = ''").fetchone()
            data_checks.append(row and row[0] == 0)
        except Exception:
            data_checks.append(False)
        try:
            row = cur.execute("SELECT COUNT(*) FROM activity_log").fetchone()
            data_checks.append(bool(row and row[0] >= 0))
        except Exception:
            data_checks.append(False)

        data_passed = sum(1 for c in data_checks if c)
        result["data_score"] = data_passed / len(data_checks)
        conn.close()
    except Exception:
        pass

    # Cap: if data integrity score < 1/3 (analogous to original data_score < 5/15),
    # schema score is meaningless — zero it out
    if result["data_score"] < (1 / 3):
        result["schema_score"] = 0.0

    return result
```

## Reference: Write-up Quality Criteria (for human review only)

The `output/migration_writeup.md` should ideally:
- List each significant data-quality fix applied (dedup, trimming, normalization, defaults, FK remapping)
- Mention schema-level changes (`users` → `accounts` + `profiles`; `audit_log` → `activity_log`)
- Explain FK remapping for deduped users
- Briefly justify the choices for default values, clamping, etc.

*(This section is documentation only — scoring is 100% automated via the grade() function above.)*
