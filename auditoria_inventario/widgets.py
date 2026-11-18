"""Componentes gráficos (mismo diseño que Control de Aceites): franja, indicadores, tablas y tarjetas."""
from __future__ import annotations

import tkinter as tk
from tkinter import ttk

from . import tema
from .tema import ACENTO, AZUL, BORDE, FONDO, FUENTE, NAVY, SUAVE, TARJETA, TEXTO, TITULO_C


class FranjaSeguridad(tk.Canvas):
    """Línea de acento ámbar que se desvanece hacia la derecha."""

    def __init__(self, master, alto=4, **kw):
        super().__init__(master, height=alto, highlightthickness=0, bd=0, background=NAVY, **kw)
        self.bind("<Configure>", self._dibujar)

    def _dibujar(self, _=None):
        self.delete("all")
        w, h = self.winfo_width(), int(self["height"])
        if w < 2:
            return
        r0, g0, b0 = (int(ACENTO[i:i + 2], 16) for i in (1, 3, 5))
        r1, g1, b1 = (int(NAVY[i:i + 2], 16) for i in (1, 3, 5))
        pasos = 48
        for k in range(pasos):
            f = (k / (pasos - 1)) ** 1.6
            col = f"#{int(r0 + (r1 - r0) * f):02X}{int(g0 + (g1 - g0) * f):02X}{int(b0 + (b1 - b0) * f):02X}"
            x0, x1 = w * k / pasos, w * (k + 1) / pasos + 1
            self.create_rectangle(x0, 0, x1, h, fill=col, outline="")


class Indicador(tk.Frame):
    """Tarjeta con ícono, título, valor grande y detalle."""

    def __init__(self, master, titulo: str, icono: str, color: str):
        super().__init__(master, background=TARJETA, highlightthickness=1, highlightbackground=BORDE)
        tk.Frame(self, background=color, width=5).pack(side="left", fill="y")
        cuerpo = tk.Frame(self, background=TARJETA)
        cuerpo.pack(side="left", fill="both", expand=True, padx=(10, 10), pady=8)
        cab = tk.Frame(cuerpo, background=TARJETA)
        cab.pack(fill="x")
        self._img = tema.icono(self, icono, 18, color)
        tk.Label(cab, image=self._img, background=TARJETA).pack(side="left")
        tk.Label(cab, text=titulo, background=TARJETA, foreground=SUAVE, font=(FUENTE, 9, "bold")).pack(
            side="left", padx=6)
        self.valor = tk.Label(cuerpo, text="—", background=TARJETA, foreground=TITULO_C, font=(FUENTE, 17, "bold"),
                              anchor="w")
        self.valor.pack(fill="x")
        self.detalle = tk.Label(cuerpo, text="", background=TARJETA, foreground=SUAVE, font=(FUENTE, 8), anchor="w")
        self.detalle.pack(fill="x")

    def fijar(self, valor: str, detalle: str = "", color: str | None = None):
        self.valor.configure(text=valor, foreground=color or TITULO_C)
        self.detalle.configure(text=detalle)


class Desplazable(ttk.Frame):
    """Marco con barra de desplazamiento vertical (rueda del mouse incluida)."""

    def __init__(self, master, fondo=TARJETA, **kw):
        super().__init__(master, **kw)
        self.canvas = tk.Canvas(self, highlightthickness=0, bd=0, background=fondo)
        self.barra = ttk.Scrollbar(self, orient="vertical", command=self.canvas.yview)
        self.interior = tk.Frame(self.canvas, background=fondo)
        self._win = self.canvas.create_window(0, 0, window=self.interior, anchor="nw")
        self.canvas.configure(yscrollcommand=self.barra.set)
        self.canvas.pack(side="left", fill="both", expand=True)
        self.barra.pack(side="right", fill="y")
        self.interior.bind("<Configure>", lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all")))
        self.canvas.bind("<Configure>", lambda e: self.canvas.itemconfigure(self._win, width=e.width))
        self.canvas.bind("<Enter>", lambda e: self.canvas.bind_all("<MouseWheel>", self._rueda))
        self.canvas.bind("<Leave>", lambda e: self.canvas.unbind_all("<MouseWheel>"))

    def _rueda(self, e):
        if self.canvas.yview() != (0.0, 1.0):
            self.canvas.yview_scroll(int(-e.delta / 120) or (-1 if e.delta > 0 else 1), "units")


def tabla(master, columnas, alto=10) -> ttk.Treeview:
    """columnas: [(id, título, ancho, alineación)]."""
    marco = ttk.Frame(master)
    tv = ttk.Treeview(marco, columns=[c[0] for c in columnas], show="headings", height=alto)
    for cid, tit, ancho, al in columnas:
        tv.heading(cid, text=tit, anchor="center")
        tv.column(cid, width=ancho, minwidth=40, anchor=al, stretch=True)
    lineas = max(t.count("\n") + 1 for _, t, _, _ in columnas)
    if lineas > 1:
        # El alto del encabezado lo fija la columna oculta #0: así los títulos de 2 líneas no se recortan.
        tv.heading("#0", text="\n".join(" " * lineas))
    sy = ttk.Scrollbar(marco, orient="vertical", command=tv.yview)
    sx = ttk.Scrollbar(marco, orient="horizontal", command=tv.xview)
    tv.configure(yscrollcommand=sy.set, xscrollcommand=sx.set)
    tv.grid(row=0, column=0, sticky="nsew")
    sy.grid(row=0, column=1, sticky="ns")
    sx.grid(row=1, column=0, sticky="ew")
    marco.rowconfigure(0, weight=1)
    marco.columnconfigure(0, weight=1)
    tv.marco = marco
    for est, col in tema.FONDO_ESTADO.items():
        tv.tag_configure(est, background=col)
    tv.tag_configure("total", background=tema.TOTAL_BG, font=(FUENTE, 9, "bold"))
    tv.tag_configure("par", background=tema.ALT)
    return tv


def tarjeta(master, titulo: str | None = None, icono: str | None = None) -> tk.Frame:
    """Tarjeta blanca con borde y título opcional. Devuelve el marco interior."""
    ext = tk.Frame(master, background=TARJETA, highlightthickness=1, highlightbackground=BORDE)
    if titulo:
        cab = tk.Frame(ext, background=TARJETA)
        cab.pack(fill="x", padx=14, pady=(10, 2))
        if icono:
            img = tema.icono(ext, icono, 16, ACENTO)
            lb = tk.Label(cab, image=img, background=TARJETA)
            lb.image = img
            lb.pack(side="left", padx=(0, 6))
        tk.Label(cab, text=titulo, background=TARJETA, foreground=TITULO_C, font=(FUENTE, 11, "bold")).pack(side="left")
        ext.cab = cab
    inner = tk.Frame(ext, background=TARJETA)
    inner.pack(fill="both", expand=True, padx=14, pady=(4, 12))
    ext.inner = inner
    return ext


__all__ = ["FranjaSeguridad", "Indicador", "Desplazable", "tabla", "tarjeta",
           "AZUL", "FONDO", "TEXTO"]
