# -*- coding: utf-8 -*-
"""BenchmarkRunner — orchestrates execution of native benchmark backends.

The runner wraps the sync ``backend.run_and_grade()`` calls in
``asyncio.to_thread`` so they don't block the event loop and can be run
concurrently when ``concurrency > 1``.
"""

from __future__ import annotations

import asyncio
import json
import sys
import time
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any

from .backend import BenchmarkBackend, TaskResult


class BenchmarkRunner:
    """Run a native benchmark backend against one agent configuration.

    Args:
        backend:     An instantiated :class:`BenchmarkBackend`.
        results_dir: Directory where JSON result files are written.
        concurrency: Maximum number of tasks to execute in parallel.
        max_retries: How many times to retry a failed or timed-out task
                     before giving up (default 1 = no retry).
    """

    def __init__(
        self,
        backend: BenchmarkBackend,
        results_dir: str | Path = "./results",
        concurrency: int = 1,
        max_retries: int = 1,
    ) -> None:
        self.backend = backend
        self.results_dir = Path(results_dir)
        self.results_dir.mkdir(parents=True, exist_ok=True)
        self.concurrency = max(1, concurrency)
        self.max_retries = max(1, max_retries)

    # ── public API ────────────────────────────────────────────────────────────

    async def run(
        self,
        agent_config: dict[str, Any],
        task_filter: list[str] | None = None,
        **load_kwargs: Any,
    ) -> list[TaskResult]:
        """Execute all (or filtered) tasks and return results.

        Args:
            agent_config: Dict passed to ``backend.run_and_grade()``.
                          Must contain at minimum ``"model"``.
            task_filter:  Optional list of task IDs to run.
            **load_kwargs: Extra kwargs forwarded to ``backend.load_tasks()``
                           (e.g. ``dataset="..."`` for QwenClawBench).
        """
        tasks = self.backend.load_tasks(task_filter, **load_kwargs)
        if not tasks:
            print(f"[{self.backend.name}] No tasks loaded — nothing to run.")
            return []

        print(f"[{self.backend.name}] {len(tasks)} task(s) loaded"
              + (f", filter={task_filter}" if task_filter else ""))

        # Generate stable paths before any task runs so checkpoints accumulate
        # in the same file even if the process is interrupted mid-run.
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        checkpoint_path = self.results_dir / f"{ts}.json"
        transcripts_dir = self.results_dir / "transcripts"
        transcripts_dir.mkdir(parents=True, exist_ok=True)

        results: list[TaskResult] = []

        workspaces_dir: Path | None = None
        if agent_config.get("save_workspace"):
            workspaces_dir = self.results_dir / "workspaces"
            workspaces_dir.mkdir(parents=True, exist_ok=True)

        docker_images_dir: Path | None = None
        if agent_config.get("save_docker_image"):
            docker_images_dir = self.results_dir / "docker_images"
            docker_images_dir.mkdir(parents=True, exist_ok=True)

        if self.concurrency == 1:
            for idx, task in enumerate(tasks, 1):
                print(f"\n  [{idx}/{len(tasks)}] {task.task_id}")
                cfg = {**agent_config, "run_id": str(idx)}
                if workspaces_dir is not None:
                    cfg["workspace_save_dir"] = str(workspaces_dir)
                if docker_images_dir is not None:
                    cfg["docker_images_save_dir"] = str(docker_images_dir)
                result = await self._run_with_retry(task, cfg)
                results.append(result)
                # Persist transcript and checkpoint immediately so a crash or
                # interrupt does not lose already-completed task data.
                _save_transcript(result, transcripts_dir)
                _write_checkpoint(results, agent_config, self.backend.name, checkpoint_path)
                # Bar reflects tasks completed so far (idx/len) after this one finishes
                self._print_progress_line(idx, len(tasks), task.task_id)
                self._print_result(result)
        else:
            sem = asyncio.Semaphore(self.concurrency)
            progress_lock = asyncio.Lock()
            n_tasks = len(tasks)
            done_count: list[int] = [0]  # mutable cell for async closure

            async def bounded(task: Any, idx: int) -> TaskResult:
                result: TaskResult
                try:
                    async with sem:
                        cfg = {**agent_config, "run_id": str(idx)}
                        if workspaces_dir is not None:
                            cfg["workspace_save_dir"] = str(workspaces_dir)
                        if docker_images_dir is not None:
                            cfg["docker_images_save_dir"] = str(docker_images_dir)
                        result = await self._run_with_retry(task, cfg)
                except BaseException as exc:
                    result = _error_result(task, str(exc), elapsed=0.0)
                async with progress_lock:
                    done_count[0] += 1
                    cur = done_count[0]
                    # Accumulate into the shared list before writing so each
                    # checkpoint contains ALL results completed so far, not just
                    # the current one (results + [result] would only write one
                    # entry per flush because results is empty until gather
                    # returns).
                    results.append(result)
                    _save_transcript(result, transcripts_dir)
                    _write_checkpoint(results, agent_config,
                                      self.backend.name, checkpoint_path)
                # Print as each task *finishes* (completion order), with a
                # one-line bar so logs show live progress (unlike a batched gather).
                self._print_progress_line(cur, n_tasks, task.task_id)
                self._print_result(result)
                return result

            gathered = await asyncio.gather(
                *[bounded(t, i + 1) for i, t in enumerate(tasks)],
                return_exceptions=True,
            )
            # results already populated inside bounded() under progress_lock.
            # Only handle tasks that raised an unexpected BaseException (they
            # were not appended there) to keep the list complete.
            completed_ids = {r.task_id for r in results}
            for task, outcome in zip(tasks, gathered):
                if isinstance(outcome, BaseException):
                    results.append(_error_result(task, str(outcome)))
                elif task.task_id not in completed_ids:
                    results.append(outcome)
            # per-task output already printed inside bounded (skip duplicate _print_result)

        self._print_summary(results)
        self._save_results(results, agent_config, checkpoint_path, transcripts_dir)
        return results

    # ── internals ─────────────────────────────────────────────────────────────

    async def _run_with_retry(self, task: Any, cfg: dict[str, Any]) -> TaskResult:
        """Execute a task with up to ``self.max_retries`` attempts.

        A retry is triggered when the result carries ``status == "error"``
        or ``timed_out == True``.  Passing results (score > 0 or
        status == "success") are returned immediately without further attempts.
        """
        last: TaskResult | None = None
        for attempt in range(1, self.max_retries + 1):
            if attempt > 1:
                print(f"    ↻ retry {attempt}/{self.max_retries} for {task.task_id}")
            last = await self._run_one(task, cfg)
            # Stop retrying on success or a meaningful score
            if last.status not in ("error",) and not last.timed_out:
                return last
            if attempt < self.max_retries:
                reason = "timed_out" if last.timed_out else f"status={last.status}"
                print(f"    ! attempt {attempt} failed ({reason}), will retry…")
        return last  # type: ignore[return-value]

    async def _run_one(self, task: Any, cfg: dict[str, Any]) -> TaskResult:
        t0 = time.time()
        try:
            return await asyncio.to_thread(self.backend.run_and_grade, task, cfg)
        except Exception as exc:
            print(f"    ERROR: {exc}")
            return _error_result(task, str(exc), elapsed=time.time() - t0)

    # ── output helpers ────────────────────────────────────────────────────────

    @staticmethod
    def _print_progress_line(done: int, total: int, task_id: str, width: int = 36) -> None:
        """One-line ASCII progress bar + counter (for log / nohup friendly)."""
        if total <= 0:
            return
        done = min(done, total)
        filled = int(width * done / total)
        filled = min(filled, width)
        bar = "#" * filled + "-" * (width - filled)
        pct = 100.0 * done / total
        line = (
            f"  [native] [{bar}]  {done:>3}/{total}  {pct:5.1f}%  ·  {task_id}"
        )
        print(line, flush=True, file=sys.stdout)

    @staticmethod
    def _print_result(r: TaskResult) -> None:
        mark = "✓" if r.passed else "✗"
        pct = r.score / r.max_score * 100 if r.max_score > 0 else 0.0
        parts = [
            f"    {mark}",
            f"score={r.score:.2f}/{r.max_score:.2f} ({pct:.0f}%)",
            f"elapsed={r.execution_time:.1f}s",
            f"[{r.grading_type}]",
            f"status={r.status}",
        ]
        if r.notes:
            parts.append(r.notes[:80])
        if r.error:
            parts.append(f"ERR:{r.error[:60]}")
        print("  ".join(parts))

    def _print_summary(self, results: list[TaskResult]) -> None:
        n = len(results)
        if n == 0:
            return
        passed = sum(1 for r in results if r.passed)
        avg = sum(r.score for r in results) / n
        total_time = sum(r.execution_time for r in results)
        bench = self.backend.name.upper()

        print(f"\n{'='*70}")
        print(f"  {bench} — {n} task(s)  passed={passed}/{n}  "
              f"avg_score={avg:.3f}  total_time={total_time:.1f}s")
        print("="*70)
        for r in sorted(results, key=lambda x: x.task_id):
            mark = "✓" if r.passed else "✗"
            pct = r.score / r.max_score * 100 if r.max_score > 0 else 0.0
            print(f"  {mark}  {r.task_id:<35}  {pct:5.1f}%  {r.status}")
        print("="*70)

        _print_label_report(results)

    def _save_results(
        self,
        results: list[TaskResult],
        agent_config: dict[str, Any],
        out_path: Path | None = None,
        transcripts_dir: Path | None = None,
    ) -> None:
        bench = self.backend.name
        model = agent_config.get("model", "unknown")
        if out_path is None:
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            out_path = self.results_dir / f"{ts}.json"
        if transcripts_dir is None:
            transcripts_dir = self.results_dir / "transcripts"
            transcripts_dir.mkdir(parents=True, exist_ok=True)

        _write_checkpoint(results, agent_config, bench, out_path)
        print(f"\n  Results → {out_path}")

        # Save any transcripts not yet persisted by the per-task checkpoint path.
        newly_written = 0
        for r in results:
            if r.transcript:
                traj_path = transcripts_dir / f"{r.task_id}.jsonl"
                if not traj_path.exists():
                    _save_transcript(r, transcripts_dir)
                    newly_written += 1
        if newly_written:
            print(f"  Transcripts → {transcripts_dir}/ ({newly_written} new file(s))")
        existing = sum(
            1 for r in results
            if r.transcript and (transcripts_dir / f"{r.task_id}.jsonl").exists()
        )
        if existing:
            print(f"  Transcripts → {transcripts_dir}/ ({existing} file(s) total)")


