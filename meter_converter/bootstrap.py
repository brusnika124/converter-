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
    service = ConverterService(reference_directory=reference_directory)
    MainWindow(root, service)
    root.mainloop()
