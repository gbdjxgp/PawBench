---
id: CTB_W06_fullstack_dev_repair
name: Full-Stack Dev Environment Repair
category: terminal
grading_type: hybrid
timeout_seconds: 600
grading_weights:
  automated: 0.8
  llm_judge: 0.2
workspace_files:
- source: assets/T052_claweval_CTB_W06_fullstack_dev_repair/project/README_DEV.md
  dest: project/README_DEV.md
- source: assets/T052_claweval_CTB_W06_fullstack_dev_repair/project/config/backend.env
  dest: project/config/backend.env
- source: assets/T052_claweval_CTB_W06_fullstack_dev_repair/project/frontend/.env.local
  dest: project/frontend/.env.local
- source: assets/T052_claweval_CTB_W06_fullstack_dev_repair/project/proxy/dev_proxy.json
  dest: project/proxy/dev_proxy.json
- source: assets/T052_claweval_CTB_W06_fullstack_dev_repair/project/scripts/check_dev_stack.py
  dest: project/scripts/check_dev_stack.py
labels:
  complexity: L3
  environment: closed
  capabilities:
  - Tool_Use
  - Logic_Reasoning
  - Planning
  - Self_Verification
  scenario: Software_Engineering/DevOps
  modality:
    type: text
---
## Prompt

Workspace files:
- `project/README_DEV.md`
- `project/config/backend.env`
- `project/frontend/.env.local`
- `project/proxy/dev_proxy.json`
- `project/scripts/check_dev_stack.py`

The local full-stack development environment is failing to start. Your task:
1. Read `README_DEV.md` first to understand the **target local-dev contract**, then inspect the three config files to understand the true root-cause chain — do not just fix the last error you see.
2. Fix the following 3 configuration files so the local dev stack is consistent again:
   - `project/config/backend.env`
   - `project/frontend/.env.local`
   - `project/proxy/dev_proxy.json`
3. Keep file paths and overall structure unchanged — do not alter business logic.
4. Run `python project/scripts/check_dev_stack.py` from the workspace root and confirm it outputs `DEV_STACK_OK`.
5. Write `DEV_ENV_FIX.md` (in the workspace root) explaining:
   - The true root cause.
   - Which errors were merely downstream symptoms.
   - Exactly which configuration values you changed.
   - How you verified the fix.

Constraints:
- Do not modify `check_dev_stack.py`.
- Do not modify the README.
- Do not add any additional services.
- Do not change local-dev configuration to production configuration.

## Expected Behavior

1. Read `README_DEV.md` to learn the target local-dev contract: backend port `9101`, public path `/api`, session mode `local`, database `postgres-dev`, frontend port `3000`, websocket `ws://backend:9101/socket`, output dir `/workspace/output/dev-stack`.
2. Recognize that the existing files still carry the **old** values (`9001` / `/api/v2` / `external` session) and need to be migrated to the new dev contract — this is an incomplete migration, not a single broken service.
3. Fix `project/config/backend.env` to:
   ```
   APP_MODE=dev
   API_PORT=9101
   DB_HOST=postgres-dev
   PUBLIC_API_PATH=/api
   SESSION_MODE=local
   STACK_OUTPUT_DIR=/workspace/output/dev-stack
   ```
4. Fix `project/frontend/.env.local` to:
   ```
   VITE_API_ORIGIN=http://localhost:9101
   VITE_API_PATH=/api
   VITE_DEV_PROXY_PORT=3000
   VITE_LOGIN_MODE=local
   ```
5. Fix `project/proxy/dev_proxy.json` so that:
   - `listen` = `3000`
   - `routes["/api"]` = `http://backend:9101/api`
   - `routes["/auth"]` = `http://backend:9101/auth`
   - `websocket` = `ws://backend:9101/socket`
6. Run `python project/scripts/check_dev_stack.py` and verify it prints `DEV_STACK_OK ...`. The script writes a status JSON under `output/dev-stack/dev_stack_status.json`.
7. Author `DEV_ENV_FIX.md` describing the migration root cause and the verification.

## Grading Criteria

- [ ] `backend.env` matches the target dev contract (`backend_ok`).
- [ ] `frontend/.env.local` matches the target dev contract (`frontend_ok`).
- [ ] `proxy/dev_proxy.json` matches the target dev contract (`proxy_ok`).
- [ ] `dev_stack_status.json` exists with the correct payload (`status_ok`).
- [ ] `DEV_ENV_FIX.md` exists with key root-cause keywords (`doc_ok`).
- [ ] LLM judge grades the explanation quality.

## Automated Checks