# ── helpers ───────────────────────────────────────────────────────────────────

def _error_result(task: Any, error: str, elapsed: float = 0.0) -> TaskResult:
    return TaskResult(
        task_id=task.task_id,
        task_name=getattr(task, "task_name", getattr(task, "name", task.task_id)),
        score=0.0,
        max_score=1.0,
        passed=False,
        grading_type="error",
        breakdown={},
        notes="",
        execution_time=elapsed,
        status="error",
        usage={},
        transcript_length=0,
        timed_out=False,
        error=error,
    )


def _save_transcript(result: TaskResult, transcripts_dir: Path) -> None:
    """Write a single task's transcript to ``transcripts_dir/{task_id}.jsonl``.

    Called immediately after each task finishes so data is not lost if the
    process is interrupted before ``_save_results`` runs.  Overwrites any
    pre-existing file (idempotent for retries).
    """
    if not result.transcript:
        return
    traj_path = transcripts_dir / f"{result.task_id}.jsonl"
    with open(traj_path, "w", encoding="utf-8") as fh:
        for entry in result.transcript:
            fh.write(json.dumps(entry, ensure_ascii=False) + "\n")


def _build_label_summary(results: list[TaskResult]) -> dict[str, Any]:
    """Aggregate pass-rate and avg-score for every label dimension value.

    Returns a dict keyed by dimension name (``capabilities``, ``modality``,
    ``scenario``, ``complexity``, ``environment``).  Each value is a dict
    keyed by the label value, containing ``total``, ``passed``, and
    ``avg_score``.

    For list-valued dimensions (``capabilities``) every element in the list
    is treated as an independent key so a task tagged with both ``Tool_Use``
    and ``Code_Manipulation`` contributes to both buckets.
    """
    # dimension name → label value → {total, passed, score_sum}
    buckets: dict[str, dict[str, dict[str, Any]]] = defaultdict(
        lambda: defaultdict(lambda: {"total": 0, "passed": 0, "score_sum": 0.0})
    )

    for r in results:
        labels = r.labels or {}

        # capabilities — list of strings
        for cap in labels.get("capabilities") or []:
            b = buckets["capabilities"][str(cap)]
            b["total"] += 1
            b["passed"] += int(r.passed)
            b["score_sum"] += r.score

        # modality — dict with a "type" key (and optional "channels" list)
        modality = labels.get("modality") or {}
        if modality:
            mod_type = str(modality.get("type", "unknown"))
            b = buckets["modality_type"][mod_type]
            b["total"] += 1
            b["passed"] += int(r.passed)
            b["score_sum"] += r.score
            for ch in modality.get("channels") or []:
                b2 = buckets["modality_channel"][str(ch)]
                b2["total"] += 1
                b2["passed"] += int(r.passed)
                b2["score_sum"] += r.score

        # scenario — plain string
        scenario = labels.get("scenario")
        if scenario:
            b = buckets["scenario"][str(scenario)]
            b["total"] += 1
            b["passed"] += int(r.passed)
            b["score_sum"] += r.score

        # complexity — plain string (e.g. "L1"–"L5")
        complexity = labels.get("complexity")
        if complexity:
            b = buckets["complexity"][str(complexity)]
            b["total"] += 1
            b["passed"] += int(r.passed)
            b["score_sum"] += r.score

        # environment — plain string (e.g. "open", "closed")
        environment = labels.get("environment")
        if environment:
            b = buckets["environment"][str(environment)]
            b["total"] += 1
            b["passed"] += int(r.passed)
            b["score_sum"] += r.score

    # Finalise: replace score_sum with avg_score
    out: dict[str, Any] = {}
    for dim, values in buckets.items():
        out[dim] = {}
        for label_val, data in sorted(values.items()):
            t = data["total"]
            out[dim][label_val] = {
                "total": t,
                "passed": data["passed"],
                "pass_rate": round(data["passed"] / t, 4) if t else 0.0,
                "avg_score": round(data["score_sum"] / t, 4) if t else 0.0,
            }
    return out


