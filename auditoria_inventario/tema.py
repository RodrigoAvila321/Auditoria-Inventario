"""Tema visual «grafito + ámbar» (mismo diseño que Control de Aceites): paleta, estilos ttk e íconos."""
from __future__ import annotations

import math
import tkinter as tk
from tkinter import ttk

from PIL import Image, ImageDraw, ImageTk

# ------------------------------------------------------------------ paleta (grafito + ámbar)
FONDO = "#15171B"        # fondo de la aplicación
TARJETA = "#1F2228"      # tarjetas y ventanas
TARJETA2 = "#272B32"     # campos, filas alternas
ALT = "#23262D"          # filas alternas en tablas
TOTAL_BG = "#2D3139"     # filas de total
BORDE = "#353A43"
NAVY = "#0E1013"         # barra superior / encabezados oscuros
NAVY2 = "#2A2F37"        # encabezados de tabla
NAVY_HOVER = "#1A1D22"
TEXTO = "#E4E6EA"
TITULO_C = "#F5F6F8"     # títulos
SUAVE = "#99A1AD"
ACENTO = "#F2A62B"       # ámbar aceite
AMBAR = "#D9902A"        # serie «sobrante» y detalles color aceite
AMARILLO = "#F6C343"
VERDE = "#3DBE7A"
ROJO = "#EF5E5B"
AZUL = "#4FA3EE"
MORADO = "#A57BE6"
GRIS = "#4A515C"
SERIE_INI = "#7D8BA3"    # serie «stock inicial» del gráfico

COLOR_ESTADO = {"No está en base": AMARILLO, "EXTRA": ROJO, "Cuadrado": VERDE, "Faltante parcial": AZUL,
                "Sin hallazgos": SUAVE}
FONDO_ESTADO = {"No está en base": "#4A4119", "EXTRA": "#4A2426", "Cuadrado": "#1D3A2B", "Faltante parcial": "#1C3148"}

FUENTE = "Segoe UI"

_cache: dict = {}


def aclarar(color: str, f: float = 0.15) -> str:
    c = color.lstrip("#")
    r, g, b = (int(c[i:i + 2], 16) for i in (0, 2, 4))
    r, g, b = (int(v + (255 - v) * f) for v in (r, g, b))
    return f"#{r:02X}{g:02X}{b:02X}"


def oscurecer(color: str, f: float = 0.15) -> str:
    c = color.lstrip("#")
    r, g, b = (int(c[i:i + 2], 16) for i in (0, 2, 4))
    r, g, b = (int(v * (1 - f)) for v in (r, g, b))
    return f"#{r:02X}{g:02X}{b:02X}"


