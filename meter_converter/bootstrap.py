from __future__ import annotations

from pathlib import Path
import tkinter as tk

from meter_converter.services.application import ConverterService
from meter_converter.ui.main_window import MainWindow

try:
    from tkinterdnd2 import TkinterDnD
    DND_AVAILABLE = True
except ImportError:
    DND_AVAILABLE = False
    TkinterDnD = None


def run() -> None:
    if DND_AVAILABLE and TkinterDnD is not None:
        root = TkinterDnD.Tk()
    else:
        root = tk.Tk()

    project_root = Path(__file__).resolve().parent.parent
    reference_directory = project_root / "справочники"
    loading_statement_template = project_root / "шаблон загрузочной ведомости.xlsx"
    service = ConverterService(
        reference_directory=reference_directory,
        loading_statement_template=loading_statement_template,
    )
    MainWindow(root, service)
    root.mainloop()
