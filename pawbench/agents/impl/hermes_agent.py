# -*- coding: utf-8 -*-
"""Hermes agent implementation for pawbench evaluation."""

import json
import os
import secrets
import shlex
import time
from datetime import datetime
from typing import Any, Dict, List, Optional

import yaml

from pawbench.agents.base import ContainerAgent
from pawbench.agents.constants import AGENT_WORKSPACE
from pawbench.envs.base import BaseEnvironment
from pawbench.llm.model_config import get_model_config, ModelConfig, ProviderType


_HERMES_VERSION = "2026.4.23"

# Map pawbench ProviderType → hermes config.yaml model.provider value.
# hermes v0.11.0 installed in the container supports these as config providers:
# "custom"   — OpenAI-compatible endpoint (DashScope, plain OpenAI, any custom URL)
# "anthropic" — Anthropic Messages API
# "gemini"   — Google AI Studio
# Other values are used by newer hermes builds but not v0.11.0.
_CONFIG_PROVIDER_MAP: Dict[ProviderType, str] = {
    ProviderType.ANTHROPIC: "anthropic",
    ProviderType.GOOGLE:    "gemini",
    ProviderType.DASHSCOPE: "custom",   # DashScope is OpenAI-compatible; use custom + base_url
    ProviderType.OPENAI:    "custom",
    ProviderType.AZURE:     "custom",   # azure-foundry not available in v0.11.0
    ProviderType.CUSTOM:    "custom",
}

# hermes v0.11.0 CLI --provider valid choices (from `hermes chat --help`).
# Providers NOT in this set must be configured via config.yaml only (no CLI flag).
_CLI_PROVIDER_CHOICES: frozenset = frozenset({
    "auto", "openrouter", "nous", "openai-codex", "copilot-acp", "copilot",
    "anthropic", "gemini", "xai", "ollama-cloud", "huggingface", "zai",
    "kimi-coding", "kimi-coding-cn", "stepfun", "minimax", "minimax-cn",
    "kilocode", "xiaomi", "arcee", "nvidia",
})

# Per-provider env var that hermes reads for the API key.
# DashScope, OpenAI, Azure, and Custom all use OPENAI_API_KEY in v0.11.0
# (the "custom" provider path in hermes reads OPENAI_API_KEY as primary key).
_PROVIDER_KEY_ENV: Dict[ProviderType, str] = {
    ProviderType.DASHSCOPE: "OPENAI_API_KEY",   # custom provider reads OPENAI_API_KEY
    ProviderType.ANTHROPIC: "ANTHROPIC_API_KEY",
    ProviderType.GOOGLE:    "GOOGLE_API_KEY",
    ProviderType.OPENAI:    "OPENAI_API_KEY",
    ProviderType.AZURE:     "OPENAI_API_KEY",
    ProviderType.CUSTOM:    "OPENAI_API_KEY",
}

# Per-provider env var for a custom base URL override (hermes convention).
_PROVIDER_BASE_URL_ENV: Dict[ProviderType, Optional[str]] = {
    ProviderType.DASHSCOPE: None,   # base_url goes into model.base_url in config.yaml
    ProviderType.ANTHROPIC: "ANTHROPIC_BASE_URL",
    ProviderType.GOOGLE:    "GEMINI_BASE_URL",
    ProviderType.OPENAI:    None,
    ProviderType.AZURE:     None,
    ProviderType.CUSTOM:    None,   # base_url goes into model.base_url in config.yaml
}


