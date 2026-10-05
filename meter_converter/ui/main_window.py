from __future__ import annotations

from pathlib import Path
import tkinter as tk
from tkinter import filedialog, messagebox

from PIL import Image, ImageDraw, ImageTk

from meter_converter.domain import InputValueType, ProcessingMode
from meter_converter.months import MONTH_NAMES_RU
from meter_converter.services.application import ConverterService
from meter_converter.ui.drawing import draw_round_rect
from meter_converter.ui.theme import (
    ACCENT_BLUE,
    ACCENT_BLUE_LIGHT,
    APP_BG,
    BORDER_LIGHT,
    CARD_BG,
    ORANGE,
    SEGMENT_BG,
    SHADOW_COLOR,
    TEXT_DARK,
    TEXT_GRAY,
)

try:
    from tkinterdnd2 import DND_FILES
    DND_AVAILABLE = True
except ImportError:
    DND_AVAILABLE = False
    DND_FILES = None


class MainWindow:
    def __init__(self, root: tk.Tk, service: ConverterService) -> None:
        self.root = root
        self.service = service
        self.file_path: Path | None = None
        self.mode = tk.StringVar(value=ProcessingMode.MANUAL.value)
        self.input_type = tk.StringVar(value=InputValueType.POINT.value)
        self._input_value = ""
        self._manual_input_value = ""
        self._manual_input_type = InputValueType.POINT.value
        self._auto_input_value = ""
        self._auto_input_type = InputValueType.POINT.value
        self.auto_override_enabled = False
        self._selector_enabled = True
        self._selector_hover_index: int | None = None
        self._selector_visual_index = 1.0
        self._selector_animation_after: str | None = None
        self._selector_card_images: dict[tuple[str, bool], ImageTk.PhotoImage] = {}
        self._dropzone_images: dict[tuple[bool, bool], ImageTk.PhotoImage] = {}
        self._lock_hover = False
        self.loading_statement_enabled = False
        self._loading_statement_hover = False
        self._statement_export_hover = False
        self._trash_icon = self._load_ui_icon("trash.png")
        self._lock_closed_icon = self._load_ui_icon("lock_closed.png")
        self._lock_open_icon = self._load_ui_icon("lock_open.png")

        self.root.title("Обработка профилей")
        self.root.geometry("560x840")
        self.root.configure(bg=APP_BG)
        self.root.resizable(False, False)
        self._set_icon()
        self._create_widgets()

    def _set_icon(self) -> None:
        icon_dir = Path(__file__).resolve().parent.parent
        try:
            png_path = icon_dir / "icon.png"
            if png_path.exists():
                self._app_icon = tk.PhotoImage(file=str(png_path))
                self.root.iconphoto(True, self._app_icon)
        except Exception:
            pass
        try:
            ico_path = icon_dir / "icon.ico"
            if ico_path.exists():
                self.root.iconbitmap(str(ico_path))
        except Exception:
            pass

    def _load_ui_icon(self, filename: str):
        try:
            icon_path = Path(__file__).resolve().parent / "assets" / filename
            if not icon_path.exists():
                return None
            return tk.PhotoImage(file=str(icon_path))
        except Exception:
            return None

    def _create_widgets(self) -> None:
        tk.Label(
            self.root,
            text="РЕЖИМ ОБРАБОТКИ",
            font=("Segoe UI", 9, "bold"),
            bg=APP_BG,
            fg=TEXT_GRAY,
        ).pack(anchor="w", padx=40, pady=(24, 6))

        self.segment_canvas = tk.Canvas(
            self.root, width=300, height=42, bg=APP_BG, highlightthickness=0
        )
        self.segment_canvas.pack(anchor="w", padx=40)
        self.segment_canvas.bind("<Button-1>", self._on_segment_click)
        self._draw_segment()

        card_width, card_height = 480, 680
        card_x, card_y = 40, 96
        self.card_canvas = tk.Canvas(
            self.root,
            width=560,
            height=card_height + 40,
            bg=APP_BG,
            highlightthickness=0,
        )
        self.card_canvas.place(x=0, y=card_y)
        draw_round_rect(
            self.card_canvas,
            card_x + 4,
            8,
            card_x + card_width + 4,
            card_height + 8,
            radius=20,
            fill=SHADOW_COLOR,
            outline="",
        )
        draw_round_rect(
            self.card_canvas,
            card_x,
            4,
            card_x + card_width,
            card_height + 4,
            radius=20,
            fill=CARD_BG,
            outline=BORDER_LIGHT,
            width=1,
        )

        inner = tk.Frame(self.card_canvas, bg=CARD_BG)
        self.card_canvas.create_window(
            card_x + 28,
            28,
            anchor="nw",
            window=inner,
            width=card_width - 56,
            height=card_height - 48,
        )

        tk.Label(
            inner,
            text="Профиля мощности",
            font=("Segoe UI", 18, "bold"),
            bg=CARD_BG,
            fg=TEXT_DARK,
        ).pack(anchor="center", pady=(0, 16))

        self.dropzone = tk.Canvas(
            inner,
            width=card_width - 56,
            height=150,
            bg=CARD_BG,
            highlightthickness=0,
        )
        self.dropzone.pack(pady=(0, 14))
        self.dropzone.bind("<Button-1>", self._on_dropzone_click)
        self.dropzone.bind("<Motion>", self._on_dropzone_motion)
        self.dropzone.bind("<Leave>", self._on_dropzone_pointer_leave)
        self._draw_dropzone()
        self._bind_drag_and_drop()

        self.reference_frame = tk.Frame(inner, bg=CARD_BG)
        self.reference_label = tk.Label(
            self.reference_frame,
            text="Справочники: проверка...",
            font=("Segoe UI", 9),
            bg=CARD_BG,
            fg=TEXT_GRAY,
            justify="left",
            wraplength=424,
        )
        self.reference_label.pack(anchor="w")

        self.selector_label = tk.Label(
            inner,
            text="Параметр поиска",
            font=("Segoe UI", 10, "bold"),
            bg=CARD_BG,
            fg=TEXT_DARK,
        )
        self.selector_label.pack(anchor="center", pady=(4, 8))

        self.input_selector = tk.Canvas(
            inner,
            width=card_width - 56,
            height=66,
            bg=CARD_BG,
            highlightthickness=0,
        )
        self.input_selector.pack(anchor="w", pady=(0, 14))
        self.input_selector.bind("<Button-1>", self._on_input_selector_click)
        self.input_selector.bind("<Motion>", self._on_input_selector_motion)
        self.input_selector.bind("<Leave>", self._on_input_selector_leave)
        self._draw_input_selector()

        self.entry_label = tk.Label(
            inner,
            text="№ Точки учета:",
            font=("Segoe UI", 10),
            bg=CARD_BG,
            fg=TEXT_DARK,
        )
        self.entry_label.pack(anchor="w", pady=(0, 6))

        self.entry_frame = tk.Frame(
            inner,
            bg="white",
            highlightthickness=1,
            highlightbackground=BORDER_LIGHT,
            highlightcolor=ACCENT_BLUE,
        )
        self.entry_frame.pack(fill="x", pady=(0, 14))

        self.input_entry = tk.Entry(
            self.entry_frame,
            font=("Segoe UI", 11),
            bd=0,
            relief="flat",
            fg=TEXT_DARK,
            disabledbackground="#f4f6f9",
            disabledforeground=TEXT_GRAY,
        )
        self.input_entry.pack(side="left", fill="x", expand=True, padx=(12, 4), pady=10)
        self.input_entry.bind("<KeyRelease>", self._on_input_changed)
        self.input_entry.bind("<Control-KeyPress>", self._on_entry_control_key)
        self.input_entry.bind("<Return>", lambda _: self._refresh_input_preview())
        self.input_entry.bind("<FocusOut>", lambda _: self._refresh_input_preview())

        self.lock_canvas = tk.Canvas(
            self.entry_frame,
            width=38,
            height=34,
            bg="white",
            highlightthickness=0,
            cursor="hand2",
        )
        self.lock_canvas.bind("<Button-1>", lambda _: self._toggle_auto_override())
        self.lock_canvas.bind("<Enter>", self._on_lock_enter)
        self.lock_canvas.bind("<Leave>", self._on_lock_leave)

        self.lookup_status = tk.Label(
            inner,
            text="",
            font=("Segoe UI", 9),
            bg=CARD_BG,
            fg=TEXT_GRAY,
        )
        self.lookup_status.pack(anchor="w", pady=(0, 6))

        self.loading_statement_canvas = tk.Canvas(
            inner,
            width=card_width - 56,
            height=34,
            bg=CARD_BG,
            highlightthickness=0,
            cursor="hand2",
        )
        self.loading_statement_canvas.pack(anchor="w", pady=(0, 8))
        self.loading_statement_canvas.bind("<Button-1>", lambda _: self._toggle_loading_statement())
        self.loading_statement_canvas.bind("<Enter>", self._on_loading_statement_enter)
        self.loading_statement_canvas.bind("<Leave>", self._on_loading_statement_leave)
        self._draw_loading_statement_toggle()

        self.actions_frame = tk.Frame(inner, bg=CARD_BG)
        self.actions_frame.pack(side="bottom", fill="x", pady=(8, 0))

        self.convert_canvas = tk.Canvas(
            self.actions_frame,
            width=card_width - 56,
            height=50,
            bg=CARD_BG,
            highlightthickness=0,
        )
        self.convert_canvas.pack()
        self.convert_canvas.bind("<Button-1>", lambda _: self.convert_file())
        self.convert_canvas.bind("<Enter>", lambda _: self._draw_convert_button(True))
        self.convert_canvas.bind("<Leave>", lambda _: self._draw_convert_button(False))
        self._draw_convert_button()

        self.statement_export_canvas = tk.Canvas(
            self.actions_frame,
            width=card_width - 56,
            height=46,
            bg=CARD_BG,
            highlightthickness=0,
        )
        self.statement_export_canvas.pack(pady=(8, 0))
        self.statement_export_canvas.bind("<Button-1>", lambda _: self.export_loading_statement())
        self.statement_export_canvas.bind("<Enter>", self._on_statement_export_enter)
        self.statement_export_canvas.bind("<Leave>", self._on_statement_export_leave)
        self._draw_statement_export_button()
        self._apply_mode()

    def _bind_drag_and_drop(self) -> None:
        if not DND_AVAILABLE or DND_FILES is None:
            return
        try:
            self.dropzone.drop_target_register(DND_FILES)
            self.dropzone.dnd_bind("<<Drop>>", self._on_file_drop)
            self.dropzone.dnd_bind("<<DropEnter>>", self._on_drag_enter)
            self.dropzone.dnd_bind("<<DropLeave>>", self._on_drag_leave)
        except AttributeError:
            pass

    def _draw_segment(self) -> None:
        canvas = self.segment_canvas
        canvas.delete("all")
        width, height = 300, 42
        draw_round_rect(canvas, 0, 0, width, height, radius=14, fill=SEGMENT_BG, outline="")
        half = width / 2
        if self.mode.get() == ProcessingMode.MANUAL.value:
            draw_round_rect(canvas, 3, 3, half - 2, height - 3, radius=12, fill="white", outline="")
            manual_color, auto_color = ACCENT_BLUE, TEXT_GRAY
        else:
            draw_round_rect(canvas, half + 2, 3, width - 3, height - 3, radius=12, fill="white", outline="")
            manual_color, auto_color = TEXT_GRAY, ACCENT_BLUE
        canvas.create_text(half / 2, height / 2, text="Ручной", font=("Segoe UI", 10, "bold"), fill=manual_color)
        canvas.create_text(half + half / 2, height / 2, text="Автоматический", font=("Segoe UI", 10, "bold"), fill=auto_color)

    def _on_segment_click(self, event) -> None:
        target_mode = ProcessingMode.MANUAL.value if event.x < 150 else ProcessingMode.AUTO.value
        if target_mode == self.mode.get():
            return

        if self.mode.get() == ProcessingMode.MANUAL.value:
            self._manual_input_value = self.input_entry.get().strip()
            self._manual_input_type = self.input_type.get()
        elif self.auto_override_enabled:
            self._auto_input_value = self.input_entry.get().strip()
            self._auto_input_type = self.input_type.get()

        self.mode.set(target_mode)
        self._draw_segment()
        self._apply_mode()

    _SELECTOR_OPTIONS = (
        ("КТ", InputValueType.KT.value),
        ("№ ТУ", InputValueType.POINT.value),
        ("№ ПУ", InputValueType.SERIAL.value),
    )
    # Compact selector layout with a 1 px safety margin on both sides.
    # 1 + 132 + 13 + 132 + 13 + 132 = 423, so the right border
    # stays fully inside the 424 px canvas instead of being clipped.
    _SELECTOR_X = (1, 146, 291)
    _SELECTOR_WIDTH = 132
    _SELECTOR_CARD_HEIGHT = 58

    def _selector_index(self, value: str | None = None) -> int:
        current = value or self.input_type.get()
        for index, (_, option_value) in enumerate(self._SELECTOR_OPTIONS):
            if option_value == current:
                return index
        return 1

    def _selector_card_image(self, state: str, enabled: bool) -> ImageTk.PhotoImage:
        key = (state, enabled)
        cached = self._selector_card_images.get(key)
        if cached is not None:
            return cached

        scale = 4
        width = self._SELECTOR_WIDTH
        height = self._SELECTOR_CARD_HEIGHT
        image = Image.new("RGBA", (width * scale, height * scale), (0, 0, 0, 0))
        draw = ImageDraw.Draw(image)

        if not enabled:
            fill = "#f8f9fb"
            outline = "#e4e9f0"
            ring = "#d7dee7"
            dot = "#c4cbd5"
        elif state == "selected":
            fill = "#f2f9ff"
            outline = "#73adff"
            ring = "#2f86ff"
            dot = "#2f86ff"
        elif state == "hover":
            fill = "#fbfdff"
            outline = "#bfdcff"
            ring = "#83cdf7"
            dot = None
        else:
            fill = "#ffffff"
            outline = "#dbe3ed"
            ring = "#9edcff"
            dot = None

        # Pillow renders at 4x and downsamples, producing much smoother
        # rounded corners and radio rings than Tk Canvas primitives.
        radius = 15 * scale
        draw.rounded_rectangle(
            (0, 0, width * scale - 1, height * scale - 1),
            radius=radius,
            fill=fill,
            outline=outline,
            width=1 * scale,
        )

        cx = 22 * scale
        cy = (height // 2) * scale
        outer_r = 10 * scale
        inner_r = 5 * scale
        draw.ellipse(
            (cx - outer_r, cy - outer_r, cx + outer_r, cy + outer_r),
            fill="#ffffff" if enabled else "#fafbfd",
            outline=ring,
            width=2 * scale,
        )
        if dot is not None:
            draw.ellipse(
                (cx - inner_r, cy - inner_r, cx + inner_r, cy + inner_r),
                fill=dot,
                outline=dot,
            )

        image = image.resize((width, height), Image.Resampling.LANCZOS)
        photo = ImageTk.PhotoImage(image)
        self._selector_card_images[key] = photo
        return photo

    def _draw_input_selector(self) -> None:
        canvas = self.input_selector
        canvas.delete("all")

        enabled = self._selector_enabled
        selected_index = self._selector_index()
        card_top = 4
        center_y = card_top + self._SELECTOR_CARD_HEIGHT / 2

        for index, (label, _value) in enumerate(self._SELECTOR_OPTIONS):
            x = self._SELECTOR_X[index]
            is_selected = index == selected_index
            is_hovered = index == self._selector_hover_index and enabled and not is_selected

            if is_selected:
                state = "selected"
            elif is_hovered:
                state = "hover"
            else:
                state = "normal"

            image = self._selector_card_image(state, enabled)
            canvas.create_image(x, card_top, anchor="nw", image=image)

            if not enabled:
                text_color = "#b3bac5"
            elif is_selected:
                text_color = "#075cf6"
            else:
                text_color = TEXT_DARK

            # Keep the typography identical in every state: selection is
            # communicated only by color/border/radio, never by bold text.
            canvas.create_text(
                x + 44,
                center_y,
                text=label,
                anchor="w",
                font=("Segoe UI", 9, "normal"),
                fill=text_color,
            )

        canvas.configure(cursor="hand2" if enabled else "arrow")

    def _selector_x_for_visual_index(self, visual_index: float) -> float:
        visual_index = max(0.0, min(2.0, visual_index))
        left_index = int(visual_index)
        if left_index >= 2:
            return float(self._SELECTOR_X[2])
        fraction = visual_index - left_index
        start = self._SELECTOR_X[left_index]
        end = self._SELECTOR_X[left_index + 1]
        return start + (end - start) * fraction

    def _animate_selector_to(self, target_index: int) -> None:
        if self._selector_animation_after is not None:
            try:
                self.root.after_cancel(self._selector_animation_after)
            except Exception:
                pass
            self._selector_animation_after = None

        start = float(self._selector_visual_index)
        target = float(target_index)
        frames = 10

        def ease_out_cubic(t: float) -> float:
            return 1 - (1 - t) ** 3

        def step(frame: int = 1) -> None:
            t = frame / frames
            eased = ease_out_cubic(t)
            self._selector_visual_index = start + (target - start) * eased
            self._draw_input_selector()
            if frame < frames:
                self._selector_animation_after = self.root.after(16, lambda: step(frame + 1))
            else:
                self._selector_visual_index = target
                self._selector_animation_after = None
                self._draw_input_selector()

        step()

    def _selector_hit_index(self, x: int, y: int) -> int | None:
        if y < 4 or y > 4 + self._SELECTOR_CARD_HEIGHT:
            return None
        for index, left in enumerate(self._SELECTOR_X):
            if left <= x <= left + self._SELECTOR_WIDTH:
                return index
        return None

    def _on_input_selector_motion(self, event) -> None:
        hover = self._selector_hit_index(event.x, event.y) if self._selector_enabled else None
        if hover != self._selector_hover_index:
            self._selector_hover_index = hover
            self._draw_input_selector()

    def _on_input_selector_leave(self, _event) -> None:
        if self._selector_hover_index is not None:
            self._selector_hover_index = None
            self._draw_input_selector()

    def _on_input_selector_click(self, event) -> None:
        if not self._selector_enabled:
            return
        index = self._selector_hit_index(event.x, event.y)
        if index is None:
            return
        value = self._SELECTOR_OPTIONS[index][1]
        if value == self.input_type.get():
            self.input_entry.focus_set()
            return

        self.input_type.set(value)
        if self.mode.get() == ProcessingMode.MANUAL.value:
            self._manual_input_type = value
        else:
            self._auto_input_type = value
        self._on_input_type_changed(animate_to=index)
        self.input_entry.focus_set()

    def _dropzone_background_image(self, selected: bool, drag_active: bool = False) -> ImageTk.PhotoImage:
        key = (selected, drag_active)
        cached = self._dropzone_images.get(key)
        if cached is not None:
            return cached

        width = int(self.dropzone["width"])
        height = int(self.dropzone["height"])
        scale = 4
        image = Image.new("RGBA", (width * scale, height * scale), (0, 0, 0, 0))
        draw = ImageDraw.Draw(image)

        fill = "#eaf2ff" if drag_active else ("#f5f9ff" if selected else "#edf4ff")
        border = "#2f86ff" if drag_active else "#6ca7ff"
        soft_border = "#cfe0fb"
        radius = 16 * scale
        inset = 2 * scale

        # A faint solid contour gives the rounded corners a clean anti-aliased edge.
        draw.rounded_rectangle(
            (inset, inset, width * scale - inset, height * scale - inset),
            radius=radius,
            fill=fill,
            outline=soft_border,
            width=1 * scale,
        )

        # The straight sections use rounded dashes.  Keeping the corner arcs solid
        # makes the frame look deliberate instead of jagged at the bends.
        dash = 7 * scale
        gap = 6 * scale
        line_w = 2 * scale
        left = inset + radius
        right = width * scale - inset - radius
        top = inset
        bottom = height * scale - inset

        def dashed_h(y: int) -> None:
            x = left
            while x < right:
                x2 = min(x + dash, right)
                draw.line((x, y, x2, y), fill=border, width=line_w)
                r = line_w // 2
                draw.ellipse((x-r, y-r, x+r, y+r), fill=border)
                draw.ellipse((x2-r, y-r, x2+r, y+r), fill=border)
                x = x2 + gap

        def dashed_v(x: int) -> None:
            y = inset + radius
            limit = height * scale - inset - radius
            while y < limit:
                y2 = min(y + dash, limit)
                draw.line((x, y, x, y2), fill=border, width=line_w)
                r = line_w // 2
                draw.ellipse((x-r, y-r, x+r, y+r), fill=border)
                draw.ellipse((x-r, y2-r, x+r, y2+r), fill=border)
                y = y2 + gap

        dashed_h(top)
        dashed_h(bottom)
        dashed_v(inset)
        dashed_v(width * scale - inset)

        # Smooth corner arcs.
        box_tl = (inset, inset, inset + 2 * radius, inset + 2 * radius)
        box_tr = (width * scale - inset - 2 * radius, inset, width * scale - inset, inset + 2 * radius)
        box_bl = (inset, height * scale - inset - 2 * radius, inset + 2 * radius, height * scale - inset)
        box_br = (width * scale - inset - 2 * radius, height * scale - inset - 2 * radius, width * scale - inset, height * scale - inset)
        draw.arc(box_tl, 180, 270, fill=border, width=line_w)
        draw.arc(box_tr, 270, 360, fill=border, width=line_w)
        draw.arc(box_bl, 90, 180, fill=border, width=line_w)
        draw.arc(box_br, 0, 90, fill=border, width=line_w)

        image = image.resize((width, height), Image.Resampling.LANCZOS)
        photo = ImageTk.PhotoImage(image)
        self._dropzone_images[key] = photo
        return photo

    def _draw_dropzone(self, filename: str | None = None, drag_active: bool = False) -> None:
        canvas = self.dropzone
        canvas.delete("all")
        width, height = int(canvas["width"]), int(canvas["height"])
        background = self._dropzone_background_image(bool(filename), drag_active)
        canvas.create_image(0, 0, anchor="nw", image=background)
        center_x, center_y = width / 2, 42
        draw_round_rect(
            canvas,
            center_x - 18,
            center_y - 18,
            center_x + 18,
            center_y + 18,
            radius=10,
            fill="white",
            outline="",
        )
        canvas.create_line(center_x, center_y - 8, center_x, center_y + 8, fill=ACCENT_BLUE, width=2)
        canvas.create_line(center_x - 7, center_y - 1, center_x, center_y - 8, fill=ACCENT_BLUE, width=2)
        canvas.create_line(center_x + 7, center_y - 1, center_x, center_y - 8, fill=ACCENT_BLUE, width=2)
        if filename:
            main_text = filename if len(filename) < 38 else filename[:35] + "..."
            sub_text = "Нажмите, чтобы изменить файл"
            self._draw_trash_icon(canvas, width - 28, 28)
        else:
            main_text = "Перетащите файл сюда"
            sub_text = "или нажмите для выбора файла"
        canvas.create_text(width / 2, 90, text=main_text, font=("Segoe UI", 11, "bold"), fill=TEXT_DARK)
        canvas.create_text(width / 2, 112, text=sub_text, font=("Segoe UI", 9), fill=TEXT_GRAY)

    def _draw_trash_icon(self, canvas: tk.Canvas, center_x: int, center_y: int) -> None:
        if self._trash_icon is not None:
            canvas.create_image(center_x, center_y, image=self._trash_icon)
            return
        canvas.create_oval(
            center_x - 16,
            center_y - 16,
            center_x + 16,
            center_y + 16,
            fill="white",
            outline=BORDER_LIGHT,
            width=1,
        )
        canvas.create_line(center_x - 7, center_y - 6, center_x + 7, center_y - 6, fill=TEXT_GRAY, width=2)
        canvas.create_line(center_x - 3, center_y - 9, center_x + 3, center_y - 9, fill=TEXT_GRAY, width=2)
        canvas.create_line(center_x - 6, center_y - 3, center_x - 4, center_y + 8, fill=TEXT_GRAY, width=2)
        canvas.create_line(center_x + 6, center_y - 3, center_x + 4, center_y + 8, fill=TEXT_GRAY, width=2)
        canvas.create_line(center_x - 4, center_y + 8, center_x + 4, center_y + 8, fill=TEXT_GRAY, width=2)

    def _on_dropzone_click(self, event) -> None:
        if self.file_path:
            width = int(self.dropzone["width"])
            if event.x >= width - 50 and event.y <= 50:
                self._clear_source_file()
                return
        self.select_file()

    def _on_dropzone_motion(self, event) -> None:
        if not self.file_path:
            self.dropzone.configure(cursor="arrow")
            return

        width = int(self.dropzone["width"])
        over_trash = event.x >= width - 50 and event.y <= 50
        self.dropzone.configure(cursor="hand2" if over_trash else "arrow")

    def _on_dropzone_pointer_leave(self, _event) -> None:
        self.dropzone.configure(cursor="arrow")

    def _clear_source_file(self) -> None:
        self.file_path = None
        self.dropzone.configure(cursor="arrow")
        self._draw_dropzone()
        self._refresh_input_preview()

    def _on_entry_control_key(self, event):
        keycode = getattr(event, "keycode", None)
        if keycode == 86:  # V
            self._paste_into_entry()
            return "break"
        if keycode == 65:  # A
            self.input_entry.selection_range(0, tk.END)
            self.input_entry.icursor(tk.END)
            return "break"
        if keycode == 67:  # C
            try:
                selected = self.input_entry.selection_get()
            except tk.TclError:
                return "break"
            self.root.clipboard_clear()
            self.root.clipboard_append(selected)
            return "break"
        if keycode == 88:  # X
            try:
                selected = self.input_entry.selection_get()
                first = self.input_entry.index(tk.SEL_FIRST)
                last = self.input_entry.index(tk.SEL_LAST)
            except tk.TclError:
                return "break"
            self.root.clipboard_clear()
            self.root.clipboard_append(selected)
            self.input_entry.delete(first, last)
            self._on_input_changed()
            self._refresh_input_preview()
            return "break"
        return None

    def _paste_into_entry(self) -> None:
        try:
            text = self.root.clipboard_get()
        except tk.TclError:
            return

        try:
            first = self.input_entry.index(tk.SEL_FIRST)
            last = self.input_entry.index(tk.SEL_LAST)
            self.input_entry.delete(first, last)
        except tk.TclError:
            pass

        self.input_entry.insert(tk.INSERT, text)
        self._on_input_changed()
        self._refresh_input_preview()

    def _draw_convert_button(self, hover: bool = False) -> None:
        canvas = self.convert_canvas
        canvas.delete("all")
        width, height = int(canvas["width"]), int(canvas["height"])
        color = "#3d7ae8" if hover else ACCENT_BLUE
        draw_round_rect(canvas, 1, 1, width - 1, height - 1, radius=14, fill=color, outline="")
        canvas.create_text(width / 2, height / 2 - (2 if hover else 0), text="КОНВЕРТИРОВАТЬ", font=("Segoe UI", 11, "bold"), fill="white")

    def _draw_loading_statement_toggle(self) -> None:
        canvas = self.loading_statement_canvas
        canvas.delete("all")
        selected = self.loading_statement_enabled
        hover = self._loading_statement_hover

        box_left, box_top, box_size = 2, 7, 20
        fill = ACCENT_BLUE if selected else ("#f7fbff" if hover else "white")
        outline = ACCENT_BLUE if selected else ("#9ecbff" if hover else BORDER_LIGHT)
        draw_round_rect(
            canvas,
            box_left,
            box_top,
            box_left + box_size,
            box_top + box_size,
            radius=6,
            fill=fill,
            outline=outline,
            width=1,
        )
        if selected:
            canvas.create_line(
                box_left + 5,
                box_top + 10,
                box_left + 9,
                box_top + 14,
                box_left + 16,
                box_top + 6,
                fill="white",
                width=2,
                capstyle=tk.ROUND,
                joinstyle=tk.ROUND,
            )
        canvas.create_text(
            32,
            17,
            anchor="w",
            text="Формировать загрузочную ведомость",
            font=("Segoe UI", 9),
            fill=TEXT_DARK,
        )

    def _toggle_loading_statement(self) -> None:
        self.loading_statement_enabled = not self.loading_statement_enabled
        self._draw_loading_statement_toggle()

    def _on_loading_statement_enter(self, _event) -> None:
        self._loading_statement_hover = True
        self._draw_loading_statement_toggle()

    def _on_loading_statement_leave(self, _event) -> None:
        self._loading_statement_hover = False
        self._draw_loading_statement_toggle()

    def _draw_statement_export_button(self) -> None:
        canvas = self.statement_export_canvas
        canvas.delete("all")
        width, height = int(canvas["width"]), int(canvas["height"])
        enabled = self.service.has_loading_statement_data

        if enabled:
            fill = ACCENT_BLUE_LIGHT if self._statement_export_hover else "white"
            outline = ACCENT_BLUE
            text_color = ACCENT_BLUE
            cursor = "hand2"
        else:
            fill = "#f7f8fa"
            outline = "#e2e6ec"
            text_color = "#a5adb9"
            cursor = "arrow"

        draw_round_rect(
            canvas,
            1,
            1,
            width - 1,
            height - 1,
            radius=13,
            fill=fill,
            outline=outline,
            width=1,
        )
        canvas.create_text(
            width / 2,
            height / 2,
            text="ВЫГРУЗИТЬ ВЕДОМОСТЬ",
            font=("Segoe UI", 10, "bold"),
            fill=text_color,
        )
        canvas.configure(cursor=cursor)

    def _on_statement_export_enter(self, _event) -> None:
        if self.service.has_loading_statement_data:
            self._statement_export_hover = True
            self._draw_statement_export_button()

    def _on_statement_export_leave(self, _event) -> None:
        if self._statement_export_hover:
            self._statement_export_hover = False
            self._draw_statement_export_button()

    def export_loading_statement(self) -> None:
        if not self.service.has_loading_statement_data:
            messagebox.showwarning(
                "Загрузочная ведомость",
                "Сначала обработайте хотя бы один профиль с включенной опцией "
                "«Формировать загрузочную ведомость»."
            )
            return

        path = filedialog.asksaveasfilename(
            title="Сохранить загрузочную ведомость",
            defaultextension=".xlsx",
            filetypes=[("Excel files", "*.xlsx")],
            initialfile="Загрузочная ведомость.xlsx",
        )
        if not path:
            return

        try:
            self.service.export_loading_statement(Path(path))
            messagebox.showinfo(
                "Готово",
                f"Загрузочная ведомость сохранена!\n{path}",
            )
        except Exception as exc:
            messagebox.showerror("Ошибка", str(exc))

    def _apply_mode(self) -> None:
        self.reference_frame.pack(after=self.dropzone, pady=(0, 14))
        self._refresh_reference_directory()

        if self.mode.get() == ProcessingMode.AUTO.value:
            self.auto_override_enabled = False
            self.input_type.set(self._auto_input_type)
            self._selector_visual_index = float(self._selector_index())
            self._set_input_value(self._auto_input_value)
            self._set_auto_controls_locked(True)
        else:
            self.input_type.set(self._manual_input_type)
            self._selector_visual_index = float(self._selector_index())
            self._set_auto_controls_locked(False, manual_mode=True)
            self._set_input_value(self._manual_input_value)

        self._update_entry_label()
        self._draw_input_selector()
        self._refresh_input_preview()

    def _set_auto_controls_locked(self, locked: bool, manual_mode: bool = False) -> None:
        if manual_mode:
            self._selector_enabled = True
            self.selector_label.config(fg=TEXT_DARK)
            self.entry_label.config(fg=TEXT_DARK)
            self.entry_frame.config(bg="white", highlightbackground=BORDER_LIGHT)
            self.input_entry.config(state="normal", bg="white")
            self.lock_canvas.configure(bg="white")
            self.lock_canvas.pack_forget()
            return

        self.auto_override_enabled = not locked
        self._selector_enabled = not locked
        self.selector_label.config(fg=TEXT_GRAY if locked else TEXT_DARK)
        self.entry_label.config(fg=TEXT_GRAY if locked else TEXT_DARK)

        if locked:
            self._auto_input_value = self.input_entry.get().strip() if self.input_entry.cget("state") == "normal" else self._auto_input_value
            self.input_entry.config(state="normal", bg="#f4f6f9")
            self._set_input_value("Определяется автоматически")
            self.input_entry.config(state="disabled")
            self.entry_frame.config(bg="#f4f6f9", highlightbackground="#e4e7ec")
            # Canvas in Tkinter cannot be transparent. Matching its background
            # to the entry frame removes the white square around the rounded lock button.
            self.lock_canvas.configure(bg="#f4f6f9")
        else:
            self.input_entry.config(state="normal", bg="white")
            self._set_input_value(self._auto_input_value)
            self.entry_frame.config(bg="white", highlightbackground=BORDER_LIGHT)
            self.lock_canvas.configure(bg="white")
            self.input_entry.focus_set()

        if not self.lock_canvas.winfo_ismapped():
            self.lock_canvas.pack(side="right", padx=(0, 6), pady=3)
        self._draw_lock_button()
        self._draw_input_selector()

    def _toggle_auto_override(self) -> None:
        if self.mode.get() != ProcessingMode.AUTO.value:
            return
        self._set_auto_controls_locked(self.auto_override_enabled)
        self._refresh_input_preview()

    def _draw_lock_button(self) -> None:
        canvas = self.lock_canvas
        canvas.delete("all")
        unlocked = self.auto_override_enabled
        hover = self._lock_hover
        fill = "#edf4ff" if hover else ("#f7f9fc" if not unlocked else "#f3f7ff")
        outline = "#c9dcff" if hover or unlocked else "#e1e5eb"
        draw_round_rect(canvas, 3, 3, 35, 31, radius=9, fill=fill, outline=outline, width=1)

        image = self._lock_open_icon if unlocked else self._lock_closed_icon
        if image is not None:
            canvas.create_image(19, 17, image=image)
            return

        # Fallback, если ассеты случайно отсутствуют.
        icon = ACCENT_BLUE if unlocked or hover else "#8f98a6"
        if unlocked:
            canvas.create_arc(11, 7, 25, 21, start=30, extent=210, style="arc", outline=icon, width=2)
            canvas.create_rectangle(12, 16, 26, 25, outline=icon, width=2)
        else:
            canvas.create_arc(11, 7, 25, 21, start=0, extent=180, style="arc", outline=icon, width=2)
            canvas.create_rectangle(11, 15, 27, 25, outline=icon, width=2)
        canvas.create_oval(18, 19, 20, 21, fill=icon, outline=icon)

    def _on_lock_enter(self, _event) -> None:
        self._lock_hover = True
        self._draw_lock_button()

    def _on_lock_leave(self, _event) -> None:
        self._lock_hover = False
        self.loading_statement_enabled = False
        self._loading_statement_hover = False
        self._statement_export_hover = False
        self._draw_lock_button()

    def _update_entry_label(self) -> None:
        current_type = InputValueType(self.input_type.get())
        labels = {
            InputValueType.KT: "Коэффициент трансформации:",
            InputValueType.POINT: "№ Точки учета:",
            InputValueType.SERIAL: "№ Прибора учета:",
        }
        self.entry_label.config(text=labels[current_type])

    def _on_input_type_changed(self, animate_to: int | None = None) -> None:
        self._selector_visual_index = float(self._selector_index())
        self._draw_input_selector()
        self._update_entry_label()
        self._refresh_input_preview()

    def _set_input_value(self, value: str) -> None:
        current_state = str(self.input_entry.cget("state"))
        if current_state == "disabled":
            self.input_entry.config(state="normal")
        self.input_entry.delete(0, tk.END)
        self.input_entry.insert(0, value)
        if current_state == "disabled":
            self.input_entry.config(state="disabled")

    def _on_input_changed(self, _event=None) -> None:
        value = self.input_entry.get().strip()
        self._input_value = value
        if self.mode.get() == ProcessingMode.MANUAL.value:
            self._manual_input_value = value
        elif self.auto_override_enabled:
            self._auto_input_value = value
        self.lookup_status.config(text="", fg=TEXT_GRAY)

    def _refresh_input_preview(self) -> None:
        if self.mode.get() == ProcessingMode.AUTO.value and not self.auto_override_enabled:
            self._refresh_auto_preview()
            return

        value = self.input_entry.get().strip()
        self._input_value = value
        input_type = InputValueType(self.input_type.get())

        if not value:
            if self.mode.get() == ProcessingMode.AUTO.value and self.file_path:
                self._refresh_auto_preview()
            else:
                self.lookup_status.config(text="", fg=TEXT_GRAY)
            return

        if input_type == InputValueType.KT:
            try:
                kt = self.service._parse_required_kt(value)
            except Exception as exc:
                self.lookup_status.config(text=str(exc), fg="#c94b4b")
                return
            text = str(int(kt)) if kt == int(kt) else str(kt)
            self.lookup_status.config(text=f"✓ КТ: {text}", fg="#2e9e5b")
            return

        if not self.service.has_references:
            self.lookup_status.config(text="Справочники не найдены в папке", fg=ORANGE)
            return

        reference = self.service.find_reference(value, input_type)
        if reference is None:
            not_found = (
                "ТУ не найден в загруженных справочниках"
                if input_type == InputValueType.POINT
                else "Заводской номер не найден в загруженных справочниках"
            )
            self.lookup_status.config(text=not_found, fg="#c94b4b")
            return

        kt = reference.transformation_coefficient
        kt_text = "—" if kt is None else (str(int(kt)) if kt == int(kt) else str(kt))
        point_text = reference.point_number or "—"
        serial_text = reference.serial_number or "—"
        self.lookup_status.config(
            text=f"✓ ТУ: {point_text}   ·   Зав. №: {serial_text}   ·   КТ: {kt_text}",
            fg="#2e9e5b",
        )

    def _refresh_auto_preview(self) -> None:
        if not self.file_path:
            self.lookup_status.config(text="", fg=TEXT_GRAY)
            return
        point_number = self.file_path.parent.name
        reference = self.service.find_reference(point_number, InputValueType.POINT)
        if reference is None or reference.transformation_coefficient is None:
            self.lookup_status.config(
                text=f"Авто: ТУ {point_number} не найден в справочниках",
                fg=ORANGE,
            )
            return
        kt = reference.transformation_coefficient
        kt_text = str(int(kt)) if kt == int(kt) else str(kt)
        self.lookup_status.config(
            text=f"Авто: ТУ {point_number}   ·   КТ: {kt_text}",
            fg="#2e9e5b",
        )

    def _refresh_reference_directory(self) -> None:
        try:
            report = self.service.refresh_references()
        except Exception as exc:
            self.reference_label.config(
                text=f"Ошибка чтения справочников: {exc}",
                fg="#c94b4b",
            )
            return

        periods = report.loaded_periods
        if periods:
            loaded = ", ".join(
                f"{MONTH_NAMES_RU.get(item.month, item.month)}_{item.year}"
                for item in periods
            )
            self.reference_label.config(
                text=f"✓ Справочники: {loaded}",
                fg="#2e9e5b",
            )
        else:
            self.reference_label.config(
                text="Справочники не найдены",
                fg=ORANGE,
            )

        if report.errors:
            self.reference_label.config(
                text="Ошибка справочника: " + " | ".join(report.errors[:2]),
                fg="#c94b4b",
            )

    def select_file(self) -> None:
        path = filedialog.askopenfilename(filetypes=[("All supported", "*.xlsx *.html *.txt *.xml")])
        if path:
            self._set_source_file(Path(path))

    def _set_source_file(self, path: Path) -> None:
        if path.suffix.lower() not in {".xlsx", ".html", ".txt", ".xml"}:
            messagebox.showerror("Ошибка", "Поддерживаются только файлы .xlsx, .html, .txt, .xml")
            return
        self.file_path = path
        self._draw_dropzone(filename=path.name)
        self._refresh_reference_directory()
        self._refresh_input_preview()

    def _on_drag_enter(self, event):
        self._draw_dropzone(
            filename=self.file_path.name if self.file_path else None,
            drag_active=True,
        )
        return getattr(event, "action", None)

    def _on_drag_leave(self, event):
        self._draw_dropzone(filename=self.file_path.name if self.file_path else None)
        return getattr(event, "action", None)

    def _on_file_drop(self, event):
        raw = str(event.data).strip()
        if raw.startswith("{") and raw.endswith("}"):
            raw = raw[1:-1]
        path = raw.split("} {")[0] if "} {" in raw else raw
        self._set_source_file(Path(path))
        return getattr(event, "action", None)

    def convert_file(self) -> None:
        if not self.file_path:
            messagebox.showerror("Ошибка", "Выберите файл")
            return
        try:
            self._refresh_reference_directory()
            is_auto_locked = (
                self.mode.get() == ProcessingMode.AUTO.value
                and not self.auto_override_enabled
            )
            current_value = "" if is_auto_locked else self.input_entry.get()
            result = self.service.convert(
                source_path=self.file_path,
                mode=ProcessingMode(self.mode.get()),
                input_text=current_value,
                input_type=InputValueType(self.input_type.get()),
                include_in_loading_statement=self.loading_statement_enabled,
            )
            self._draw_statement_export_button()
            messagebox.showinfo("Готово", f"Файл сохранён!\n{result.output_path}")
        except Exception as exc:
            messagebox.showerror("Ошибка", str(exc))
