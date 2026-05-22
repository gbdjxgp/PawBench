# -*- coding: utf-8 -*-
"""OpenClaw agent implementation for pawbench evaluation."""

import json
import os
import shlex
import time
from typing import Any, Dict

from pawbench.agents.base import ContainerAgent
from pawbench.agents.constants import AGENT_WORKSPACE
from pawbench.envs.base import BaseEnvironment
from pawbench.llm.model_config import get_model_config, ProviderType


_GATEWAY_PORT = 18789


class OpenClawAgent(ContainerAgent):
    """OpenClaw agent for pawbench evaluation.

    Runs tasks via ``openclaw agent --message``.  Pre-built image
    ``copawbench-openclaw:latest`` already has openclaw 2026.4.24 installed;
    the slow-path installs from npm when only a plain base image is used.
    """

    def __init__(self, name: str = "openclaw", **kwargs: Any):
        super().__init__(name, **kwargs)

    def _agent_id(self) -> str:
        """Return a stable, filesystem-safe openclaw agent ID for this run."""
        model = self.config.get("model", "dashscope/qwen3.6-plus")
        slug = model.replace("/", "-").replace(".", "-").lower()
        return f"bench-{slug}"

    def _openclaw_model_id(self, model_identifier: str) -> str:
        """Translate a pawbench model identifier to an openclaw model identifier.

        openclaw's first-party DashScope integration (``extensions/qwen/``) uses
        ``"qwen"`` as the canonical provider ID.  Mapping ``dashscope/model`` →
        ``qwen/model`` ensures the model reference matches the provider key we
        write into ``openclaw.json``.
        """
        parts = model_identifier.split("/", 1)
        if len(parts) == 2:
            provider_str = parts[0].lower()
            model_name = parts[1]
            if provider_str == "dashscope":
                return f"qwen/{model_name}"
        return model_identifier

    # ── installation ──────────────────────────────────────────────────────────

    async def install(self, environment: BaseEnvironment) -> None:
        check = await environment.execute_command("command -v openclaw", timeout=10)
        if check.get("returncode", 1) == 0 and check.get("stdout", "").strip():
            return
        await environment.execute_command(
            "apt-get update && "
            "DEBIAN_FRONTEND=noninteractive apt-get install -y git curl && "
            "node --version | grep -qE 'v(2[2-9]|[3-9][0-9])' || "
            "(curl -fsSL https://deb.nodesource.com/setup_22.x | bash - && "
            "DEBIAN_FRONTEND=noninteractive apt-get install -y nodejs)",
            timeout=180,
        )
        await environment.execute_command(
            "npm install -g openclaw@2026.4.24", timeout=180
        )

    # ── setup ─────────────────────────────────────────────────────────────────

    async def setup(self, environment: BaseEnvironment) -> None:
        await self.install(environment)

        # Create workspace and openclaw state directories.
        # No symlinks needed — the agent will be bound to AGENT_WORKSPACE
        # directly via ``openclaw agents add --workspace``.
        await environment.execute_command(
            f"mkdir -p {AGENT_WORKSPACE}/output {AGENT_WORKSPACE}/sessions && "
            "mkdir -p /root/.openclaw/agents",
            timeout=15,
        )

        model_identifier = self.config.get("model", "dashscope/qwen3.6-plus")
        rc = get_model_config(model_identifier).resolve_with(self.config)
        api_key = rc.api_key
        base_url = rc.base_url

        # Write provider + model configuration into openclaw.json once so
        # every subsequent openclaw invocation (gateway, agents add, agent run)
        # uses consistent settings without further patching.
        await self._configure_openclaw_json(
            environment,
            api_key=api_key,
            base_url=base_url,
            model_identifier=model_identifier,
        )

        # NOTE: _stabilise_gateway_plugins() — disable bonjour + run
        # ``openclaw doctor --fix`` — is currently disabled.  The fix is
        # validated in isolation but the in-benchmark integration still
        # leaves the gateway in a half-dead state on some tasks; pausing
        # the call here while we investigate.  The method body is preserved
        # below so we can re-enable it with a single line.

        await self._ensure_gateway(environment, api_key=api_key)

        # Create (or recreate) the named bench agent so its workspace and
        # model are explicitly bound.  Deleting first guarantees no stale
        # config from a previous run leaks into the new task.
        agent_id = self._agent_id()
        openclaw_model = self._openclaw_model_id(model_identifier)
        env_prefix = (
            f"export QWEN_API_KEY={shlex.quote(api_key)} "
            f"DASHSCOPE_API_KEY={shlex.quote(api_key)} && "
        )
        # NOTE: The first openclaw CLI invocation in a fresh container installs
        # all plugin runtime dependencies (~26 s).  Timeouts here must exceed
        # that warm-up cost; subsequent invocations reuse the cached deps and
        # complete in < 1 s.
        await environment.execute_command(
            f"{env_prefix}"
            f"openclaw agents delete {shlex.quote(agent_id)} --force 2>/dev/null || true",
            timeout=90,
        )
        add_result = await environment.execute_command(
            f"{env_prefix}"
            f"openclaw agents add {shlex.quote(agent_id)} "
            f"--model {shlex.quote(openclaw_model)} "
            f"--workspace {shlex.quote(AGENT_WORKSPACE)} "
            "--non-interactive",
            timeout=120,
        )
        if add_result.get("returncode", 1) != 0:
            import logging
            logging.getLogger(__name__).error(
                "openclaw agents add failed (exit %s) — agent=%s model=%s\nstdout: %s\nstderr: %s",
                add_result.get("returncode"),
                agent_id,
                model_identifier,
                (add_result.get("stdout") or "")[:500],
                (add_result.get("stderr") or "")[:500],
            )

        # ``agents add`` rewrites openclaw.json and may drop fields like
        # ``gateway.mode`` that the gateway requires on startup.  Patch them
        # back in immediately after ``agents add`` completes so the gateway
        # restart below does not fail with "missing gateway.mode".
        await environment.write_file(
            "/tmp/patch_gateway_mode.py",
            "import json, os\n"
            "p = '/root/.openclaw/openclaw.json'\n"
            "d = json.load(open(p)) if os.path.exists(p) else {}\n"
            "d.setdefault('gateway', {})['mode'] = 'local'\n"
            "json.dump(d, open(p, 'w'), indent=2)\n"
            "print('gateway.mode ensured')\n",
        )
        await environment.execute_command(
            "python3 /tmp/patch_gateway_mode.py",
            timeout=10,
        )

        # ``agents add`` writes to openclaw.json and exits; the gateway picks up
        # the change via an inotify watcher.  In containers that hit the inotify
        # limit (ENOSPC) the watcher silently fails and the gateway may not
        # learn about the new agent for 30–60 s.  Force-restarting the gateway
        # here ensures it loads the agent config from disk immediately, so that
        # the first ``openclaw agent --message`` call in run() succeeds.
        await environment.execute_command(
            "pkill -9 -f 'openclaw gateway' 2>/dev/null; "
            "pkill -9 -f 'openclaw-gateway' 2>/dev/null; "
            "sleep 0.5; true",
            timeout=8,
        )
        await environment.execute_command(
            f"export QWEN_API_KEY={shlex.quote(api_key)} && "
            f"export DASHSCOPE_API_KEY={shlex.quote(api_key)} && "
            f"export OPENAI_API_KEY={shlex.quote(api_key)} && "
            "export OPENCLAW_DISABLE_BONJOUR=1 && "
            "nohup openclaw gateway >/tmp/openclaw_gateway.log 2>&1 & "
            "echo $! >/tmp/openclaw_gateway.pid || true",
            timeout=10,
        )
        # Wait for gateway to come back up and load the new agent config.
        wait_cmd = (
            f'python3 -c "'
            "import socket, time; "
            f"deadline=time.time()+45; ok=False\n"
            "while time.time()<deadline:\n"
            f"  s=socket.socket(); s.settimeout(0.3)\n"
            f"  try: s.connect(('127.0.0.1',18789)); ok=True; break\n"
            f"  except Exception: time.sleep(0.3)\n"
            f"  finally:\n"
            f"    try: s.close()\n"
            f"    except Exception: pass\n"
            "print('GATEWAY_READY' if ok else 'GATEWAY_NOT_READY')\""
        )
        await environment.execute_command(wait_cmd, timeout=55)

    # ── openclaw.json configuration ───────────────────────────────────────────

    # Map from pawbench/openclaw provider id → openclaw ``api`` protocol type.
    # Everything not listed here uses ``openai-completions`` (the safe default
    # for any OpenAI-compatible endpoint, including DashScope).
    _PROVIDER_API_TYPE: Dict[str, str] = {
        "anthropic": "anthropic-messages",
        "google":    "google-generative-ai",
        "ollama":    "ollama",
    }

    # Per-provider env var that carries the API key.
    _PROVIDER_KEY_ENV: Dict[str, str] = {
        "dashscope": "DASHSCOPE_API_KEY",
        "qwen":      "DASHSCOPE_API_KEY",
        "anthropic": "ANTHROPIC_API_KEY",
        "google":    "GOOGLE_API_KEY",
    }

    async def _configure_openclaw_json(
        self,
        environment: BaseEnvironment,
        *,
        api_key: str,
        base_url: str,
        model_identifier: str,
    ) -> None:
        """Patch ``~/.openclaw/openclaw.json`` with provider and model config.

        This replaces the previous dual-path approach (auth-profiles.json +
        conditional openclaw.json patch) with a single, always-executed write:

        * The API key is stored as an env-variable reference so the plaintext
          secret does not appear in the config file. The env vars are set
          before every openclaw invocation anyway.
        * ``base_url`` defaults to the official DashScope endpoint when the
          provider is ``dashscope``/``qwen`` and no override is supplied.
        * Model metadata (``reasoning``, ``contextWindow``, ``maxTokens``) is
          filled in for well-known providers so openclaw can handle thinking
          mode and context-limit decisions correctly.
        * ``thinkingFormat`` is intentionally omitted — valid values in the
          current openclaw schema are ``openai``, ``openrouter``, ``deepseek``,
          and ``zai``; ``qwen``/``qwen-chat-template`` are explicitly excluded.
        * ``compaction`` is set to ``safeguard`` and ``tools.allow`` to ``["*"]``
          to match QwenClawBench defaults and avoid silent task failures.
        """
        try:
            provider_str = (
                model_identifier.split("/", 1)[0].lower()
                if "/" in model_identifier else "openai"
            )
            model_name = model_identifier.split("/")[-1]

            # ── provider id & base URL ─────────────────────────────────────
            if provider_str in ("dashscope", "qwen"):
                # openclaw's first-party Qwen/DashScope plugin (extensions/qwen/)
                # defines PROVIDER_ID = "qwen" and only recognises "qwen" /
                # "modelstudio" when scanning openclaw.json at runtime.  Writing
                # "dashscope" as the provider key would be treated as an unknown
                # custom provider and the qwen plugin would still route known Qwen
                # model names to its own "qwen" entry, silently overriding ours.
                # Using "qwen" as the key, combined with disabling the plugin
                # below, gives us full control over the provider configuration.
                openclaw_provider = "qwen"
                effective_base_url = (
                    base_url or "https://dashscope.aliyuncs.com/compatible-mode/v1"
                )
            elif provider_str == "custom":
                # For CUSTOM providers, use "custom" as the provider key so it
                # matches the model reference written by ``openclaw agents add
                # --model custom/<model_name>``.  Using a hostname-derived key
                # (e.g. "custom-172-17-0-1") would create a mismatch: the agent
                # entry would reference provider "custom" while the provider is
                # registered under the hostname-derived name, causing the gateway
                # to fail model lookup silently.
                openclaw_provider = "custom"
                effective_base_url = base_url or ""
            elif base_url:
                from urllib.parse import urlparse
                hostname = urlparse(base_url).hostname or "custom"
                openclaw_provider = "custom-" + hostname.replace(".", "-")
                effective_base_url = base_url
            else:
                openclaw_provider = provider_str
                effective_base_url = ""

            # ── api protocol type ──────────────────────────────────────────
            provider_api = self._PROVIDER_API_TYPE.get(provider_str, "openai-completions")

            # ── api key reference ──────────────────────────────────────────
            # Use a literal string key (not an env-ref object).  The env-ref
            # format is rejected by openclaw's config validator when
            # ``agents add`` runs, and the agents add command would abort.
            # The API key is already available in the container environment
            # for every openclaw invocation, so embedding it directly is
            # equivalent but avoids the schema validation failure.
            api_key_entry: Any = api_key

            # openclaw schema requires BOTH "id" and "name" for model list entries
            # under models.providers.<p>.models[]; omitting either causes config
            # validation failure on ``openclaw agents add``.
            model_entry: Dict[str, Any] = {
                "id": model_name,
                "name": model_name,
                "compat": {"supportsTools": True},
            }
            # Resolve vision capability from ModelConfig — single source of truth.
            # supports_vision / vision_model are populated by ModelConfigManager
            # from the _VISION_CAPABLE_MODELS / _VISION_COMPANION registries in
            # model_config.py; no capability knowledge lives in this file.
            mc = get_model_config(model_identifier)
            _input_modalities = ["text", "image"] if mc.supports_vision else ["text"]

            # Populate context/token limits, reasoning flag, and input modalities
            # for well-known providers.  openclaw uses these to drive thinking
            # mode activation, context-window guards, and tool routing.
            if provider_str in ("dashscope", "qwen"):
                model_entry["reasoning"] = True
                model_entry["contextWindow"] = 200000
                model_entry["maxTokens"] = 32768
                model_entry["input"] = _input_modalities
            elif provider_str == "anthropic":
                model_entry["reasoning"] = True
                model_entry["contextWindow"] = 200000
                model_entry["maxTokens"] = 32000
                model_entry["input"] = _input_modalities
            elif provider_str == "openai":
                model_entry["contextWindow"] = 128000
                model_entry["maxTokens"] = 16384
                model_entry["input"] = _input_modalities

            primary = f"{openclaw_provider}/{model_name}"

            # ── vision model (agents.defaults.imageModel) ─────────────────
            # openclaw routes image-tool calls through agents.defaults.imageModel.
            # Without an explicit setting it falls back to the global default
            # (currently openai/gpt-5.5), which 403s when a DashScope key is
            # active.  Callers can override via agent_config["vision_model"].
            vision_model_name: str = (
                self.config.get("vision_model")
                or (model_name if mc.supports_vision else "")
                or mc.vision_model
                or ""
            )
            vision_model_ref = (
                f"{openclaw_provider}/{vision_model_name}" if vision_model_name else ""
            )
            # Only register a separate VL provider entry when the primary model
            # is text-only; vision-capable models already cover image input.
            vision_model_entry: Dict[str, Any] = {}
            if vision_model_name and not mc.supports_vision:
                vision_model_entry = {
                    "id": vision_model_name,
                    "name": vision_model_name,
                    "input": ["text", "image"],
                    "compat": {"supportsTools": False},
                }

            patch_script = (
                "import json, os\n"
                "p = '/root/.openclaw/openclaw.json'\n"
                "os.makedirs(os.path.dirname(p), exist_ok=True)\n"
                "d = json.load(open(p)) if os.path.exists(p) else {}\n"
                # ── provider ──────────────────────────────────────────────
                "providers = d.setdefault('models', {}).setdefault('providers', {})\n"
                f"prov = providers.setdefault({json.dumps(openclaw_provider)}, "
                f"  {{'api': {json.dumps(provider_api)}, 'models': []}})\n"
                f"prov['api'] = {json.dumps(provider_api)}\n"
                f"prov['baseUrl'] = {json.dumps(effective_base_url)}\n"
                f"prov['apiKey'] = {json.dumps(api_key_entry)}\n"
                # ── primary model entry ────────────────────────────────────
                "models = prov.setdefault('models', [])\n"
                f"m = next((x for x in models if x.get('id') == {json.dumps(model_name)} or x.get('name') == {json.dumps(model_name)}), None)\n"
                # Use json.loads to embed model_entry: json.dumps outputs JSON
                # booleans (true/false) which are NOT valid Python literals and
                # would raise NameError in the generated patch script.
                # Double-encoding (json.dumps of a json.dumps string) turns the
                # object into a quoted JSON string literal that json.loads can
                # safely parse at runtime.
                f"new_entry = json.loads({json.dumps(json.dumps(model_entry))})\n"
                "if m is None:\n"
                "    models.append(new_entry)\n"
                "else:\n"
                "    m.update(new_entry)\n"
                # ── vision model entry (for image tool) ────────────────────
                # Register the VL model in the same provider so openclaw's
                # config validator accepts the agents.defaults.imageModel ref.
                + (
                    f"vision_entry = json.loads({json.dumps(json.dumps(vision_model_entry))})\n"
                    f"vm = next((x for x in models if x.get('id') == {json.dumps(vision_model_name)}), None)\n"
                    "if vm is None:\n"
                    "    models.append(vision_entry)\n"
                    "else:\n"
                    "    vm.update(vision_entry)\n"
                    if vision_model_entry else ""
                )
                # ── gateway.mode (required since openclaw 2026.4.x) ───────
                # openclaw gateway refuses to start if gateway.mode is absent.
                # agents add may drop this field when rewriting openclaw.json;
                # ensure it is always present after our patch.
                + "d.setdefault('gateway', {}).setdefault('mode', 'local')\n"
                # ── agents.defaults ───────────────────────────────────────
                + "agents_cfg = d.setdefault('agents', {}).setdefault('defaults', {})\n"
                f"agents_cfg['model'] = {{'primary': {json.dumps(primary)}}}\n"
                f"agents_cfg.setdefault('models', {{}})[{json.dumps(primary)}] = "
                f"  {json.dumps({'alias': model_name})}\n"
                # compaction safeguard prevents long-task context overflow
                "agents_cfg.setdefault('compaction', {})['mode'] = 'safeguard'\n"
                # Set timeoutSeconds to a large value so the gateway does not cut the
                # LLM proxy connection mid-call.  The default of 600 causes a 630 s
                # hard cut ((600+30)×1000 ms) that breaks long thinking-mode calls.
                # openclaw's schema rejects 0 (must be >0), so use 86400 (24 h) as an
                # effectively-infinite sentinel.  The real deadline is enforced by the
                # outer asyncio.wait_for in backend.py.
                "agents_cfg['timeoutSeconds'] = 86400\n"
                # ── imageModel: route image-tool calls to VL model ─────────
                # openclaw.image tool resolves agents.defaults.imageModel to
                # pick which model to send vision requests to.  Without this,
                # it falls back to the global default (currently openai/gpt-5.5)
                # which is unreachable with a DashScope API key → 403/Unknown.
                + (
                    f"agents_cfg['imageModel'] = {json.dumps(vision_model_ref)}\n"
                    f"print('vision model set to: {vision_model_ref}')\n"
                    if vision_model_ref else
                    "print('no vision model configured for this provider')\n"
                )
                # ── disable qwen plugin (dashscope only) ──────────────────
                # The built-in "qwen" plugin (extensions/qwen/) routes known
                # Qwen model names (e.g. qwen3.6-plus) to the "qwen" provider
                # with "openai-responses" API at runtime, based on model name
                # matching — regardless of which provider key we wrote.  This
                # would override our "qwen/openai-completions" config, which is
                # the correct protocol for DashScope's OpenAI-compat endpoint.
                # Disabling the plugin ensures our provider config is used as-is.
                # models.mode=merge alone does not suppress the plugin's runtime
                # API-type override.
                + (
                    "d.setdefault('plugins', {}).setdefault('entries', {})['qwen'] = {'enabled': False}\n"
                    if provider_str == "dashscope" else ""
                )
                # ── tools ─────────────────────────────────────────────────
                # Allow all tools by default; restrictive defaults may silently
                # block shell/browser tools the agent needs for tasks.
                + "d.setdefault('tools', {})['allow'] = ['*']\n"
                # ── write ─────────────────────────────────────────────────
                + "json.dump(d, open(p, 'w'), indent=2)\n"
                + f"print('configured openclaw.json: provider=' + {json.dumps(openclaw_provider)} "
                + f"+ ' model=' + {json.dumps(model_name)})\n"
            )
            await environment.write_file("/tmp/patch_openclaw.py", patch_script)
            patch_result = await environment.execute_command(
                f"export QWEN_API_KEY={shlex.quote(api_key)} "
                f"DASHSCOPE_API_KEY={shlex.quote(api_key)} && "
                "python3 /tmp/patch_openclaw.py",
                timeout=15,
            )
            if patch_result.get("returncode", 1) != 0:
                import logging
                logging.getLogger(__name__).warning(
                    "_configure_openclaw_json patch failed (exit %s):\n%s\n%s",
                    patch_result.get("returncode"),
                    (patch_result.get("stdout") or "")[:500],
                    (patch_result.get("stderr") or "")[:500],
                )
        except Exception:
            import logging
            logging.getLogger(__name__).exception("_configure_openclaw_json failed")

    # ── gateway helpers ────────────────────────────────────────────────────────

    async def _stabilise_gateway_plugins(self, environment: BaseEnvironment) -> None:
        """Patch the openclaw image so the gateway survives in a Docker container.

        Two issues block the browser-plugin path on a bare ``openclaw-pawbench``
        image and would otherwise be silent failures:

        1. ``bonjour`` (mDNS service advertisement, via ``@homebridge/ciao``)
           tries to broadcast on multicast, which Docker's default bridge does
           not support.  After ~20 s the ``CIAO ANNOUNCEMENT CANCELLED``
           rejection is unhandled and crashes the entire gateway process,
           leaving every subsequent WS request hanging on a 1006 close.
        2. The bundled ``browser`` plugin requires runtime deps
           (``playwright-core``, ``express``, ``undici``,
           ``@modelcontextprotocol/sdk``) that the image may not ship.
           ``openclaw doctor --fix`` is the official way to install just the
           missing ones; it is idempotent on a fully populated image.

        Without these two patches, ``ws://127.0.0.1:18789`` drops every
        browser-related call after the first request — the symptom diagnosed
        on ``gui_002_zh`` (62.5% score, "browser gateway not running").
        """
        await environment.execute_command(
            "openclaw config set plugins.entries.bonjour.enabled false 2>&1 | tail -2 || true",
            timeout=90,
        )
        await environment.execute_command(
            "openclaw doctor --fix 2>&1 | tail -5 || true",
            timeout=180,
        )

    async def _ensure_gateway(self, environment: BaseEnvironment, *, api_key: str = "") -> None:
        port = _GATEWAY_PORT

        # TCP-based liveness check: verify the gateway port is actually accepting
        # connections, not just that a process with the saved PID exists.
        # A PID-only check misses "half-dead" gateways where the process is alive
        # but the port has stopped responding (e.g. after an internal crash or
        # deadlock).  A bare TCP connect is sufficient — we don't need a full WS
        # handshake, and a 1006 WS rejection would still mean the port is open.
        tcp_check = (
            'python3 -c "'
            "import socket\n"
            f"s = socket.socket(); s.settimeout(2)\n"
            "try:\n"
            f"  s.connect(('127.0.0.1', {port})); print('ALIVE')\n"
            "except Exception: print('DEAD')\n"
            "finally:\n"
            "  try: s.close()\n"
            "  except Exception: pass\n"
            '"'
        )
        r = await environment.execute_command(tcp_check, timeout=5)
        if "ALIVE" in (r.get("stdout") or ""):
            return

        # Gateway not running (or PID dead after a crash).  Kill any stale
        # zombie/orphan processes before starting a fresh one.
        await environment.execute_command(
            "pkill -9 -f 'openclaw gateway' 2>/dev/null; "
            "pkill -9 -f 'openclaw-gateway' 2>/dev/null; "
            "sleep 0.5; true",
            timeout=8,
        )

        # OPENCLAW_DISABLE_BONJOUR=1 prevents the bonjour/ciao mDNS advertiser
        # from running.  In a Docker container the default bridge network does
        # not support multicast; when bonjour tries to announce and fails,
        # `installCiaoUnhandledRejectionListener` may re-throw the rejection as
        # an uncaught exception, crashing the gateway process and leaving every
        # subsequent WebSocket connection with a 1006 abnormal closure.
        await environment.execute_command(
            f"export QWEN_API_KEY={shlex.quote(api_key)} && "
            f"export DASHSCOPE_API_KEY={shlex.quote(api_key)} && "
            f"export OPENAI_API_KEY={shlex.quote(api_key)} && "
            "export OPENCLAW_DISABLE_BONJOUR=1 && "
            "nohup openclaw gateway >/tmp/openclaw_gateway.log 2>&1 & "
            "echo $! >/tmp/openclaw_gateway.pid || true",
            timeout=10,
        )

        # Allow up to 45 s for the gateway to install plugin deps and start
        # listening.  On a warm container (deps already cached) this is < 2 s.
        wait_cmd = (
            f'python3 -c "'
            "import socket, time; "
            f"deadline=time.time()+45; ok=False\n"
            "while time.time()<deadline:\n"
            f"  s=socket.socket(); s.settimeout(0.3)\n"
            f"  try: s.connect(('127.0.0.1',{port})); ok=True; break\n"
            f"  except Exception: time.sleep(0.3)\n"
            f"  finally:\n"
            f"    try: s.close()\n"
            f"    except Exception: pass\n"
            "print('GATEWAY_READY' if ok else 'GATEWAY_NOT_READY')\""
        )
        await environment.execute_command(wait_cmd, timeout=55)

    async def _ensure_gateway_strict(self, environment: BaseEnvironment, *, api_key: str = "") -> None:
        """Stronger gateway start used for the browser-plugin investigation.

        Currently NOT called from ``setup()``.  Kept here so we can swap
        ``_ensure_gateway → _ensure_gateway_strict`` once the gateway-stability
        work is completed.

        Differences from ``_ensure_gateway``:

        * Always force-restarts the gateway instead of trusting a port probe
          (a half-dead gateway can keep 18789 listening but reject WS
          sessions with 1006).
        * Polls ``openclaw browser doctor`` instead of a raw socket connect,
          so it returns only when the browser plugin is actually serving
          requests (~15 s after the log line ``ready``).
        """
        await environment.execute_command(
            "pkill -9 -f 'openclaw gateway' 2>/dev/null; "
            "pkill -9 -f 'openclaw-gateway' 2>/dev/null; "
            "sleep 1; true",
            timeout=10,
        )

        await environment.execute_command(
            f"export QWEN_API_KEY={shlex.quote(api_key)} && "
            f"export DASHSCOPE_API_KEY={shlex.quote(api_key)} && "
            f"export OPENAI_API_KEY={shlex.quote(api_key)} && "
            "export OPENCLAW_DISABLE_BONJOUR=1 && "
            "rm -f /tmp/openclaw_gateway.log && "
            "nohup openclaw gateway >/tmp/openclaw_gateway.log 2>&1 & "
            "echo $! >/tmp/openclaw_gateway.pid || true",
            timeout=10,
        )

        wait_cmd = (
            "for i in $(seq 1 60); do "
            "  if openclaw browser doctor 2>&1 | "
            "     grep -q 'OK gateway: browser control endpoint reachable'; then "
            "    echo GATEWAY_READY; exit 0; "
            "  fi; "
            "  sleep 1; "
            "done; "
            "echo GATEWAY_NOT_READY; "
            "tail -25 /tmp/openclaw_gateway.log 2>/dev/null || true"
        )
        await environment.execute_command(wait_cmd, timeout=75)

    # ── run ───────────────────────────────────────────────────────────────────

    async def run(self, instruction: str, environment: BaseEnvironment) -> Dict[str, Any]:
        model_identifier = self.config.get("model", "dashscope/qwen3.6-plus")
        rc = get_model_config(model_identifier).resolve_with(self.config)
        api_key = rc.api_key
        model_config = rc.model_config

        agent_id = self._agent_id()
        agent_id_lower = agent_id.lower()

        # Wipe sessions from any previous run so openclaw starts a fresh
        # conversation for this task.
        await environment.execute_command(
            f"rm -f /root/.openclaw/agents/{agent_id_lower}/sessions/*.jsonl "
            f"/root/.openclaw/agents/{agent_id_lower}/sessions/*.jsonl.lock "
            f"/root/.openclaw/agents/{agent_id_lower}/sessions/sessions.json "
            "2>/dev/null || true",
            timeout=15,
        )

        # Re-check gateway liveness before each task (it may have crashed).
        await self._ensure_gateway(environment, api_key=api_key)

        # Verify the agent is actually known to the gateway.  In rare cases
        # (inotify exhaustion, timing) the gateway starts without the agent
        # config loaded.  Re-add + restart the gateway when that happens.
        openclaw_model = self._openclaw_model_id(model_identifier)
        env_prefix = (
            f"export QWEN_API_KEY={shlex.quote(api_key)} "
            f"DASHSCOPE_API_KEY={shlex.quote(api_key)} && "
        )
        check_result = await environment.execute_command(
            f"{env_prefix}openclaw agents list 2>&1 || true",
            timeout=30,
        )
        check_output = (check_result.get("stdout") or "") + (check_result.get("stderr") or "")
        if agent_id.lower() not in check_output.lower():
            import logging
            logging.getLogger(__name__).warning(
                "Agent %s not found in 'openclaw agents list' at run() start — re-adding and restarting gateway",
                agent_id,
            )
            await environment.execute_command(
                f"{env_prefix}"
                f"openclaw agents add {shlex.quote(agent_id)} "
                f"--model {shlex.quote(openclaw_model)} "
                f"--workspace {shlex.quote(AGENT_WORKSPACE)} "
                "--non-interactive",
                timeout=120,
            )
            # Restore gateway.mode which agents add may have dropped.
            await environment.write_file(
                "/tmp/patch_gateway_mode.py",
                "import json, os\n"
                "p = '/root/.openclaw/openclaw.json'\n"
                "d = json.load(open(p)) if os.path.exists(p) else {}\n"
                "d.setdefault('gateway', {})['mode'] = 'local'\n"
                "json.dump(d, open(p, 'w'), indent=2)\n"
                "print('gateway.mode ensured')\n",
            )
            await environment.execute_command(
                "python3 /tmp/patch_gateway_mode.py",
                timeout=10,
            )
            # Force-restart gateway to load the newly written config.
            await environment.execute_command(
                "pkill -9 -f 'openclaw gateway' 2>/dev/null; "
                "pkill -9 -f 'openclaw-gateway' 2>/dev/null; "
                "sleep 0.5; true",
                timeout=8,
            )
            await environment.execute_command(
                f"export QWEN_API_KEY={shlex.quote(api_key)} && "
                f"export DASHSCOPE_API_KEY={shlex.quote(api_key)} && "
                f"export OPENAI_API_KEY={shlex.quote(api_key)} && "
                "export OPENCLAW_DISABLE_BONJOUR=1 && "
                "nohup openclaw gateway >/tmp/openclaw_gateway.log 2>&1 & "
                "echo $! >/tmp/openclaw_gateway.pid || true",
                timeout=10,
            )
            wait_cmd = (
                f'python3 -c "'
                "import socket, time; "
                f"deadline=time.time()+45; ok=False\n"
                "while time.time()<deadline:\n"
                f"  s=socket.socket(); s.settimeout(0.3)\n"
                f"  try: s.connect(('127.0.0.1',18789)); ok=True; break\n"
                f"  except Exception: time.sleep(0.3)\n"
                f"  finally:\n"
                f"    try: s.close()\n"
                f"    except Exception: pass\n"
                "print('GATEWAY_READY' if ok else 'GATEWAY_NOT_READY')\""
            )
            await environment.execute_command(wait_cmd, timeout=55)

        # Remove BOOTSTRAP.md / SOUL.md from the task workspace so they don't
        # distract the agent with openclaw-specific onboarding instructions.
        # Enabled by default (skip_bootstrap defaults to True); pass
        # skip_bootstrap=False in agent_config to keep the files.
        if self.config.get("skip_bootstrap", True):
            await environment.execute_command(
                f"rm -f {AGENT_WORKSPACE}/BOOTSTRAP.md 2>/dev/null || true",
                timeout=10,
            )

        escaped = shlex.quote(instruction)
        session_id = f"pawbench-{int(time.time() * 1000)}"

        inner_timeout = int(self.config.get("task_timeout_s") or 1800)

        thinking_level = (
            self.config.get("thinking_level") or self.config.get("thinking") or ""
        )
        thinking_args = (
            f"--thinking {shlex.quote(thinking_level)} " if thinking_level else ""
        )

        run_cmd = (
            f"export QWEN_API_KEY={shlex.quote(api_key)} && "
            f"export OPENAI_API_KEY={shlex.quote(api_key)} && "
            f"export DASHSCOPE_API_KEY={shlex.quote(api_key)} && "
            f"cd {shlex.quote(AGENT_WORKSPACE)} && "
            f"timeout {inner_timeout}s openclaw agent "
            f"--agent {shlex.quote(agent_id)} --session-id {session_id} "
            f"{thinking_args}--message {escaped} "
            f"2>&1 | tee /tmp/openclaw_output.txt || true"
        )
        result = await environment.execute_command(run_cmd, timeout=inner_timeout + 60)
        output_content = (
            await environment.read_file("/tmp/openclaw_output.txt") or result["stdout"]
        )

        # Copy openclaw session files into workspace/sessions/ so that
        # extract_transcript() can find them.  Trajectory files are preferred
        # (they carry the full messagesSnapshot); plain session JSONL files are
        # copied as a fallback for older openclaw builds.
        await environment.execute_command(
            f"mkdir -p {AGENT_WORKSPACE}/sessions && "
            f"sessions_dir=/root/.openclaw/agents/{agent_id_lower}/sessions && "
            "for f in \"$sessions_dir\"/*.trajectory.jsonl; do "
            '  [ -f "$f" ] || continue; '
            f'  cp "$f" "{AGENT_WORKSPACE}/sessions/"; '
            "done && "
            "for f in \"$sessions_dir\"/*.jsonl; do "
            '  [ -f "$f" ] || continue; '
            '  case "$f" in *.trajectory.jsonl) continue;; esac; '
            f'  cp "$f" "{AGENT_WORKSPACE}/sessions/"; '
            "done",
            timeout=15,
        )

        await self._sync_workspace_to_output(environment, AGENT_WORKSPACE)

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
                "model_name": model_config.model_name,
                "session_id": session_id,
            },
        }

    async def teardown(self, environment: BaseEnvironment) -> None:
        agent_id = self._agent_id()
        await environment.execute_command(
            f"openclaw agents delete {shlex.quote(agent_id)} --force 2>/dev/null || true",
            timeout=60,
        )
        await environment.execute_command(
            "rm -f /tmp/openclaw_output.txt /tmp/patch_openclaw.py",
            timeout=10,
        )

    @property
    def version(self) -> str:
        return "2026.4.24"
