# -*- coding: utf-8 -*-
"""PawBench backend — load, run and grade pawbench tasks.

Expected directory layout
-------------------------
<benchmark_path>/                   ← benchmarks/pawbench/
  data/
    claw-eval-converted/            ← default dataset
      tasks/
        task_*.md
      assets/
        ...
    wildclaw-converted/             ← optional second dataset
      tasks/
        task_*.md
      assets/
        ...

Run with copaw agent (default)::

    python run_bench.py --model openai/gpt-4o

Run with OpenClaw Docker agent::

    python run_bench.py --agents openclaw --model dashscope/qwen3.6-plus

Run a specific dataset::

    python run_bench.py --dataset wildclaw-converted --model openai/gpt-4o

agent_config keys
-----------------
model              str   (required) Model identifier
agent_type         str   ``"copaw"`` (default) or ``"openclaw"``
dataset            str   Dataset name under ``data/`` (default: claw-eval-converted)
docker_image       str   Docker image override
timeout_multiplier float  Scale task timeouts (default: 1.0)
thinking_level     str   [openclaw] Thinking level (low/medium/high/xhigh)
api_key            str   [copaw] API key forwarded to the agent
base_url           str   [copaw] OpenAI-compatible base URL
judge_model        str   Model used for LLM-judge grading
verbose            bool  Verbose logging (default: False)
"""

from __future__ import annotations

import asyncio
import os
import shlex
import shutil
import subprocess
import tempfile
import time
import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .utils.anomalies import detect_anomalies
from .agents.factory import AgentFactory
from .grader import grade_task
from .task_loader import TaskLoader


@dataclass
class TaskResult:
    """Unified result returned by the backend after running one task."""

    task_id: str
    task_name: str
    score: float
    max_score: float
    passed: bool
    grading_type: str
    breakdown: dict[str, float]
    notes: str
    execution_time: float
    status: str          # "success" | "timeout" | "error"
    usage: dict[str, Any]
    transcript_length: int
    timed_out: bool
    error: str = ""
    transcript: list = field(default_factory=list)
    # Anomaly detection result (from anomalies.detect_anomalies).
    # has_error=True means the score is unreliable (API quota, OOM, etc.).
    anomaly: dict = field(default_factory=dict)
    # Task labels copied from the task's YAML front-matter ``labels:`` block.
    labels: dict = field(default_factory=dict)


class BenchmarkBackend(ABC):
    """Abstract contract for a benchmark backend.

    Concrete subclasses are expected to delegate task execution and grading to
    the benchmark's own libraries.  Currently :class:`PawBenchBackend` is the
    only implementation, but the ABC documents the contract should additional
    backends be added in the future.
    """

    def __init__(self, benchmark_path: str | Path) -> None:
        self.benchmark_path = Path(benchmark_path).resolve()
        if not self.benchmark_path.exists():
            raise FileNotFoundError(
                f"Benchmark path not found: {self.benchmark_path}"
            )

    @property
    @abstractmethod
    def name(self) -> str:
        """Short identifier, e.g. ``'pawbench'``."""

    @abstractmethod
    def load_tasks(
        self,
        task_filter: list[str] | None = None,
        **kwargs: Any,
    ) -> list[Any]:
        """Load native Task objects from the benchmark directory."""

    @abstractmethod
    def run_and_grade(
        self,
        task: Any,
        agent_config: dict[str, Any],
    ) -> TaskResult:
        """Execute *task* and grade the result."""