class HermesAgent(ContainerAgent):
    """Hermes Agent for pawbench evaluation.

    Runs tasks via ``hermes chat -q "instruction" -Q --yolo``.
    Pre-built image ``hermes-qwenclawbench:latest`` already has Hermes
    installed; the slow-path installs from PyPI when only a plain base image
    is used.
    """

    def __init__(self, name: str = "hermes", **kwargs: Any):
        super().__init__(name, **kwargs)

    # ── installation ──────────────────────────────────────────────────────────

    async def install(self, environment: BaseEnvironment) -> None:
        check = await environment.execute_command("command -v hermes", timeout=30)
        if check.get("returncode", 1) == 0 and check.get("stdout", "").strip():
            return

        await environment.execute_command(
            "apt-get update -qq && "
            "DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends "
            "python3 python3-pip git curl ripgrep 2>/dev/null | tail -3 || true",
            timeout=120,
        )
        install_result = await environment.execute_command(
            f"pip install --quiet 'hermes-agent=={_HERMES_VERSION}' 2>&1 | tail -5",
            timeout=300,
        )
        if install_result.get("returncode", 1) != 0:
            await environment.execute_command(
                "curl -LsSf https://astral.sh/uv/install.sh | env HOME=/root sh && "
                f"git clone --depth 1 --branch v{_HERMES_VERSION} "
                "https://github.com/NousResearch/hermes-agent.git /opt/hermes && "
                "cd /opt/hermes && "
                "/root/.local/bin/uv venv /opt/hermes-venv --python 3.11 && "
                "/root/.local/bin/uv pip install -e '.[all]' "
                "  --python /opt/hermes-venv/bin/python3 2>&1 | tail -10 && "
                "ln -sf /opt/hermes-venv/bin/hermes /usr/local/bin/hermes",
                timeout=600,
            )

    # ── config helpers ────────────────────────────────────────────────────────

    @staticmethod
    def _config_provider(provider: ProviderType) -> str:
        """Map pawbench ProviderType to hermes config.yaml model.provider value."""
        return _CONFIG_PROVIDER_MAP.get(provider, "custom")

    @staticmethod
    def _cli_provider(provider: ProviderType) -> Optional[str]:
        """Return the --provider CLI flag value, or None if not valid in v0.11.0."""
        config_prov = _CONFIG_PROVIDER_MAP.get(provider, "custom")
        return config_prov if config_prov in _CLI_PROVIDER_CHOICES else None

    def _build_config(
        self, model_config: ModelConfig, *, explicit_base_url: bool = False
    ) -> Dict[str, Any]:
        """Build a valid hermes config.yaml dict.

        Rules (from hermes_cli/config.py _KNOWN_ROOT_KEYS and runtime_provider.py):
        - Valid root keys: _config_version, model, providers, agent, terminal, workspace
        - model: string or dict; dict fields: default, provider, base_url, api_mode,
          max_tokens
        - agent: dict fields: max_turns
        - terminal.cwd: sets the working directory for every terminal tool call
        - workspace: root dir for write_file tool (must match AGENT_WORKSPACE so
          the grader can find output files via collect_workspace)
        - --yolo on CLI handles approval bypass; no "approvals" key in config
        """
        config_prov = self._config_provider(model_config.provider)
        max_turns = int(self.config.get("max_turns", 90))

        # hermes v2026.4.x hardcodes the API endpoint for native providers
        # ("anthropic" → api.anthropic.com, "gemini" → generativelanguage.googleapis.com)
        # and ignores both ANTHROPIC_BASE_URL env var and model.base_url in config.yaml
        # for those providers.  When the caller provides an explicit custom base_url,
        # fall back to the "custom" (OpenAI-compatible) provider so hermes uses the
        # configured endpoint instead of its hardcoded default.
        if explicit_base_url and model_config.base_url and config_prov in ("anthropic", "gemini"):
            config_prov = "custom"
            # OpenAI SDK expects the base_url to end with /v1; normalise if missing.
            url = model_config.base_url.rstrip("/")
            if not url.endswith("/v1"):
                model_config.base_url = url + "/v1"

        model_section: Dict[str, Any] = {
            "provider": config_prov,
            "default":  model_config.model_name,
        }
        # "custom" provider requires base_url in config.yaml so hermes knows
        # which endpoint to call.
        if model_config.base_url:
            model_section["base_url"] = model_config.base_url

        # Set a generous max_tokens so the model can generate complete responses
        # including tool calls without hitting a truncation limit.  Claude Opus
        # with extended thinking can consume many tokens internally; a low default
        # (e.g. 4096) can cause the second+ LLM call to return an empty response,
        # making hermes terminate the session prematurely.
        max_tokens = int(self.config.get("max_tokens", 16000))
        model_section["max_tokens"] = max_tokens

        return {
            "_config_version": 1,
            "model": model_section,
            "agent": {
                "max_turns": max_turns,
            },
            "terminal": {
                "cwd": AGENT_WORKSPACE,   # hermes terminal tool initial directory
            },
            "workspace": AGENT_WORKSPACE,  # write_file root — must match benchmark workspace
        }

    def _build_dotenv(
        self,
        api_key: str,
        model_config: ModelConfig,
        *,
        explicit_base_url: bool = False,
        is_custom_fallback: bool = False,
    ) -> str:
        """Build ~/.hermes/.env content.

        Only writes the env var that hermes actually reads for this provider.
        The base URL override env var (e.g. ANTHROPIC_BASE_URL) is written only
        when the caller explicitly configured a custom URL — not when it's the
        pawbench default — so hermes falls back to its own hardcoded default
        for native providers (anthropic, gemini).

        When ``is_custom_fallback`` is True the provider was downgraded to
        "custom" in config.yaml (because hermes ignores base_url for native
        providers), so we also write OPENAI_API_KEY which is what the hermes
        "custom" provider path reads.
        """
        provider = model_config.provider
        key_var = _PROVIDER_KEY_ENV.get(provider, "OPENAI_API_KEY")
        lines = [f"{key_var}={api_key}"]

        # custom-fallback path: hermes reads OPENAI_API_KEY for the "custom"
        # provider; write it alongside the native key so either path works.
        if is_custom_fallback and key_var != "OPENAI_API_KEY":
            lines.append(f"OPENAI_API_KEY={api_key}")

        # Write base URL override env var for providers that use env-var routing
        # (anthropic, gemini) — skipped for custom (URL is in config.yaml).
        # In the fallback case the base_url already has /v1 appended, but that's
        # harmless since these env vars won't be read by hermes for "custom".
        url_env = _PROVIDER_BASE_URL_ENV.get(provider)
        if explicit_base_url and url_env and model_config.base_url:
            lines.append(f"{url_env}={model_config.base_url}")

        return "\n".join(lines) + "\n"

    # ── setup ─────────────────────────────────────────────────────────────────

    async def setup(self, environment: BaseEnvironment) -> None:
        await self.install(environment)

        # Create required directories only — no invalid symlinks.
        await environment.execute_command(
            f"mkdir -p {AGENT_WORKSPACE}/sessions {AGENT_WORKSPACE}/output "
            "&& mkdir -p /root/.hermes/sessions",
            timeout=15,
        )

        # Write a placeholder config (model details are written per-task in run()).
        placeholder: Dict[str, Any] = {
            "_config_version": 1,
            "agent": {"max_turns": 90},
            "terminal": {"cwd": AGENT_WORKSPACE},
        }
        await environment.write_file(
            "/root/.hermes/config.yaml",
            yaml.dump(placeholder, default_flow_style=False, allow_unicode=True),
        )

        # Clean any state left from a previous run.
        await self._reset_hermes_state(environment)

    # ── per-task state reset ──────────────────────────────────────────────────

    async def _reset_hermes_state(self, environment: BaseEnvironment) -> None:
        """Wipe hermes session state so each task starts clean."""
        await environment.execute_command(
            "rm -f /root/.hermes/state.db "
            "/root/.hermes/state.db-wal "
            "/root/.hermes/state.db-shm "
            "/root/.hermes/sessions/*.jsonl "
            "/root/.hermes/sessions/*.jsonl.lock "
            "2>/dev/null || true",
            timeout=15,
        )

    # ── run ───────────────────────────────────────────────────────────────────

    async def run(self, instruction: str, environment: BaseEnvironment) -> Dict[str, Any]:
        model_identifier = self.config.get("model", "dashscope/qwen3.6-plus")
        model_config = get_model_config(model_identifier)
        api_key = (
            self.config.get("api_key")
            or model_config.api_key
            or os.environ.get(_PROVIDER_KEY_ENV.get(model_config.provider, "OPENAI_API_KEY"), "")
        )
        # Allow explicit base_url override from pawbench config.
        explicit_base_url = bool(self.config.get("base_url"))
        if explicit_base_url:
            model_config.base_url = self.config["base_url"]

        # Detect whether _build_config will fall back from a native provider
        # (anthropic/gemini) to "custom" because hermes hardcodes its default
        # endpoint for those providers and ignores base_url in config.yaml.
        _orig_config_prov = self._config_provider(model_config.provider)
        is_custom_fallback = (
            explicit_base_url
            and bool(model_config.base_url)
            and _orig_config_prov in ("anthropic", "gemini")
        )

        # Write per-task config.yaml and .env.
        await environment.write_file(
            "/root/.hermes/config.yaml",
            yaml.dump(
                self._build_config(model_config, explicit_base_url=explicit_base_url),
                default_flow_style=False,
                allow_unicode=True,
            ),
        )
        await environment.write_file(
            "/root/.hermes/.env",
            self._build_dotenv(
                api_key,
                model_config,
                explicit_base_url=explicit_base_url,
                is_custom_fallback=is_custom_fallback,
            ),
        )

        # Reset session state before each task.
        await self._reset_hermes_state(environment)

        # When falling back to "custom" provider, do not pass --provider on the
        # CLI: the "custom" provider is not in hermes v0.11.0's --provider
        # choices, and passing the original native provider flag (e.g.
        # --provider anthropic) would override config.yaml and re-enable the
        # hardcoded default endpoint.
        if is_custom_fallback:
            cli_provider = None
        else:
            cli_provider = self._cli_provider(model_config.provider)
        inner_timeout = int(self.config.get("task_timeout_s") or 1800)
        session_id = f"pawbench-{int(time.time() * 1000)}"

        # Only pass --provider when the value is in v0.11.0's valid choices.
        # For custom-endpoint providers (DashScope, plain OpenAI, Azure) hermes
        # reads provider + base_url from config.yaml automatically.
        provider_flag = f"--provider {shlex.quote(cli_provider)} " if cli_provider else ""

        run_cmd = (
            f"cd {shlex.quote(AGENT_WORKSPACE)} && "
            # --kill-after=10s: send SIGKILL if hermes is still alive 10 s after SIGTERM,
            # guaranteeing the process (and its inherited fds) eventually closes.
            # Use direct file redirection instead of `| tee` so that orphaned hermes
            # child processes holding the pipe write-end cannot keep docker exec alive.
            f"timeout --kill-after=10s {inner_timeout}s hermes chat "
            f"-q {shlex.quote(instruction)} "
            f"-Q "
            f"--yolo "
            f"{provider_flag}"
            f"--model {shlex.quote(model_config.model_name)} "
            f"> /tmp/hermes_output.txt 2>&1 || true"
        )
        result = await environment.execute_command(run_cmd, timeout=inner_timeout + 70)
        output_content = await environment.read_file("/tmp/hermes_output.txt") or result["stdout"]

        await self._sync_workspace_to_output(environment, AGENT_WORKSPACE)
        await self._write_synthetic_session(
            environment, session_id, instruction, output_content, model_config
        )

        return {
            "success": result["success"],
            "output": output_content,
            "error": result.get("stderr", ""),
            "returncode": result["returncode"],
            "session_data": "",
            "metrics": {
                "execution_time": 0,
                "model_used": model_config.get_full_model_identifier(),
                "provider": model_config.provider.value,
                "config_provider": self._config_provider(model_config.provider),
                "cli_provider": cli_provider,
                "model_name": model_config.model_name,
                "session_id": session_id,
            },
        }

    # ── session helpers ───────────────────────────────────────────────────────

    @staticmethod
    def _short_id() -> str:
        return secrets.token_hex(4)

    @staticmethod
    def _iso_z(ms: int) -> str:
        return (
            datetime.utcfromtimestamp(ms / 1000).strftime("%Y-%m-%dT%H:%M:%S.")
            + f"{ms % 1000:03d}Z"
        )

    @staticmethod
    def _read_hermes_jsonl_messages(raw: str) -> List[Dict[str, Any]]:
        """Parse a hermes ``{session_id}.jsonl`` transcript into OpenAI-style messages."""
        msgs: List[Dict[str, Any]] = []
        for line in raw.splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except (json.JSONDecodeError, ValueError):
                continue
            if not isinstance(obj, dict):
                continue
            msg = obj.get("message") if isinstance(obj.get("message"), dict) else obj
            if isinstance(msg, dict) and msg.get("role"):
                msgs.append(msg)
        return msgs

    # SQLite dump script: pulls every message of the most-recently-started
    # session from ``~/.hermes/state.db`` and emits a JSON list of OpenAI-style
    # rows on stdout.  Hermes 2026.4.x persists the full multi-turn trajectory
    # (including tool_calls / reasoning_content) in this DB.
    # Uses dynamic schema discovery to handle different hermes versions.
    _SQLITE_DUMP_SCRIPT = '''
import json, os, sqlite3, sys

db_path = os.path.expanduser("~/.hermes/state.db")
if not os.path.exists(db_path):
    print("[]")
    sys.exit(0)

try:
    conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
except Exception:
    conn = sqlite3.connect(db_path)
conn.row_factory = sqlite3.Row
try:
    # Dynamic schema discovery — handles different hermes versions
    tables = {r[0] for r in conn.execute(
        "SELECT name FROM sqlite_master WHERE type=\'table\'"
    )}

    sess_table = next((t for t in ("sessions", "session", "chat_sessions") if t in tables), None)
    if not sess_table:
        print("[]"); sys.exit(0)

    sess_cols = {r[1] for r in conn.execute(f"PRAGMA table_info({sess_table})")}
    id_col = next((c for c in ("id", "session_id", "sid") if c in sess_cols), None)
    ts_col = next((c for c in ("started_at", "created_at", "timestamp", "ts") if c in sess_cols), None)
    if not id_col:
        print("[]"); sys.exit(0)

    order_clause = f"ORDER BY {ts_col} DESC" if ts_col else ""
    sess = conn.execute(f"SELECT {id_col} FROM {sess_table} {order_clause} LIMIT 1").fetchone()
    if not sess:
        print("[]"); sys.exit(0)
    sess_id = sess[0]

    msg_table = next((t for t in ("messages", "message", "chat_messages") if t in tables), None)
    if not msg_table:
        print("[]"); sys.exit(0)

    msg_cols = {r[1] for r in conn.execute(f"PRAGMA table_info({msg_table})")}
    fk_col = next((c for c in ("session_id", "sess_id", "session", "chat_session_id") if c in msg_cols), None)
    if not fk_col:
        print("[]"); sys.exit(0)

    want = ["role", "content", "tool_call_id", "tool_calls", "tool_name", "timestamp"]
    extra = ["finish_reason", "reasoning", "reasoning_content"]
    select = [c for c in want + extra if c in msg_cols]
    order_m = next((c for c in ("timestamp", "ts", "created_at", "id") if c in msg_cols), None)
    order_m_clause = f"ORDER BY {order_m}" if order_m else ""

    rows = conn.execute(
        f"SELECT {\', \'.join(select)} FROM {msg_table} "
        f"WHERE {fk_col} = ? {order_m_clause}",
        (sess_id,),
    ).fetchall()

    msgs = []
    for r in rows:
        d = dict(r)
        m = {"role": d.get("role")}
        if d.get("content") is not None:
            m["content"] = d["content"]
        if d.get("tool_call_id"):
            m["tool_call_id"] = d["tool_call_id"]
        if d.get("tool_name"):
            m["name"] = d["tool_name"]
        tc_raw = d.get("tool_calls")
        if tc_raw:
            try:
                m["tool_calls"] = json.loads(tc_raw)
            except Exception:
                pass
        for opt in ("reasoning_content", "reasoning", "finish_reason"):
            v = d.get(opt)
            if v:
                m[opt] = v
        msgs.append(m)
    print(json.dumps(msgs, ensure_ascii=False))
finally:
    conn.close()
'''

    @classmethod
    async def _dump_hermes_session_messages(
        cls, environment: BaseEnvironment
    ) -> List[Dict[str, Any]]:
        """Pull the latest hermes session from ``~/.hermes/state.db``.

        Returns ``[]`` if the DB doesn't exist, has no sessions, or the dump
        fails.  Falls back to ``hermes history --format json`` when the DB
        dump returns empty.
        """
        await environment.write_file("/tmp/hermes_session_dump.py", cls._SQLITE_DUMP_SCRIPT)
        r = await environment.execute_command(
            "python3 /tmp/hermes_session_dump.py", timeout=30
        )
        raw = (r.get("stdout") or "").strip()
        if not raw:
            return []
        try:
            data = json.loads(raw)
        except (json.JSONDecodeError, ValueError):
            return []
        if isinstance(data, list) and data:
            return data

        # state.db dump returned empty — try `hermes history` CLI as fallback
        hist_r = await environment.execute_command(
            "hermes history --format json 2>/dev/null | head -c 524288 || true",
            timeout=20,
        )
        hist_raw = (hist_r.get("stdout") or "").strip()
        if hist_raw:
            try:
                hist_data = json.loads(hist_raw)
                if isinstance(hist_data, list) and hist_data:
                    return hist_data
            except (json.JSONDecodeError, ValueError):
                pass
        return []

    @classmethod
    def _build_openclaw_events(
        cls,
        hermes_msgs: List[Dict[str, Any]],
        *,
        session_id: str,
        instruction: str,
        final_text: str,
        model_config: ModelConfig,
        cwd: str,
    ) -> List[Dict[str, Any]]:
        """Convert hermes OpenAI-style messages into openclaw JSONL event dicts."""
        provider = model_config.provider.value
        model_name = model_config.model_name
        api = "openai-completions"

        base_ms = int(time.time() * 1000)
        offset = 0

        def _next_ms() -> int:
            nonlocal offset
            offset += 1
            return base_ms + offset

        events: List[Dict[str, Any]] = []

        # ── header events ─────────────────────────────────────────────────────
        events.append({
            "type": "session",
            "version": 3,
            "id": session_id,
            "timestamp": cls._iso_z(base_ms),
            "cwd": cwd,
        })

        parent_id: Any = None

        mc_id = cls._short_id()
        events.append({
            "type": "model_change",
            "id": mc_id,
            "parentId": parent_id,
            "timestamp": cls._iso_z(_next_ms()),
            "provider": provider,
            "modelId": model_name,
        })
        parent_id = mc_id

        tlc_id = cls._short_id()
        events.append({
            "type": "thinking_level_change",
            "id": tlc_id,
            "parentId": parent_id,
            "timestamp": cls._iso_z(_next_ms()),
            "thinkingLevel": "off",
        })
        parent_id = tlc_id

        snap_ms = _next_ms()
        snap_id = cls._short_id()
        events.append({
            "type": "custom",
            "customType": "model-snapshot",
            "data": {
                "timestamp": snap_ms,
                "provider": provider,
                "modelApi": api,
                "modelId": model_name,
            },
            "id": snap_id,
            "parentId": parent_id,
            "timestamp": cls._iso_z(snap_ms),
        })
        parent_id = snap_id

        # ── message events ────────────────────────────────────────────────────
        saw_user = False

        def _normalise_content_blocks(raw_content: Any) -> List[Dict[str, Any]]:
            if isinstance(raw_content, str):
                return [{"type": "text", "text": raw_content}] if raw_content else []
            if not isinstance(raw_content, list):
                return []
            blocks: List[Dict[str, Any]] = []
            for b in raw_content:
                if not isinstance(b, dict):
                    if isinstance(b, str) and b:
                        blocks.append({"type": "text", "text": b})
                    continue
                btype = b.get("type")
                if btype == "text":
                    txt = b.get("text") or ""
                    if txt:
                        blocks.append({"type": "text", "text": txt})
                elif btype == "thinking":
                    txt = b.get("thinking") or b.get("text") or ""
                    if txt:
                        blocks.append({
                            "type": "thinking",
                            "thinking": txt,
                            "thinkingSignature": b.get("thinkingSignature", "reasoning_content"),
                        })
                elif btype in ("toolCall", "tool_use"):
                    blocks.append(b)
            return blocks

        for msg in hermes_msgs:
            role = msg.get("role")
            raw_content = msg.get("content")
            ts_ms = _next_ms()

            if role == "user":
                blocks = _normalise_content_blocks(raw_content) or [
                    {"type": "text", "text": ""}
                ]
                ev_id = cls._short_id()
                events.append({
                    "type": "message",
                    "id": ev_id,
                    "parentId": parent_id,
                    "timestamp": cls._iso_z(ts_ms),
                    "message": {
                        "role": "user",
                        "content": blocks,
                        "timestamp": ts_ms,
                    },
                })
                parent_id = ev_id
                saw_user = True

            elif role == "assistant":
                blocks: List[Dict[str, Any]] = []

                reasoning = msg.get("reasoning_content")
                if isinstance(reasoning, str) and reasoning.strip():
                    blocks.append({
                        "type": "thinking",
                        "thinking": reasoning.strip(),
                        "thinkingSignature": "reasoning_content",
                    })

                blocks.extend(_normalise_content_blocks(raw_content))

                tool_calls = msg.get("tool_calls") or []
                for tc in tool_calls:
                    if not isinstance(tc, dict):
                        continue
                    fn = tc.get("function") or {}
                    name = fn.get("name") or tc.get("name") or ""
                    if not name:
                        continue
                    raw_args = fn.get("arguments")
                    if raw_args is None:
                        raw_args = tc.get("arguments")
                    if isinstance(raw_args, str):
                        try:
                            raw_args = json.loads(raw_args)
                        except (json.JSONDecodeError, ValueError):
                            raw_args = {"_raw": raw_args}
                    elif raw_args is None:
                        raw_args = {}
                    blocks.append({
                        "type": "toolCall",
                        "id": tc.get("id") or f"call_{cls._short_id()}",
                        "name": name,
                        "arguments": raw_args,
                    })

                if not blocks:
                    continue

                ev_id = cls._short_id()
                events.append({
                    "type": "message",
                    "id": ev_id,
                    "parentId": parent_id,
                    "timestamp": cls._iso_z(ts_ms),
                    "message": {
                        "role": "assistant",
                        "content": blocks,
                        "api": api,
                        "provider": provider,
                        "model": model_name,
                        "usage": msg.get("usage") or {},
                        "stopReason": "toolUse" if tool_calls else "stop",
                        "timestamp": ts_ms,
                        "responseId": msg.get("responseId") or msg.get("id") or "",
                    },
                })
                parent_id = ev_id

            elif role in ("tool", "function"):
                if isinstance(raw_content, str):
                    text = raw_content
                else:
                    norm = _normalise_content_blocks(raw_content)
                    text = norm[0].get("text", "") if norm else ""
                ev_id = cls._short_id()
                events.append({
                    "type": "message",
                    "id": ev_id,
                    "parentId": parent_id,
                    "timestamp": cls._iso_z(ts_ms),
                    "message": {
                        "role": "toolResult",
                        "toolCallId": msg.get("tool_call_id") or "",
                        "toolName": msg.get("name") or "",
                        "content": [{"type": "text", "text": text}],
                        "isError": bool(msg.get("isError")),
                        "timestamp": ts_ms,
                    },
                })
                parent_id = ev_id

            # role == "system" intentionally skipped

        # ── fallback: synthesise minimal user+assistant pair ──────────────────
        _N_HEADER_EVENTS = 4
        if len(events) <= _N_HEADER_EVENTS:
            user_ms = _next_ms()
            user_id = cls._short_id()
            events.append({
                "type": "message",
                "id": user_id,
                "parentId": parent_id,
                "timestamp": cls._iso_z(user_ms),
                "message": {
                    "role": "user",
                    "content": [{"type": "text", "text": instruction}],
                    "timestamp": user_ms,
                },
            })
            parent_id = user_id

            asst_ms = _next_ms()
            asst_id = cls._short_id()
            events.append({
                "type": "message",
                "id": asst_id,
                "parentId": parent_id,
                "timestamp": cls._iso_z(asst_ms),
                "message": {
                    "role": "assistant",
                    "content": [{"type": "text", "text": final_text}],
                    "api": api,
                    "provider": provider,
                    "model": model_name,
                    "usage": {},
                    "stopReason": "stop",
                    "timestamp": asst_ms,
                    "responseId": "",
                },
            })

        elif not saw_user:
            # Splice a synthetic user turn before the first real message event.
            user_ms = base_ms
            user_id = cls._short_id()
            user_event = {
                "type": "message",
                "id": user_id,
                "parentId": snap_id,
                "timestamp": cls._iso_z(user_ms),
                "message": {
                    "role": "user",
                    "content": [{"type": "text", "text": instruction}],
                    "timestamp": user_ms,
                },
            }
            events.insert(_N_HEADER_EVENTS, user_event)
            if len(events) > _N_HEADER_EVENTS + 1 and events[_N_HEADER_EVENTS + 1].get("type") == "message":
                events[_N_HEADER_EVENTS + 1]["parentId"] = user_id

        return events

    async def _write_synthetic_session(
        self,
        environment: BaseEnvironment,
        session_id: str,
        instruction: str,
        agent_output: str,
        model_config: ModelConfig,
    ) -> None:
        """Persist the run's transcript in openclaw JSONL format under workspace/sessions/.

        Primary source is the hermes SQLite state.db; falls back to the
        legacy per-session JSONL files if the DB is empty or unavailable.
        """
        # 1. Attempt SQLite dump (hermes 2026.4.x primary format).
        hermes_msgs = await self._dump_hermes_session_messages(environment)

        # 2. Fall back to most-recent .jsonl under ~/.hermes/sessions/.
        if not hermes_msgs:
            pick_session = (
                "shopt -s nullglob; best=; best_m=0; "
                f"for f in {AGENT_WORKSPACE}/sessions/*.jsonl"
                " /root/.hermes/sessions/*.jsonl; do "
                '  [ -f "$f" ] || continue; '
                '  case "$f" in '
                f"    {AGENT_WORKSPACE}/sessions/{session_id}.jsonl) continue;; "
                "  esac; "
                '  m=$(stat -c %Y "$f" 2>/dev/null || echo 0); '
                '  if [ "$m" -gt "$best_m" ]; then best_m=$m; best=$f; fi; '
                "done; "
                'printf %s "$best"'
            )
            sess_r = await environment.execute_command(pick_session, timeout=15)
            hermes_jsonl_path = (sess_r.get("stdout") or "").strip()
            if hermes_jsonl_path:
                read_r = await environment.execute_command(
                    f"cat {shlex.quote(hermes_jsonl_path)}", timeout=20
                )
                hermes_msgs = self._read_hermes_jsonl_messages(read_r.get("stdout") or "")

        # 3. Derive final_text from the last assistant turn.
        final_text = agent_output.strip()
        for msg in hermes_msgs:
            if msg.get("role") != "assistant":
                continue
            raw_content = msg.get("content")
            if isinstance(raw_content, str) and raw_content.strip():
                final_text = raw_content.strip()
            elif isinstance(raw_content, list):
                for b in raw_content:
                    if isinstance(b, dict) and b.get("type") == "text":
                        t = (b.get("text") or "").strip()
                        if t:
                            final_text = t

        # 4. Build openclaw event sequence.
        openclaw_events = self._build_openclaw_events(
            hermes_msgs,
            session_id=session_id,
            instruction=instruction,
            final_text=final_text,
            model_config=model_config,
            cwd=AGENT_WORKSPACE,
        )

        # 5. Write <session_id>.jsonl (one event per line).
        await environment.execute_command(
            f"mkdir -p {AGENT_WORKSPACE}/sessions", timeout=10
        )
        jsonl_blob = (
            "\n".join(
                json.dumps(ev, ensure_ascii=False, separators=(",", ":"))
                for ev in openclaw_events
            )
            + "\n"
        )
        await environment.write_file(
            f"{AGENT_WORKSPACE}/sessions/{session_id}.jsonl", jsonl_blob
        )

        # 6. Write hermes_session.json for the grader pipeline.
        message_events = [ev for ev in openclaw_events if ev.get("type") == "message"]
        synth_session = {
            "session_id": session_id,
            "query": instruction,
            "final_text": final_text,
            "status": "completed",
            "trajectory": [],
            "agent": {
                "memory": {"content": message_events},
                "_model_trajectory": [],
            },
        }
        await environment.write_file(
            f"{AGENT_WORKSPACE}/sessions/hermes_session.json",
            json.dumps(synth_session, ensure_ascii=False, indent=2),
        )

    # ── post-run hook ─────────────────────────────────────────────────────────

    async def post_run_collect(self, environment: BaseEnvironment) -> None:
        """Capture hermes system prompt so backend.py can prepend it to the
        transcript.

        Tries two sources in order:
        1. ``system_prompt`` column in the hermes SQLite ``sessions`` table.
        2. ``role=system`` first message in the ``messages`` table (some hermes
           versions store the system prompt as a regular message row).
        """
        _CAPTURE_SCRIPT = r"""python3 - <<'__PYEOF__'
import json, os, sqlite3, sys

db = os.path.expanduser('~/.hermes/state.db')
if not os.path.exists(db):
    print('')
    sys.exit(0)

try:
    conn = sqlite3.connect(f'file:{db}?mode=ro', uri=True)
except Exception:
    conn = sqlite3.connect(db)

conn.row_factory = sqlite3.Row
try:
    sess_cols = {row[1] for row in conn.execute('PRAGMA table_info(sessions)')}
    sess = conn.execute(
        'SELECT * FROM sessions ORDER BY started_at DESC LIMIT 1'
    ).fetchone()
    if not sess:
        print('')
        sys.exit(0)

    # 1. Prefer dedicated system_prompt column
    if 'system_prompt' in sess_cols:
        sp = sess['system_prompt'] or ''
        if sp.strip():
            print(sp.strip())
            sys.exit(0)

    # 2. Fall back to first system message in messages table
    msg_cols = {row[1] for row in conn.execute('PRAGMA table_info(messages)')}
    if 'role' in msg_cols and 'content' in msg_cols:
        row = conn.execute(
            "SELECT content FROM messages WHERE session_id = ? AND role = 'system' "
            'ORDER BY timestamp, id LIMIT 1',
            (sess['id'],),
        ).fetchone()
        if row and row['content']:
            print(str(row['content']).strip())
            sys.exit(0)
finally:
    conn.close()

print('')
__PYEOF__
"""
        sp_result = await environment.execute_command(_CAPTURE_SCRIPT, timeout=15)
        sp_text = (sp_result.get("stdout") or "").strip()
        self._last_system_prompt: "str | None" = sp_text if sp_text else None

        # Sync hermes internal workspace to the standard benchmark path so the
        # grader can find output files via collect_workspace().
        # hermes write_file writes to its own workspace dir (e.g.
        # ~/.hermes/workspaces/default/) even when workspace: is set in config.
        # Explicitly mirror all non-bytecode files from every known hermes
        # workspace location into AGENT_WORKSPACE before the backend snapshots it.
        _SYNC_CMD = rf"""
DEST={AGENT_WORKSPACE}
mkdir -p "$DEST/output"
for src_dir in ~/.hermes/workspaces/default /root/.hermes/workspaces/default; do
  [ -d "$src_dir" ] || continue
  find "$src_dir" -maxdepth 5 -type f \
      ! -path '*/site-packages/*' ! -name '*.pyc' \
      2>/dev/null | while read -r f; do
    rel="${{f#${{src_dir}}/}}"
    dest="$DEST/$rel"
    mkdir -p "$(dirname "$dest")"
    [ ! -s "$dest" ] && [ -s "$f" ] && cp "$f" "$dest" 2>/dev/null || true
  done
done
"""
        await environment.execute_command(_SYNC_CMD, timeout=30)

    # ── teardown ──────────────────────────────────────────────────────────────

    async def teardown(self, environment: BaseEnvironment) -> None:
        # Copy hermes CLI output to the workspace BEFORE deleting it so it
        # is captured as an artifact.  This is invaluable for diagnosing
        # premature-session-termination failures (the output shows exactly
        # what hermes printed, including any error messages from the LLM loop).
        await environment.execute_command(
            f"[ -f /tmp/hermes_output.txt ] && "
            f"cp /tmp/hermes_output.txt {AGENT_WORKSPACE}/hermes_output.txt "
            f"|| true",
            timeout=10,
        )
        await environment.execute_command(
            "rm -f /tmp/hermes_output.txt /tmp/hermes_session_dump.py",
            timeout=10,
        )

    @property
    def version(self) -> str:
        return _HERMES_VERSION