def _print_label_report(results: list[TaskResult]) -> None:
    """Print a human-readable breakdown of scores grouped by each label dimension."""
    summary = _build_label_summary(results)
    if not summary:
        return

    dim_titles = {
        "capabilities":      "Capabilities",
        "modality_type":     "Modality (type)",
        "modality_channel":  "Modality (channel)",
        "scenario":          "Scenario",
        "complexity":        "Complexity",
        "environment":       "Environment",
    }

    print(f"\n{'─'*70}")
    print("  Label-Dimension Report")
    print(f"{'─'*70}")

    for dim_key in ("capabilities", "modality_type", "modality_channel",
                    "scenario", "complexity", "environment"):
        if dim_key not in summary:
            continue
        title = dim_titles.get(dim_key, dim_key)
        print(f"\n  [{title}]")
        col_w = max((len(k) for k in summary[dim_key]), default=10)
        col_w = max(col_w, 10)
        header = (
            f"  {'Label':<{col_w}}  {'Total':>6}  {'Passed':>6}  "
            f"{'Pass%':>7}  {'AvgScore':>9}"
        )
        print(header)
        print("  " + "-" * (col_w + 35))
        for label_val, data in summary[dim_key].items():
            pass_pct = data["pass_rate"] * 100
            print(
                f"  {label_val:<{col_w}}  {data['total']:>6}  {data['passed']:>6}  "
                f"{pass_pct:>6.1f}%  {data['avg_score']:>9.4f}"
            )

    print(f"{'─'*70}\n")