class PawBenchBackend(BenchmarkBackend):
    """Run and grade pawbench tasks.

    Supported agent types (``--agents`` / ``agent_config["agent_type"]``):

    * ``"copaw"`` (default) — QwenPaw HTTP-API agent.
      Default image: ``qwenclawbench-copaw:latest``
      (docker/Dockerfile.qwenclawbench-copaw)

    * ``"openclaw"`` — OpenClaw CLI agent (``openclaw agent --message``).
      Default image: ``openclaw-pawbench:latest``
      (examples/upstream/docker/Dockerfile.pawbench-openclaw — has pre-configured
      qwen provider and gateway auth; use ``docker/Dockerfile.openclaw`` only as
      a base for building this image, NOT directly for evaluation)

    * ``"hermes"`` — Hermes Agent v0.11 (``hermes chat -q … --yolo``).
      Default image: ``hermes-qwenclawbench:latest``
      (docker/Dockerfile.hermes — built from qwenclawbench family)
    """

    DEFAULT_DATASET = "claw-eval-converted"

    @property
    def name(self) -> str:
        return "pawbench"

    # ── public API ────────────────────────────────────────────────────────────

    def load_tasks(
        self,
        task_filter: list[str] | None = None,
        dataset: str | None = None,
        **_kwargs: Any,
    ) -> list[Any]:
        ds = dataset or self.DEFAULT_DATASET
        tasks_dir = self.benchmark_path / "data" / ds / "tasks"
        if not tasks_dir.exists():
            raise FileNotFoundError(
                f"pawbench tasks directory not found: {tasks_dir}\n"
                f"Expected: <benchmark_path>/data/{ds}/tasks/"
            )
        loader = TaskLoader(tasks_dir)
        tasks = loader.load_all_tasks()
        if task_filter:
            tasks = [
                t for t in tasks
                if t.task_id in task_filter
                or any(t.task_id.startswith(f) for f in task_filter)
            ]
        return tasks

    def run_and_grade(
        self,
        task: Any,
        agent_config: dict[str, Any],
    ) -> TaskResult:
        task_timeout_s = getattr(task, "timeout_seconds", 300)
        timeout_multiplier = float(agent_config.get("timeout_multiplier", 1.0))
        scaled_task_timeout = int(task_timeout_s * timeout_multiplier)
        # Three concentric layers, all derived from the task's own timeout:
        #   inner  : the in-container `timeout Ns hermes/openclaw …` shell command
        #   middle : docker exec wall-clock (inner + 60s grace)
        #   outer  : asyncio.wait_for in this method (inner + 600s grace)
        # Earlier versions hard-coded the inner/middle layer to 660/720s, which
        # silently capped any task whose own ``timeout_seconds`` was larger. We
        # now propagate the true value via ``agent_config``.
        agent_config = {
            **agent_config,
            "task_timeout_s": scaled_task_timeout,
        }
        agent = AgentFactory.create(agent_config)
        hard_limit = scaled_task_timeout + 600
        try:
            return asyncio.run(
                asyncio.wait_for(
                    self._run_agent_async(task, agent, agent_config),
                    timeout=hard_limit,
                )
            )
        except (asyncio.TimeoutError, TimeoutError):
            return TaskResult(
                task_id=task.task_id,
                task_name=getattr(task, "name", task.task_id),
                score=0.0, max_score=1.0, passed=False,
                grading_type="error", breakdown={}, notes="",
                execution_time=float(hard_limit),
                status="error", usage={}, transcript_length=0,
                timed_out=True,
                error=f"Task exceeded hard wall-clock limit of {hard_limit}s",
                labels=getattr(task, "labels", {}),
            )


    # ── unified docker-agent execution ────────────────────────────────────────

    async def _run_agent_async(
        self,
        task: Any,
        agent: Any,
        agent_config: dict[str, Any],
    ) -> TaskResult:
        """Generic async runner: stage files → setup → run → collect → grade.

        Works for all agent types (copaw / openclaw / hermes).  Agent-specific
        behaviour (workspace symlinks, session conversion, transcript building)
        is delegated to the agent class via ``setup()``, ``post_run_collect()``
        and ``extract_transcript()``.
        """
        from pawbench.envs.docker import DockerEnvironment

        api_key = agent_config.get("api_key") or os.environ.get("OPENAI_API_KEY", "")
        base_url = agent_config.get("base_url") or os.environ.get(
            "OPENAI_BASE_URL", "https://api.openai.com/v1"
        )
        dataset = agent_config.get("dataset", self.DEFAULT_DATASET)
        judge_model = agent_config.get("judge_model")
        verbose = bool(agent_config.get("verbose", False))
        docker_image = (
            agent_config.get("docker_image")
            or AgentFactory.default_image_for_type(agent_config.get("agent_type", "copaw"))
        )

        assets_dir = self.benchmark_path / "data" / dataset / "assets"
        container_name = f"pawbench-{agent.name}-{task.task_id}-{uuid.uuid4().hex[:8]}"

        env = DockerEnvironment(
            name=container_name,
            image=docker_image,
            environment_vars={
                "OPENAI_API_KEY": api_key,
                "OPENAI_BASE_URL": base_url,
                "DASHSCOPE_API_KEY": api_key,
            },
        )

        t0 = time.time()
        local_workspace: Path | None = None
        stdout_output = ""
        exit_ok = False

        try:
            await env.start()
            await env.execute_command(
                "mkdir -p /app/working/workspaces/default/output "
                "/app/working/workspaces/default/sessions"
            )

            # Stage task workspace files into the container.
            for file_spec in getattr(task, "workspace_files", []):
                if "content" in file_spec:
                    dest = f"/app/working/workspaces/default/{file_spec['path']}"
                    await env.write_file(dest, file_spec["content"])
                elif "source" in file_spec and "dest" in file_spec:
                    source_rel = file_spec["source"]
                    src: Path | None = None
                    # Datasets such as pawbench-v1.0 use sources like
                    # "assets/T042_.../fixtures/...".  *assets_dir* already ends
                    # in ".../assets", so joining the full *source_rel* yields a
                    # non-existent ".../assets/assets/..." path.  Strip a leading
                    # "assets/" when present.
                    source_rel_stripped = (
                        source_rel[len("assets/") :]
                        if source_rel.startswith("assets/")
                        else source_rel
                    )
                    for candidate in [
                        assets_dir / task.task_id / source_rel,
                        assets_dir / source_rel,
                        assets_dir / source_rel_stripped,
                        assets_dir / task.task_id / source_rel_stripped,
                    ]:
                        if candidate.exists():
                            src = candidate
                            break
                    if src is not None:
                        container_dest = f"/app/working/workspaces/default/{file_spec['dest']}"
                        await env.execute_command(
                            f"mkdir -p {shlex.quote(str(Path(container_dest).parent))}"
                        )
                        await env.copy_to(src, container_dest)
                    elif verbose:
                        print(f"  [{agent.name}] WARNING: workspace file not found: {source_rel}")

            await agent.setup(env)
            run_result = await agent.run(task.prompt, env)
            stdout_output = run_result.get("output", "")
            exit_ok = run_result.get("success", False)

            # Let the agent sync any agent-internal dirs into the standard workspace.
            await agent.post_run_collect(env)

            local_workspace = Path(tempfile.mkdtemp(prefix=f"pawbench_{task.task_id}_"))
            # Primary copy: full workspace tree (includes sessions/, output/, etc.)
            subprocess.run(
                ["docker", "cp",
                 f"{container_name}:/app/working/workspaces/default/.",
                 str(local_workspace)],
                capture_output=True, text=True,
            )
            # Secondary copy: flatten output/ files to workspace root so graders
            # that look at the workspace root can find them directly.
            subprocess.run(
                ["docker", "cp",
                 f"{container_name}:/app/working/workspaces/default/output/.",
                 str(local_workspace)],
                capture_output=True, text=True,
            )

            # Merge workspace/ subdir if docker cp created one inside local_workspace.
            workspace_subdir = local_workspace / "workspace"
            if workspace_subdir.is_dir():
                for src_file in workspace_subdir.rglob("*"):
                    if not src_file.is_file():
                        continue
                    rel = src_file.relative_to(workspace_subdir)
                    dest_file = local_workspace / rel
                    dest_file.parent.mkdir(parents=True, exist_ok=True)
                    if not dest_file.exists() or dest_file.stat().st_size == 0:
                        shutil.copy2(src_file, dest_file)

        except Exception as exc:
            return TaskResult(
                task_id=task.task_id,
                task_name=getattr(task, "name", task.task_id),
                score=0.0, max_score=1.0, passed=False,
                grading_type="error", breakdown={}, notes="",
                execution_time=time.time() - t0,
                status="error", usage={}, transcript_length=0,
                timed_out=False, error=str(exc),
                labels=getattr(task, "labels", {}),
            )
        finally:
            try:
                await agent.teardown(env)
            except Exception:
                pass
            docker_images_save_dir = agent_config.get("docker_images_save_dir")
            if docker_images_save_dir and env.container_id:
                _save_docker_image(container_name, task.task_id, Path(docker_images_save_dir))
            try:
                await env.stop()
            except Exception:
                pass

        transcript = agent.extract_transcript(local_workspace, stdout_output)

        # Prepend a system message when the agent captured a system prompt
        # during post_run_collect() and the transcript doesn't already open
        # with one (openclaw handles its own injection via trajectory JSONL).
        system_prompt = agent.get_system_prompt()
        if system_prompt and transcript:
            first_role = ""
            first_msg = transcript[0]
            if first_msg.get("type") == "message":
                first_role = (first_msg.get("message") or {}).get("role", "")
            if first_role != "system":
                transcript.insert(0, {
                    "type": "message",
                    "message": {
                        "role": "system",
                        "content": [{"type": "text", "text": system_prompt}],
                    },
                })

        execution_result: dict[str, Any] = {
            "agent_id": agent.name,
            "task_id": task.task_id,
            "status": "success" if exit_ok else "error",
            "transcript": transcript,
            "usage": {},
            "workspace": str(local_workspace) if local_workspace else "",
            "exit_code": 0 if exit_ok else 1,
            "timed_out": False,
            "execution_time": time.time() - t0,
            "stdout": stdout_output,
            "stderr": "",
        }

        judge_api_key = agent_config.get("judge_api_key") or api_key
        judge_base_url = agent_config.get("judge_base_url") or base_url

        grade_notes = ""
        try:
            grade = _grade_with_credentials(
                task=task,
                execution_result=execution_result,
                judge_model=judge_model,
                api_key=judge_api_key,
                base_url=judge_base_url,
                verbose=verbose,
            )
            grade_notes = getattr(grade, "notes", "")
        except Exception as exc:
            grade = _StubGrade(task.task_id, f"Grading failed: {exc}")
            grade_notes = grade.notes
        finally:
            if local_workspace and local_workspace.exists():
                workspace_save_dir = agent_config.get("workspace_save_dir")
                if workspace_save_dir:
                    dest = Path(workspace_save_dir) / task.task_id
                    # Best-effort save. Two real races we've hit:
                    #   1. Chrome/Chromium creates SingletonLock/SingletonSocket/
                    #      SingletonCookie as symlinks pointing to
                    #      "<container_hostname>-<pid>". After ``docker cp`` to
                    #      the host these become DANGLING symlinks (target lives
                    #      only inside the container). With ``symlinks=False``
                    #      (the default) ``shutil.copytree`` follows the symlink,
                    #      hits ENOENT, and aggregates the per-file errors into
                    #      one ``shutil.Error`` at the end of the walk.
                    #   2. Random transient OSError on tmpfs / overlayfs.
                    # In either case we ALREADY have a graded result; we MUST
                    # NOT let a workspace-archive failure inside ``finally``
                    # cancel the function's normal return path (which would
                    # otherwise propagate the exception up to BenchmarkRunner
                    # and turn the row into ``status=error``).
                    try:
                        shutil.copytree(
                            str(local_workspace), str(dest),
                            dirs_exist_ok=True,
                            ignore_dangling_symlinks=True,
                        )
                        print(f"  [{agent.name}] workspace saved to {dest}")
                    except (shutil.Error, OSError) as exc:
                        # ``shutil.Error.args[0]`` is a list of (src, dst, msg)
                        # tuples — keep only the count to avoid log spam.
                        n_errs = len(exc.args[0]) if (
                            isinstance(exc, shutil.Error) and exc.args and
                            isinstance(exc.args[0], list)
                        ) else 1
                        print(
                            f"  [{agent.name}] workspace partial save to {dest} "
                            f"({n_errs} entries skipped: {type(exc).__name__})"
                        )
                if os.environ.get("PAWBENCH_KEEP_WORKSPACE"):
                    print(f"  [{agent.name}] workspace kept at {local_workspace}")
                else:
                    shutil.rmtree(local_workspace, ignore_errors=True)

        anomaly = detect_anomalies(execution_result, grade_notes)

        return TaskResult(
            task_id=task.task_id,
            task_name=getattr(task, "name", task.task_id),
            score=grade.score, max_score=grade.max_score,
            passed=grade.score >= grade.max_score,
            grading_type=grade.grading_type,
            breakdown=getattr(grade, "breakdown", {}),
            notes=grade_notes,
            execution_time=execution_result["execution_time"],
            status=execution_result["status"],
            usage={},
            transcript_length=len(transcript),
            timed_out=False,
            transcript=transcript,
            anomaly=anomaly,
            labels=getattr(task, "labels", {}),
        )


