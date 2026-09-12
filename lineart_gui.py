#!/usr/bin/env python3
"""
lineart_gui.py
---------------
Interfaz gráfica que replica los 5 modos de
online.rapidresizer.com/photograph-to-pattern.php:
    Edges | Thin | Threshold | Adaptive | Color

CÓMO USARLO (directo en Python):
    pip install opencv-python numpy pillow
    python3 lineart_gui.py
    (necesita rapidresizer_core.py en la misma carpeta)

CÓMO CONVERTIRLO A .EXE (en Windows):
    pip install pyinstaller opencv-python numpy pillow
    pyinstaller --onefile --windowed --name LineArtConverter lineart_gui.py
    El .exe queda en la carpeta "dist".
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox, colorchooser
import cv2
import numpy as np
from PIL import Image, ImageTk

from rapidresizer_core import mode_edges, mode_thin, mode_threshold, mode_adaptive, mode_color


class LineArtApp:
    PREVIEW_MAX_SIZE = 460

    def __init__(self, root):
        self.root = root
        self.root.title("Convertidor a Lineart / Stencil (estilo RapidResizer)")
        self.root.geometry("1100x680")
        self.root.minsize(900, 560)

        self.original_bgr = None
        self.result_img = None
        self._update_job = None

        # Variables compartidas por pestaña (cada modo tiene su propio set,
        # igual que la web recuerda el estado de cada pestaña por separado)
        self.threshold_vars = {
            "edges": tk.DoubleVar(value=128),
            "canny": tk.DoubleVar(value=128),
            "blobs": tk.DoubleVar(value=128),
            "adaptive": tk.DoubleVar(value=32),
            "color-threshold": tk.DoubleVar(value=128),
        }
        self.blur_vars = {m: tk.DoubleVar(value=1.0) for m in self.threshold_vars}
        self.outline_vars = {
            "blobs": tk.BooleanVar(value=False),
            "adaptive": tk.BooleanVar(value=False),
            "color-threshold": tk.BooleanVar(value=False),
        }
        self.target_color_rgb = (150, 40, 40)
        self.tolerance_var = tk.DoubleVar(value=25.0)

        self.current_mode = tk.StringVar(value="edges")

        self._build_ui()

    # ---------------------------------------------------------------- UI ---
    def _build_ui(self):
        top = ttk.Frame(self.root, padding=10)
        top.pack(side="top", fill="x")
        ttk.Button(top, text="Abrir imagen…", command=self.open_image).pack(side="left")
        ttk.Button(top, text="Guardar resultado…", command=self.save_result).pack(side="left", padx=(8, 0))

        # Pestañas iguales a la web: Edges | Thin | Threshold | Adaptive | Color
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(side="top", fill="x", padx=10, pady=(0, 4))

        self.tab_edges = self._make_simple_tab("edges")
        self.tab_canny = self._make_simple_tab("canny")
        self.tab_blobs = self._make_full_tab("blobs")
        self.tab_adaptive = self._make_full_tab("adaptive")
        self.tab_color = self._make_color_tab("color-threshold")

        self.notebook.add(self.tab_edges, text="Edges")
        self.notebook.add(self.tab_canny, text="Thin")
        self.notebook.add(self.tab_blobs, text="Threshold")
        self.notebook.add(self.tab_adaptive, text="Adaptive")
        self.notebook.add(self.tab_color, text="Color")
        self.notebook.bind("<<NotebookTabChanged>>", self._on_tab_changed)

        # Previsualización
        preview = ttk.Frame(self.root, padding=10)
        preview.pack(side="top", fill="both", expand=True)
        preview.columnconfigure(0, weight=1)
        preview.columnconfigure(1, weight=1)
        preview.rowconfigure(1, weight=1)

        ttk.Label(preview, text="ORIGINAL").grid(row=0, column=0)
        ttk.Label(preview, text="RESULTADO").grid(row=0, column=1)
        self.original_label = ttk.Label(preview, background="#222")
        self.original_label.grid(row=1, column=0, sticky="nsew", padx=4, pady=4)
        self.result_label = ttk.Label(preview, background="#222")
        self.result_label.grid(row=1, column=1, sticky="nsew", padx=4, pady=4)

        self.status_var = tk.StringVar(value="Abre una imagen para empezar.")
        ttk.Label(self.root, textvariable=self.status_var, padding=(10, 4)).pack(side="bottom", fill="x")

    def _make_simple_tab(self, mode: str) -> ttk.Frame:
        """Pestañas Edges / Thin: slider gris (threshold) + slider Sharp<->Soft (blur)."""
        frame = ttk.Frame(self.notebook, padding=10)
        self._add_threshold_slider(frame, mode)
        self._add_blur_slider(frame, mode)
        return frame

    def _make_full_tab(self, mode: str) -> ttk.Frame:
        """Pestañas Threshold / Adaptive: igual que arriba + checkbox Outline."""
        frame = ttk.Frame(self.notebook, padding=10)
        self._add_threshold_slider(frame, mode)
        self._add_blur_slider(frame, mode)
        ttk.Checkbutton(
            frame, text="Outline (convierte las áreas en solo contornos)",
            variable=self.outline_vars[mode], command=self.schedule_update
        ).pack(anchor="w", pady=(6, 0))
        return frame

    def _make_color_tab(self, mode: str) -> ttk.Frame:
        frame = ttk.Frame(self.notebook, padding=10)

        color_row = ttk.Frame(frame)
        color_row.pack(fill="x")
        ttk.Label(color_row, text="Color objetivo:").pack(side="left")
        self.color_swatch = tk.Canvas(color_row, width=28, height=18, bg=self._rgb_to_hex(self.target_color_rgb),
                                       highlightthickness=1, highlightbackground="#000")
        self.color_swatch.pack(side="left", padx=8)
        ttk.Button(color_row, text="Elegir color…", command=self.pick_color).pack(side="left")

        tol_row = ttk.Frame(frame)
        tol_row.pack(fill="x", pady=(10, 0))
        ttk.Label(tol_row, text="Tolerancia").pack(side="left")
        ttk.Scale(tol_row, from_=0, to=100, variable=self.tolerance_var, orient="horizontal",
                  command=lambda _=None: self.schedule_update()).pack(side="left", fill="x", expand=True, padx=8)

        self._add_blur_slider(frame, mode)
        ttk.Checkbutton(
            frame, text="Outline (convierte las áreas en solo contornos)",
            variable=self.outline_vars[mode], command=self.schedule_update
        ).pack(anchor="w", pady=(6, 0))
        return frame

    def _add_threshold_slider(self, frame, mode):
        row = ttk.Frame(frame)
        row.pack(fill="x")
        ttk.Label(row, text="Negro").pack(side="left")
        ttk.Scale(row, from_=0, to=255, variable=self.threshold_vars[mode], orient="horizontal",
                  command=lambda _=None: self.schedule_update()).pack(side="left", fill="x", expand=True, padx=8)
        ttk.Label(row, text="Blanco").pack(side="left")

    def _add_blur_slider(self, frame, mode):
        row = ttk.Frame(frame)
        row.pack(fill="x", pady=(8, 0))
        ttk.Label(row, text="Sharp").pack(side="left")
        ttk.Scale(row, from_=0, to=4, variable=self.blur_vars[mode], orient="horizontal",
                  command=lambda _=None: self.schedule_update()).pack(side="left", fill="x", expand=True, padx=8)
        ttk.Label(row, text="Soft").pack(side="left")

    # ----------------------------------------------------------- acciones ---
    def _on_tab_changed(self, _event=None):
        idx = self.notebook.index(self.notebook.select())
        self.current_mode.set(["edges", "canny", "blobs", "adaptive", "color-threshold"][idx])
        self.schedule_update()

    def pick_color(self):
        rgb, hex_color = colorchooser.askcolor(color=self._rgb_to_hex(self.target_color_rgb),
                                                title="Elige el color objetivo")
        if rgb is None:
            return
        self.target_color_rgb = tuple(int(c) for c in rgb)
        self.color_swatch.configure(bg=hex_color)
        self.schedule_update()

    @staticmethod
    def _rgb_to_hex(rgb):
        return "#{:02x}{:02x}{:02x}".format(*[int(c) for c in rgb])

    def open_image(self):
        path = filedialog.askopenfilename(
            title="Selecciona una imagen",
            filetypes=[("Imágenes", "*.jpg *.jpeg *.png *.bmp *.webp"), ("Todos los archivos", "*.*")]
        )
        if not path:
            return
        img = cv2.imread(path)
        if img is None:
            messagebox.showerror("Error", "No se pudo abrir esa imagen.")
            return
        self.original_bgr = img
        self.status_var.set(f"Cargada: {path}")
        self._show_gray_or_bgr_on_label(img, self.original_label)
        self.update_result()

    def schedule_update(self):
        if self._update_job is not None:
            self.root.after_cancel(self._update_job)
        self._update_job = self.root.after(120, self.update_result)

    def update_result(self):
        if self.original_bgr is None:
            return
        mode = self.current_mode.get()
        img = self.original_bgr

        if mode == "edges":
            result = mode_edges(img, blur=self.blur_vars[mode].get(), threshold=self.threshold_vars[mode].get())
        elif mode == "canny":
            result = mode_thin(img, blur=self.blur_vars[mode].get(), threshold=self.threshold_vars[mode].get())
        elif mode == "blobs":
            result = mode_threshold(img, blur=self.blur_vars[mode].get(), threshold=self.threshold_vars[mode].get(),
                                     outline=self.outline_vars[mode].get())
        elif mode == "adaptive":
            result = mode_adaptive(img, blur=self.blur_vars[mode].get(), threshold=self.threshold_vars[mode].get(),
                                    outline=self.outline_vars[mode].get())
        else:  # color-threshold
            result = mode_color(img, target_rgb=self.target_color_rgb, blur=self.blur_vars[mode].get(),
                                 tolerance=self.tolerance_var.get(), outline=self.outline_vars[mode].get())

        self.result_img = result
        self._show_gray_or_bgr_on_label(result, self.result_label)
        self.status_var.set(f"Modo: {mode}")

    def save_result(self):
        if self.result_img is None:
            messagebox.showwarning("Nada que guardar", "Primero abre y procesa una imagen.")
            return
        path = filedialog.asksaveasfilename(
            title="Guardar resultado", defaultextension=".png",
            filetypes=[("PNG", "*.png"), ("JPEG", "*.jpg")]
        )
        if not path:
            return
        cv2.imwrite(path, self.result_img)
        self.status_var.set(f"Guardado en: {path}")
        messagebox.showinfo("Listo", f"Imagen guardada en:\n{path}")

    # ------------------------------------------------------------- helpers ---
    def _show_gray_or_bgr_on_label(self, img, label_widget):
        if img.ndim == 2:
            img_rgb = cv2.cvtColor(img, cv2.COLOR_GRAY2RGB)
        else:
            img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        pil_img = Image.fromarray(img_rgb.astype(np.uint8))

        w, h = pil_img.size
        scale = min(self.PREVIEW_MAX_SIZE / w, self.PREVIEW_MAX_SIZE / h, 1.0)
        new_size = (max(1, int(w * scale)), max(1, int(h * scale)))
        pil_img = pil_img.resize(new_size, Image.LANCZOS)

        tk_img = ImageTk.PhotoImage(pil_img)
        label_widget.configure(image=tk_img)
        label_widget.image = tk_img


def main():
    root = tk.Tk()
    LineArtApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
