# -*- coding: utf-8 -*-
"""pawbench — agent benchmark runner for the pawbench dataset.

Public API
----------
* :class:`PawBenchBackend`  — load + run + grade pawbench tasks
* :class:`BenchmarkBackend` — abstract contract (one implementation today)
* :class:`TaskResult`       — per-task result dataclass
* :class:`BenchmarkRunner`  — orchestrates concurrent execution + checkpointing
* :class:`Task`, :class:`TaskLoader` — task data model and Markdown parser
* :class:`GradeResult`, :func:`grade_task` — grading entry points
"""

from .backend import BenchmarkBackend, PawBenchBackend, TaskResult
from .grader import GradeResult, grade_task
from .runner import BenchmarkRunner
from .task_loader import Task, TaskLoader

__all__ = [
    "BenchmarkBackend",
    "BenchmarkRunner",
    "GradeResult",
    "PawBenchBackend",
    "Task",
    "TaskLoader",
    "TaskResult",
    "grade_task",
]
