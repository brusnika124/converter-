from __future__ import annotations

from pathlib import Path


class OutputPathGenerator:
    def next_path(self, source_path: Path) -> Path:
        directory = source_path.parent
        candidate = directory / "профиль.xlsx"
        counter = 1
        while candidate.exists():
            candidate = directory / f"профиль{counter}.xlsx"
            counter += 1
        return candidate
