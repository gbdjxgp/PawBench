# -*- coding: utf-8 -*-
"""Base environment interface for pawbench."""

import abc
from pathlib import Path
from typing import Any, Dict, Optional


class BaseEnvironment(abc.ABC):
    """Abstract base for execution environments."""

    def __init__(self, name: str, **kwargs: Any):
        self.name = name
        self.config = kwargs

    @abc.abstractmethod
    async def start(self) -> None: ...

    @abc.abstractmethod
    async def stop(self) -> None: ...

    @abc.abstractmethod
    async def execute_command(self, command: str, timeout: Optional[int] = None) -> Dict[str, Any]: ...

    @abc.abstractmethod
    async def copy_to(self, source: Path, destination: str) -> bool: ...

    @abc.abstractmethod
    async def copy_from(self, source: str, destination: Path) -> bool: ...

    @abc.abstractmethod
    async def write_file(self, path: str, content: str) -> bool: ...

    @abc.abstractmethod
    async def read_file(self, path: str) -> Optional[str]: ...

    @property
    @abc.abstractmethod
    def is_running(self) -> bool: ...