def aplicar(root: tk.Tk):
    s = ttk.Style(root)
    try:
        s.theme_use("clam")
    except tk.TclError:
        pass
    base = (FUENTE, 10)
    # Solo widgets tk clásicos: en ttk el «*Font» del option database taparía la fuente de cada estilo.
    for clase in ("Label", "Button", "Entry", "Text", "Listbox", "Spinbox", "Menu", "Message"):
        root.option_add(f"*{clase}.font", base)
    root.option_add("*TCombobox*Listbox.font", base)
    root.option_add("*TCombobox*Listbox.background", TARJETA2)
    root.option_add("*TCombobox*Listbox.foreground", TEXTO)
    root.option_add("*TCombobox*Listbox.selectBackground", ACENTO)
    root.option_add("*TCombobox*Listbox.selectForeground", NAVY)
    root.option_add("*Toplevel.background", TARJETA)
    root.configure(background=FONDO)
    s.configure(".", font=base, background=TARJETA, foreground=TEXTO, bordercolor=BORDE,
                lightcolor=BORDE, darkcolor=BORDE, troughcolor=FONDO, focuscolor=ACENTO,
                selectbackground=ACENTO, selectforeground=NAVY, insertcolor=TEXTO, fieldbackground=TARJETA2)
    for est in ("TFrame", "TLabel", "TCheckbutton", "TRadiobutton", "TLabelframe", "TLabelframe.Label"):
        s.configure(est, background=TARJETA, foreground=TEXTO)
    s.configure("Cab.TLabel", foreground=SUAVE, font=(FUENTE, 9, "bold"))
    campo = dict(fieldbackground=TARJETA2, foreground=TEXTO, insertcolor=ACENTO, bordercolor=BORDE,
                 lightcolor=TARJETA2, darkcolor=TARJETA2)
    s.configure("TEntry", padding=5, **campo)
    s.map("TEntry", bordercolor=[("focus", ACENTO)], lightcolor=[("focus", ACENTO)])
    s.configure("TSpinbox", padding=4, arrowsize=12, arrowcolor=ACENTO, background=TARJETA2, **campo)
    s.map("TSpinbox", bordercolor=[("focus", ACENTO)], lightcolor=[("focus", ACENTO)])
    s.configure("TCombobox", padding=4, arrowsize=14, arrowcolor=ACENTO, background=TARJETA2, **campo)
    s.map("TCombobox", fieldbackground=[("readonly", TARJETA2)], foreground=[("readonly", TEXTO)],
          selectbackground=[("readonly", TARJETA2)], selectforeground=[("readonly", TEXTO)],
          bordercolor=[("focus", ACENTO)])
    s.configure("Treeview", rowheight=28, background=TARJETA, fieldbackground=TARJETA, foreground=TEXTO,
                borderwidth=0, font=(FUENTE, 9))
    s.map("Treeview", background=[("selected", "#5A4521")], foreground=[("selected", TITULO_C)])
    s.configure("Treeview.Heading", background=NAVY2, foreground=ACENTO, font=(FUENTE, 8, "bold"),
                relief="flat", padding=(4, 6), bordercolor=BORDE)
    s.map("Treeview.Heading", background=[("active", "#353B45")])
    for orient in ("Vertical", "Horizontal"):
        s.configure(f"{orient}.TScrollbar", arrowsize=12, background="#3A404A", troughcolor=TARJETA,
                    bordercolor=TARJETA, arrowcolor=SUAVE, lightcolor="#3A404A", darkcolor="#3A404A")
        s.map(f"{orient}.TScrollbar", background=[("active", "#4A515C")])
    for nombre, color, texto in (("Verde", "#2E9C63", "#FFFFFF"), ("Rojo", "#C9443F", "#FFFFFF"),
                                 ("Azul", "#2F7FC6", "#FFFFFF"), ("Naranja", ACENTO, NAVY),
                                 ("Gris", GRIS, TEXTO), ("Morado", "#7E58C2", "#FFFFFF"), ("Navy", "#343A44", TEXTO)):
        for sufijo, pad, tam in (("", (14, 7), 9), ("Grande", (18, 12), 10)):
            est = f"{nombre}{sufijo}.TButton"
            s.configure(est, background=color, foreground=texto, font=(FUENTE, tam, "bold"),
                        padding=pad, borderwidth=0, bordercolor=color, lightcolor=color, darkcolor=color,
                        focuscolor=color, relief="flat")
            act = aclarar(color, 0.15)
            dis = "#2B2F36"
            s.map(est, background=[("disabled", dis), ("pressed", oscurecer(color, 0.2)), ("active", act)],
                  foreground=[("disabled", "#5E6570")],
                  bordercolor=[("disabled", dis), ("active", act)],
                  lightcolor=[("disabled", dis), ("active", act)],
                  darkcolor=[("disabled", dis), ("active", act)])


# ------------------------------------------------------------------ íconos
def _caja(d, x0, y0, x1, y1, color, fondo):
    """Caja de repuestos con tapa."""
    d.rounded_rectangle((x0, y0, x1, y1), radius=14, fill=color)
    d.rectangle((x0, y0 + (y1 - y0) * 0.28 - 5, x1, y0 + (y1 - y0) * 0.28 + 5), fill=fondo)
    cx = (x0 + x1) / 2
    d.rectangle((cx - 14, y0, cx + 14, y0 + (y1 - y0) * 0.55), fill=fondo)


def _lupa(d, cx, cy, r, grosor, color):
    d.ellipse((cx - r, cy - r, cx + r, cy + r), outline=color, width=grosor)
    k = r * 0.72
    d.line((cx + k, cy + k, cx + r * 1.75, cy + r * 1.75), fill=color, width=int(grosor * 1.5))


def _engranaje(d, cx, cy, r_ext, r_int, r_hueco, dientes, color):
    pts = []
    for i in range(dientes * 4):
        a = 2 * math.pi * i / (dientes * 4)
        r = r_ext if (i % 4) in (1, 2) else r_int
        pts.append((cx + r * math.cos(a), cy + r * math.sin(a)))
    d.polygon(pts, fill=color)
    d.ellipse((cx - r_hueco, cy - r_hueco, cx + r_hueco, cy + r_hueco), fill=(0, 0, 0, 0))