# ── helpers ───────────────────────────────────────────────────────────────────

def _save_docker_image(container_name: str, task_id: str, save_dir: Path) -> None:
    """Commit a running container and export it as a .tar file.

    Steps:
      1. ``docker commit <container_name> <tmp_tag>``
      2. ``docker save <tmp_tag> -o <save_dir>/<task_id>.tar``
      3. ``docker rmi <tmp_tag>``  (clean up the ephemeral image layer)

    Errors are printed but never re-raised so a failed save never turns a
    passing task into an error result.
    """
    safe_task_id = task_id.replace("/", "_").replace(":", "_")
    tmp_tag = f"pawbench-snapshot-{safe_task_id}:{uuid.uuid4().hex[:8]}"
    out_path = save_dir / f"{safe_task_id}.tar"
    try:
        commit_res = subprocess.run(
            ["docker", "commit", container_name, tmp_tag],
            capture_output=True, text=True,
        )
        if commit_res.returncode != 0:
            print(
                f"  [docker-save] WARNING: docker commit failed for {container_name}: "
                f"{commit_res.stderr.strip()}"
            )
            return
        save_res = subprocess.run(
            ["docker", "save", tmp_tag, "-o", str(out_path)],
            capture_output=True, text=True,
        )
        if save_res.returncode != 0:
            print(
                f"  [docker-save] WARNING: docker save failed for {tmp_tag}: "
                f"{save_res.stderr.strip()}"
            )
        else:
            print(f"  [docker-save] image saved → {out_path}")
    except Exception as exc:
        print(f"  [docker-save] WARNING: unexpected error saving image for {task_id}: {exc}")
    finally:
        subprocess.run(["docker", "rmi", "-f", tmp_tag], capture_output=True)


