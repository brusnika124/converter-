from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path

from meter_converter.domain import ParsedProfile


class ProfileParser(ABC):
    @abstractmethod
    def parse(self, path: Path) -> ParsedProfile:
        raise NotImplementedError