def dibujar(nombre: str, color="#FFFFFF") -> Image.Image:
    n = 256
    img = Image.new("RGBA", (n, n), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    c = color
    T = (0, 0, 0, 0)
    if nombre == "logo":
        d.rounded_rectangle((0, 0, 255, 255), radius=56, fill="#23272E")
        d.rounded_rectangle((10, 10, 245, 245), radius=48, outline=ACENTO, width=10)
        _caja(d, 40, 70, 176, 206, ACENTO, "#23272E")                                # caja de repuestos
        d.ellipse((112, 110, 222, 220), fill="#23272E")                              # lupa
        _lupa(d, 160, 158, 38, 16, "#FFFFFF")
    elif nombre == "caja":
        _caja(d, 24, 40, 232, 232, c, T)
    elif nombre == "excel":
        d.polygon([(52, 18), (164, 18), (212, 66), (212, 238), (52, 238)], fill=c)
        d.polygon([(164, 18), (164, 66), (212, 66)], fill=T)
        for x in (84, 132):
            for y in (100, 146, 192):
                d.rectangle((x, y - 14, x + 40, y + 14), fill=T)
    elif nombre == "cargar":
        d.polygon([(52, 18), (164, 18), (212, 66), (212, 238), (52, 238)], fill=c)
        d.polygon([(164, 18), (164, 66), (212, 66)], fill=T)
        d.rectangle((116, 120, 148, 206), fill=T)
        d.polygon([(84, 132), (180, 132), (132, 82)], fill=T)
    elif nombre == "exportar":
        d.polygon([(52, 18), (164, 18), (212, 66), (212, 238), (52, 238)], fill=c)
        d.polygon([(164, 18), (164, 66), (212, 66)], fill=T)
        d.rectangle((116, 84, 148, 160), fill=T)
        d.polygon([(84, 150), (180, 150), (132, 204)], fill=T)
    elif nombre == "buscar":
        _lupa(d, 104, 104, 70, 26, c)
    elif nombre == "agregar" or nombre == "nuevo":
        d.rounded_rectangle((104, 24, 152, 232), radius=14, fill=c)
        d.rounded_rectangle((24, 104, 232, 152), radius=14, fill=c)
    elif nombre == "extra":                                                          # bandera
        d.rectangle((40, 20, 64, 240), fill=c)
        d.polygon([(64, 28), (224, 28), (186, 84), (224, 140), (64, 140)], fill=c)
    elif nombre == "alerta":
        d.polygon([(128, 18), (244, 230), (12, 230)], fill=c)
        d.rounded_rectangle((114, 84, 142, 168), radius=8, fill=T)
        d.ellipse((112, 184, 144, 216), fill=T)
    elif nombre == "faltante":
        d.ellipse((24, 24, 232, 232), outline=c, width=22)
        d.rounded_rectangle((70, 112, 186, 144), radius=10, fill=c)
    elif nombre == "lista":
        for y in (52, 128, 204):
            d.ellipse((22, y - 18, 58, y + 18), fill=c)
            d.rounded_rectangle((80, y - 14, 236, y + 14), radius=8, fill=c)
    elif nombre == "entrega":
        d.rounded_rectangle((30, 40, 226, 226), radius=24, outline=c, width=20)
        d.line((76, 136, 116, 176, 186, 92), fill=c, width=26, joint="curve")
    elif nombre == "borrar":
        d.rectangle((40, 44, 216, 68), fill=c)
        d.rectangle((100, 20, 156, 44), fill=c)
        d.polygon([(60, 80), (196, 80), (184, 238), (72, 238)], fill=c)
        for x in (104, 152):
            d.rectangle((x - 6, 104, x + 6, 212), fill=T)
    elif nombre == "config":
        _engranaje(d, 128, 128, 112, 86, 36, 9, c)
    elif nombre == "ayuda":
        d.ellipse((20, 20, 236, 236), fill=c)
        d.ellipse((112, 58, 144, 90), fill=T)
        d.rounded_rectangle((112, 110, 144, 198), radius=10, fill=T)
    elif nombre == "panel":
        d.arc((22, 40, 234, 252), 180, 360, fill=c, width=30)
        d.line((128, 146, 186, 82), fill=c, width=18)
        d.ellipse((104, 122, 152, 170), fill=c)
        d.rounded_rectangle((60, 196, 196, 226), radius=10, fill=c)
    else:
        d.ellipse((60, 60, 196, 196), fill=c)
    return img


def icono(root, nombre: str, tam: int = 18, color="#FFFFFF") -> ImageTk.PhotoImage:
    clave = (id(root.tk), nombre, tam, color)
    if clave not in _cache:
        img = dibujar(nombre, color).resize((tam, tam), Image.LANCZOS)
        _cache[clave] = ImageTk.PhotoImage(img, master=root)
    return _cache[clave]


def guardar_ico(ruta: str):
    dibujar("logo").save(ruta, sizes=[(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)])


def guardar_png(nombre: str, ruta: str, color="#FFFFFF", tam: int = 256):
    dibujar(nombre, color).resize((tam, tam), Image.LANCZOS).save(ruta)