def _grade_with_credentials(
    *,
    task: Any,
    execution_result: dict[str, Any],
    judge_model: str | None,
    api_key: str | None,
    base_url: str | None,
    verbose: bool,
) -> Any:
    """Call grade_task with JUDGE_BASE_URL / JUDGE_API_KEY injected into env."""
    kwargs: dict[str, Any] = dict(
        task=task, execution_result=execution_result,
        verbose=verbose,
    )
    if judge_model:
        kwargs["judge_model"] = judge_model

    if not api_key or not base_url:
        return grade_task(**kwargs)

    saved = {
        "JUDGE_BASE_URL": os.environ.get("JUDGE_BASE_URL"),
        "JUDGE_API_KEY": os.environ.get("JUDGE_API_KEY"),
    }
    os.environ["JUDGE_BASE_URL"] = base_url
    os.environ["JUDGE_API_KEY"] = api_key
    try:
        return grade_task(**kwargs)
    finally:
        for key, val in saved.items():
            if val is not None:
                os.environ[key] = val
            elif key in os.environ:
                del os.environ[key]


class _StubGrade:
    def __init__(self, task_id: str, notes: str) -> None:
        self.task_id = task_id
        self.score = 0.0
        self.max_score = 1.0
        self.grading_type = "error"
        self.breakdown: dict[str, float] = {}
        self.notes = notes