def _write_checkpoint(
    results: list[TaskResult],
    agent_config: dict[str, Any],
    bench_name: str,
    out_path: Path,
) -> None:
    """Overwrite *out_path* with all results accumulated so far.

    Using a fixed path (generated once per run) means partial runs survive
    process crashes: the last checkpoint always contains everything up to the
    most recently completed task.
    """
    model = agent_config.get("model", "unknown")
    payload = {
        "benchmark": bench_name,
        "model": model,
        "timestamp": datetime.now().isoformat(),
        "summary": {
            "total": len(results),
            "passed": sum(1 for r in results if r.passed),
            "avg_score": (
                sum(r.score for r in results) / len(results) if results else 0.0
            ),
            "errors": {
                "total": sum(1 for r in results if r.status == "error"),
                "timed_out": sum(1 for r in results if r.timed_out),
                "failed": sum(1 for r in results if r.status == "error" and not r.timed_out),
            },
            "by_label": _build_label_summary(results),
        },
        "results": [
            {
                "task_id": r.task_id,
                "task_name": r.task_name,
                "score": r.score,
                "max_score": r.max_score,
                "passed": r.passed,
                "grading_type": r.grading_type,
                "breakdown": r.breakdown,
                "notes": r.notes,
                "execution_time": r.execution_time,
                "status": r.status,
                "usage": r.usage,
                "transcript_length": r.transcript_length,
                "timed_out": r.timed_out,
                "error": r.error,
                "labels": r.labels,
            }
            for r in results
        ],
    }
    # Write atomically via a temp file to avoid a corrupt file if interrupted
    # mid-write.
    tmp = out_path.with_suffix(".tmp")
    tmp.write_text(json.dumps(payload, ensure_ascii=False, indent=2))
    tmp.replace(out_path)