```python
import json
from pathlib import Path


def grade(transcript: list, workspace_path: str) -> dict:
    result = {
        "backend_ok": 0.0,
        "frontend_ok": 0.0,
        "proxy_ok": 0.0,
        "status_ok": 0.0,
        "doc_exists": 0.0,
        "doc_keywords_ok": 0.0,
    }

    workspace = Path(workspace_path)
    backend_path = workspace / "project" / "config" / "backend.env"
    frontend_path = workspace / "project" / "frontend" / ".env.local"
    proxy_path = workspace / "project" / "proxy" / "dev_proxy.json"
    status_path = workspace / "output" / "dev-stack" / "dev_stack_status.json"
    doc_path = workspace / "DEV_ENV_FIX.md"

    def _load_env(path: Path) -> dict:
        out = {}
        try:
            for line in path.read_text().splitlines():
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                key, value = line.split("=", 1)
                out[key.strip()] = value.strip()
        except Exception:
            pass
        return out

    backend = _load_env(backend_path)
    if (
        backend.get("APP_MODE") == "dev"
        and backend.get("API_PORT") == "9101"
        and backend.get("DB_HOST") == "postgres-dev"
        and backend.get("PUBLIC_API_PATH") == "/api"
        and backend.get("SESSION_MODE") == "local"
        and backend.get("STACK_OUTPUT_DIR") == "/workspace/output/dev-stack"
    ):
        result["backend_ok"] = 1.0
    else:
        hits = sum(
            1 for k, v in {
                "APP_MODE": "dev",
                "API_PORT": "9101",
                "DB_HOST": "postgres-dev",
                "PUBLIC_API_PATH": "/api",
                "SESSION_MODE": "local",
                "STACK_OUTPUT_DIR": "/workspace/output/dev-stack",
            }.items()
            if backend.get(k) == v
        )
        if hits >= 4:
            result["backend_ok"] = 0.5
        elif hits >= 2:
            result["backend_ok"] = 0.2

    frontend = _load_env(frontend_path)
    if (
        frontend.get("VITE_API_ORIGIN") == "http://localhost:9101"
        and frontend.get("VITE_API_PATH") == "/api"
        and frontend.get("VITE_DEV_PROXY_PORT") == "3000"
        and frontend.get("VITE_LOGIN_MODE") == "local"
    ):
        result["frontend_ok"] = 1.0
    else:
        hits = sum(
            1 for k, v in {
                "VITE_API_ORIGIN": "http://localhost:9101",
                "VITE_API_PATH": "/api",
                "VITE_DEV_PROXY_PORT": "3000",
                "VITE_LOGIN_MODE": "local",
            }.items()
            if frontend.get(k) == v
        )
        if hits >= 3:
            result["frontend_ok"] = 0.5
        elif hits >= 1:
            result["frontend_ok"] = 0.2

    try:
        proxy = json.loads(proxy_path.read_text())
        routes = proxy.get("routes") or {}
        if (
            proxy.get("listen") == 3000
            and routes.get("/api") == "http://backend:9101/api"
            and routes.get("/auth") == "http://backend:9101/auth"
            and proxy.get("websocket") == "ws://backend:9101/socket"
        ):
            result["proxy_ok"] = 1.0
        else:
            hits = sum([
                proxy.get("listen") == 3000,
                routes.get("/api") == "http://backend:9101/api",
                routes.get("/auth") == "http://backend:9101/auth",
                proxy.get("websocket") == "ws://backend:9101/socket",
            ])
            if hits >= 3:
                result["proxy_ok"] = 0.5
            elif hits >= 1:
                result["proxy_ok"] = 0.2
    except Exception:
        pass

    if status_path.is_file():
        try:
            status = json.loads(status_path.read_text())
            expected = {
                "backend_mode": "dev",
                "backend_port": 9101,
                "db_host": "postgres-dev",
                "frontend_port": 3000,
                "public_api_path": "/api",
                "session_mode": "local",
                "status": "healthy",
            }
            if status == expected:
                result["status_ok"] = 1.0
            elif all(status.get(k) == v for k, v in expected.items()):
                result["status_ok"] = 0.7
        except Exception:
            pass

    if doc_path.is_file():
        try:
            text = doc_path.read_text()
            result["doc_exists"] = 1.0
            lower = text.lower()
            must_have = ["root cause", "根因", "9001", "9101", "api/v2", "local", "proxy", "验证"]
            hits = sum(1 for kw in must_have if kw.lower() in lower)
            if hits >= 5 and len(text) >= 140:
                result["doc_keywords_ok"] = 1.0
            elif hits >= 3:
                result["doc_keywords_ok"] = 0.5
        except Exception:
            pass

    return result
```

## LLM Judge Rubric

### Criterion 1: Migration Explanation Quality (Weight: 100%)

Evaluate the `DEV_ENV_FIX.md` write-up (or the final assistant message if the file is missing).

**Expected content:**
- Identifies that the true root cause is an **incomplete migration** from the old `9001` / `/api/v2` / external-session stack to the new `9101` / `/api` / local-session contract — not a single failing service.
- Distinguishes the symptoms (mismatched ports, mismatched API paths, wrong session mode, wrong proxy listen, mismatched output dir) from the root cause.
- Lists exactly which keys were changed in each of the three files (`backend.env`, `frontend/.env.local`, `dev_proxy.json`).
- Mentions that verification was done by running `check_dev_stack.py` and seeing `DEV_STACK_OK`.

**Scoring bands:**
- **0.9-1.0**: All four points covered; concrete keys cited (`API_PORT`, `VITE_API_ORIGIN`, `routes`, `STACK_OUTPUT_DIR`); verification described; old vs new contract clearly distinguished.
- **0.7-0.8**: Root cause and fix clear; minor omissions in symptom-vs-cause separation or verification step.
- **0.5-0.6**: Identifies the migration issue but missing concrete key changes or the verification step.
- **0.3-0.4**: Vague description; mentions ports / config but no migration framing.
- **0.0-0.2**: Wrong root cause, fabricated fix, or no usable explanation.
