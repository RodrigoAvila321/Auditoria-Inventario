"""Ventanas de carga: Excel base (diferencias) y Excel de repuestos encontrados (hallazgos)."""
from __future__ import annotations

import datetime as dt
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from . import TITULO, tema
from .calculo import ESTADO_NO_BASE, calcular_resultado, crear_hallazgos, extras, preparar_base
from .excel import (CLAVES_CANT, CLAVES_CODIGO, CLAVES_DESC, CLAVES_DIF, EXTENSIONES, ErrorArchivo, adivinar,
                    columna, detectar_encabezado, filas_crudas, hojas, tabla)
from .tema import ACENTO, FUENTE, NAVY, ROJO, SUAVE, TARJETA, TEXTO, TITULO_C, VERDE
from .util import fmt_num
from .widgets import FranjaSeguridad
from .widgets import tabla as tabla_tv

SIN_DESC = "(sin descripción)"
SIN_CANT = "(sin columna: cada fila cuenta 1)"


class Dialogo(tk.Toplevel):
    """Ventana modal con encabezado oscuro y franja ámbar (igual que Control de Aceites)."""

    def __init__(self, master, titulo: str, subtitulo: str = "", icono: str = "excel", ancho=980, alto=None):
        super().__init__(master)
        self.withdraw()
        self.title(f"{titulo} - {TITULO}")
        self.configure(background=TARJETA)
        self.transient(master.winfo_toplevel())
        self.resizable(True, True)
        self.resultado = None
        cab = tk.Frame(self, background=NAVY)
        cab.pack(fill="x")
        self._ico = tema.icono(self, icono, 30, ACENTO)
        tk.Label(cab, image=self._ico, background=NAVY).pack(side="left", padx=(18, 10), pady=12)
        txt = tk.Frame(cab, background=NAVY)
        txt.pack(side="left", fill="x", pady=10)
        tk.Label(txt, text=titulo, background=NAVY, foreground="#FFFFFF", font=(FUENTE, 14, "bold"),
                 anchor="w").pack(fill="x")
        if subtitulo:
            tk.Label(txt, text=subtitulo, background=NAVY, foreground="#B9C4D3", font=(FUENTE, 9),
                     anchor="w", justify="left").pack(fill="x")
        FranjaSeguridad(self, alto=6).pack(fill="x")
        self.pie = tk.Frame(self, background=TARJETA)
        self.pie.pack(side="bottom", fill="x", padx=18, pady=(0, 14))
        self.cuerpo = tk.Frame(self, background=TARJETA)
        self.cuerpo.pack(fill="both", expand=True, padx=18, pady=12)
        self.error = tk.Label(self.pie, text="", background=TARJETA, foreground=ROJO, font=(FUENTE, 9, "bold"),
                              anchor="w", justify="left", wraplength=ancho - 340)
        self.error.pack(side="left", fill="x", expand=True)
        self._geom = (ancho, alto)
        self.bind("<Escape>", lambda e: self.cancelar())
        self.protocol("WM_DELETE_WINDOW", self.cancelar)

    def boton(self, texto, estilo, cmd):
        b = ttk.Button(self.pie, text=texto, style=f"{estilo}.TButton", command=cmd)
        b.pack(side="right", padx=(8, 0))
        return b

    def mostrar(self):
        self.update_idletasks()
        w, h = self._geom
        h = h or self.winfo_reqheight()
        sw, sh = self.winfo_screenwidth(), self.winfo_screenheight()
        w, h = min(w, sw - 40), min(h, sh - 80)
        x = max(0, (sw - w) // 2)
        y = max(0, (sh - h) // 2 - 20)
        self.geometry(f"{w}x{h}+{x}+{y}")
        self.deiconify()
        self.lift()
        try:
            self.grab_set()
        except tk.TclError:
            pass
        self.focus_force()
        self.wait_window()
        return self.resultado

    def cancelar(self):
        self.resultado = None
        self.destroy()


def elegir_archivo(master, titulo: str) -> str | None:
    ruta = filedialog.askopenfilename(parent=master, title=titulo, filetypes=EXTENSIONES)
    return ruta or None


def _etiqueta(master, texto):
    return tk.Label(master, text=texto, background=TARJETA, foreground=SUAVE, font=(FUENTE, 9, "bold"), anchor="w")


class _DialogoExcel(Dialogo):
    """Base común: archivo, hoja, fila de encabezados, elección de columnas y vista previa del archivo."""

    texto_aceptar = "Aceptar"

    def __init__(self, master, ruta: str, titulo: str, subtitulo: str, icono: str, alto=720):
        super().__init__(master, titulo, subtitulo, icono, ancho=1040, alto=alto)
        self.ruta = ruta
        self.columnas: list[str] = []
        self.datos: list[list] = []
        self._filas: dict[str, list[list]] = {}
        c = self.cuerpo

        fila = tk.Frame(c, background=TARJETA)
        fila.pack(fill="x")
        _etiqueta(fila, "ARCHIVO").pack(side="left")
        self.lbl_archivo = tk.Label(fila, text="", background=TARJETA, foreground=TITULO_C,
                                    font=(FUENTE, 10, "bold"), anchor="w")
        self.lbl_archivo.pack(side="left", padx=(8, 12))
        ttk.Button(fila, text="Cambiar archivo…", style="Navy.TButton", command=self._cambiar).pack(side="left")

        fila = tk.Frame(c, background=TARJETA)
        fila.pack(fill="x", pady=(10, 0))
        _etiqueta(fila, "Hoja").grid(row=0, column=0, sticky="w")
        _etiqueta(fila, "Fila de encabezados").grid(row=0, column=1, sticky="w", padx=(14, 0))
        self.v_hoja = tk.StringVar()
        self.cb_hoja = ttk.Combobox(fila, textvariable=self.v_hoja, state="readonly", width=30)
        self.cb_hoja.grid(row=1, column=0, sticky="w")
        self.cb_hoja.bind("<<ComboboxSelected>>", lambda e: self._cargar_hoja())
        self.v_fila = tk.IntVar(value=1)
        self.sp_fila = ttk.Spinbox(fila, from_=1, to=500, textvariable=self.v_fila, width=6,
                                   command=self._aplicar_encabezado)
        self.sp_fila.grid(row=1, column=1, sticky="w", padx=(14, 0))
        self.sp_fila.bind("<Return>", lambda e: self._aplicar_encabezado())
        self.sp_fila.bind("<FocusOut>", lambda e: self._aplicar_encabezado())
        tk.Label(fila, text="Se detecta sola; cámbiela si los títulos de las columnas no están en la fila 1.",
                 background=TARJETA, foreground=SUAVE, font=(FUENTE, 8)).grid(row=1, column=2, sticky="w", padx=10)

        self.marco_cols = tk.Frame(c, background=TARJETA)
        self.marco_cols.pack(fill="x", pady=(12, 0))
        self._construir_columnas(self.marco_cols)

        self.lbl_resumen = tk.Label(c, text="", background=TARJETA, foreground=TEXTO, font=(FUENTE, 10, "bold"),
                                    anchor="w", justify="left")
        self.lbl_resumen.pack(fill="x", pady=(12, 0))
        self.lbl_avisos = tk.Label(c, text="", background=TARJETA, foreground=tema.AMARILLO, font=(FUENTE, 9),
                                   anchor="w", justify="left", wraplength=980)
        self.lbl_avisos.pack(fill="x")

        self._extra_ui(c)

        _etiqueta(c, "VISTA PREVIA DEL ARCHIVO (primeras filas)").pack(fill="x", pady=(10, 2))
        self.marco_prev = tk.Frame(c, background=TARJETA)
        self.marco_prev.pack(fill="both", expand=True)

        self.boton("Cancelar", "Gris", self.cancelar)
        self.b_ok = self.boton(self.texto_aceptar, "Naranja", self.aceptar)
        self.after(10, self._cargar_archivo)

    # -- a implementar por cada diálogo
    def _construir_columnas(self, marco):
        raise NotImplementedError

    def _extra_ui(self, marco):
        pass

    def _poblar_columnas(self):
        raise NotImplementedError

    def _actualizar(self):
        raise NotImplementedError

    # -- comunes
    def _combo(self, marco, col, titulo, ancho=30):
        _etiqueta(marco, titulo).grid(row=0, column=col, sticky="w", padx=(0 if col == 0 else 14, 0))
        v = tk.StringVar()
        cb = ttk.Combobox(marco, textvariable=v, state="readonly", width=ancho)
        cb.grid(row=1, column=col, sticky="w", padx=(0 if col == 0 else 14, 0))
        cb.bind("<<ComboboxSelected>>", lambda e: self._actualizar())
        return v, cb

    def _cambiar(self):
        ruta = elegir_archivo(self, "Seleccione el archivo")
        if ruta:
            self.ruta = ruta
            self._filas.clear()
            self._cargar_archivo()

    def _cargar_archivo(self):
        self.lbl_archivo.configure(text=Path(self.ruta).name)
        self.error.configure(text="")
        try:
            nombres = hojas(self.ruta)
        except ErrorArchivo as e:
            self._sin_datos(str(e))
            return
        self.cb_hoja.configure(values=nombres)
        self.v_hoja.set(nombres[0] if nombres else "")
        self._cargar_hoja(primera=True)

    def _filas_hoja(self, hoja):
        if hoja not in self._filas:
            self._filas[hoja] = filas_crudas(self.ruta, hoja)
        return self._filas[hoja]

    def _cargar_hoja(self, primera=False):
        try:
            filas = self._filas_hoja(self.v_hoja.get())
            if primera and not filas:
                # Si la primera hoja está vacía, usar la primera con datos
                for h in self.cb_hoja.cget("values"):
                    if self._filas_hoja(h):
                        self.v_hoja.set(h)
                        filas = self._filas_hoja(h)
                        break
        except ErrorArchivo as e:
            self._sin_datos(str(e))
            return
        except Exception as e:  # noqa: BLE001
            self._sin_datos(f"No se pudo leer la hoja: {e}")
            return
        self.v_fila.set(detectar_encabezado(filas))
        self._aplicar_encabezado()

    def _aplicar_encabezado(self):
        try:
            fila = int(self.sp_fila.get())
        except (ValueError, tk.TclError):
            fila = 1
        filas = self._filas.get(self.v_hoja.get(), [])
        self.columnas, self.datos = tabla(filas, max(1, fila))
        if not self.columnas or not self.datos:
            self._sin_datos("La hoja no tiene datos bajo la fila de encabezados elegida.")
            return
        self.error.configure(text="")
        self._poblar_columnas()
        self._vista_previa()
        self._actualizar()

    def _sin_datos(self, msg):
        self.columnas, self.datos = [], []
        self.error.configure(text=msg)
        self.lbl_resumen.configure(text="")
        self.lbl_avisos.configure(text="")
        for w in self.marco_prev.winfo_children():
            w.destroy()
        self.b_ok.state(["disabled"])

    def _vista_previa(self):
        for w in self.marco_prev.winfo_children():
            w.destroy()
        cols = [(f"c{j}", c, 120, "w") for j, c in enumerate(self.columnas)]
        tv = tabla_tv(self.marco_prev, cols, alto=6)
        tv.marco.pack(fill="both", expand=True)
        for i, f in enumerate(self.datos[:30]):
            tv.insert("", "end", values=["" if v is None else str(v) for v in f], tags=("par",) if i % 2 else ())

    def _idx(self, nombre):
        return self.columnas.index(nombre) if nombre in self.columnas else None


# ------------------------------------------------------------------- Excel base
class DialogoBase(_DialogoExcel):
    texto_aceptar = "Usar este Excel base"

    def __init__(self, master, ruta: str, quitar_ceros: bool = True):
        self._quitar_ceros = quitar_ceros
        self.base: dict = {}
        super().__init__(master, ruta, "Cargar Excel base",
                         "Elija qué columna es el código y cuál la diferencia (faltantes en negativo: -5 = faltan 5). "
                         "El archivo original no se modifica.", "excel")

    def _construir_columnas(self, m):
        self.v_cod, self.cb_cod = self._combo(m, 0, "Columna de CÓDIGO")
        self.v_dif, self.cb_dif = self._combo(m, 1, "Columna de DIFERENCIA")
        self.v_desc, self.cb_desc = self._combo(m, 2, "Columna de DESCRIPCIÓN (opcional)")
        self.v_ceros = tk.BooleanVar(value=self._quitar_ceros)
        ttk.Checkbutton(m, text="Ignorar ceros a la izquierda en códigos numéricos (00123 = 123)",
                        variable=self.v_ceros, command=self._actualizar).grid(row=2, column=0, columnspan=3,
                                                                              sticky="w", pady=(8, 0))

    def _poblar_columnas(self):
        cols = self.columnas
        self.cb_cod.configure(values=cols)
        self.cb_dif.configure(values=cols)
        self.cb_desc.configure(values=[SIN_DESC] + cols)
        if self.v_cod.get() not in cols:
            self.v_cod.set(cols[adivinar(cols, CLAVES_CODIGO, 0)])
        if self.v_dif.get() not in cols:
            self.v_dif.set(cols[adivinar(cols, CLAVES_DIF, min(1, len(cols) - 1))])
        if self.v_desc.get() not in cols:
            i = adivinar(cols, CLAVES_DESC, None)
            self.v_desc.set(cols[i] if i is not None else SIN_DESC)

    def _actualizar(self):
        ic, idf, ide = self._idx(self.v_cod.get()), self._idx(self.v_dif.get()), self._idx(self.v_desc.get())
        if ic is None or idf is None:
            return
        if ic == idf:
            self.error.configure(text="La columna de código y la de diferencia deben ser distintas.")
            self.b_ok.state(["disabled"])
            return
        self.error.configure(text="")
        self.base, avisos = preparar_base(columna(self.datos, ic), columna(self.datos, idf),
                                          columna(self.datos, ide) if ide is not None else None, self.v_ceros.get())
        falt = [i for i in self.base.values() if i["dif"] < 0]
        unidades = sum(-i["dif"] for i in falt)
        self.lbl_resumen.configure(
            text=f"{fmt_num(len(self.base), 0)} códigos  ·  {fmt_num(len(falt), 0)} con faltante  ·  "
                 f"{fmt_num(unidades, 2)} unidades faltantes",
            foreground=VERDE if self.base else ROJO)
        self.lbl_avisos.configure(text="\n".join("⚠ " + a for a in avisos))
        self.b_ok.state(["!disabled"] if self.base else ["disabled"])

    def aceptar(self):
        if not self.base:
            return
        self.resultado = {
            "base": self.base,
            "info": {"archivo": Path(self.ruta).name, "ruta": str(self.ruta), "hoja": self.v_hoja.get(),
                     "fila_encabezado": int(self.v_fila.get()), "col_codigo": self.v_cod.get(),
                     "col_diferencia": self.v_dif.get(),
                     "col_descripcion": "" if self.v_desc.get() == SIN_DESC else self.v_desc.get(),
                     "quitar_ceros": bool(self.v_ceros.get()),
                     "cargado": dt.datetime.now().isoformat(sep=" ", timespec="seconds")},
        }
        self.destroy()


# ------------------------------------------------------------------- Excel de hallazgos
class DialogoHallazgos(_DialogoExcel):
    texto_aceptar = "Agregar hallazgos"

    def __init__(self, master, ruta: str, base: dict, hallazgos: list[dict], quitar_ceros: bool,
                 origenes: set[str]):
        self.base = base
        self.actuales = hallazgos
        self.quitar_ceros = quitar_ceros
        self.origenes = origenes
        self.nuevos: list[dict] = []
        super().__init__(master, ruta, "Cargar Excel de repuestos encontrados",
                         "Agrega de una vez muchos repuestos encontrados. También sirve para retomar la hoja "
                         "«Hallazgos» de un Excel exportado.", "cargar", alto=800)

    @property
    def origen(self):
        return f"Excel: {Path(self.ruta).name}"

    def _construir_columnas(self, m):
        self.v_cod, self.cb_cod = self._combo(m, 0, "Columna de CÓDIGO")
        self.v_cant, self.cb_cant = self._combo(m, 1, "Columna de CANTIDAD", ancho=36)

    def _extra_ui(self, c):
        _etiqueta(c, "CÓMO QUEDARÍAN ESTOS CÓDIGOS AL AGREGARLOS").pack(fill="x", pady=(10, 2))
        cols = [("cod", "Código", 110, "w"), ("desc", "Descripción", 260, "w"), ("dif", "Dif. original", 90, "e"),
                ("enc", "Encontrado", 90, "e"), ("nueva", "Nueva dif.", 90, "e"),
                ("extra", "EXTRA", 80, "e"), ("est", "Estado", 130, "center")]
        self.tv_cruce = tabla_tv(c, cols, alto=7)
        self.tv_cruce.marco.pack(fill="both", expand=True)

    def _poblar_columnas(self):
        cols = self.columnas
        self.cb_cod.configure(values=cols)
        self.cb_cant.configure(values=[SIN_CANT] + cols)
        if self.v_cod.get() not in cols:
            self.v_cod.set(cols[adivinar(cols, CLAVES_CODIGO, 0)])
        if self.v_cant.get() not in cols:
            i = adivinar(cols, CLAVES_CANT, None)
            self.v_cant.set(cols[i] if i is not None else SIN_CANT)

    def _actualizar(self):
        ic, iq = self._idx(self.v_cod.get()), self._idx(self.v_cant.get())
        if ic is None:
            return
        if ic == iq:
            self.error.configure(text="La columna de código y la de cantidad deben ser distintas.")
            self.b_ok.state(["disabled"])
            return
        self.nuevos, avisos = crear_hallazgos(columna(self.datos, ic),
                                              columna(self.datos, iq) if iq is not None else None, self.quitar_ceros)
        codigos = {h["codigo"] for h in self.nuevos}
        res = [f for f in calcular_resultado(self.base, self.actuales + self.nuevos) if f["codigo"] in codigos]
        ext = extras(res)
        nb = sum(1 for f in res if f["estado"] == ESTADO_NO_BASE)
        texto = (f"{fmt_num(len(self.nuevos), 0)} filas válidas  ·  "
                 f"{fmt_num(sum(h['cantidad'] for h in self.nuevos), 2)} unidades  ·  {len(codigos)} códigos")
        if ext:
            texto += (f"\n→ Quedarían {fmt_num(sum(f['extra'] for f in ext), 2)} unidades EXTRA en {len(ext)} código(s)"
                      + (f" ({nb} no están en el Excel base)" if nb else ""))
        elif self.nuevos:
            texto += "\n→ Sin extras: todo queda dentro de los faltantes originales."
        self.lbl_resumen.configure(text=texto, foreground=ROJO if ext else (VERDE if self.nuevos else ROJO))
        if self.origen in self.origenes:
            avisos.insert(0, f"Ya se agregó un archivo llamado «{Path(self.ruta).name}». "
                             "Agregarlo de nuevo duplicaría las cantidades.")
        self.lbl_avisos.configure(text="\n".join("⚠ " + a for a in avisos))
        self.tv_cruce.delete(*self.tv_cruce.get_children())
        for f in res:
            self.tv_cruce.insert("", "end", values=fila_resultado(f), tags=(f["estado"],))
        self.error.configure(text="" if self.nuevos else "No hay filas válidas para agregar.")
        self.b_ok.state(["!disabled"] if self.nuevos else ["disabled"])

    def aceptar(self):
        if not self.nuevos:
            return
        if self.origen in self.origenes and not messagebox.askyesno(
                TITULO, f"El archivo «{Path(self.ruta).name}» ya fue agregado.\n\n"
                        "¿Agregarlo de nuevo? Las cantidades se sumarán otra vez.", parent=self, icon="warning"):
            return
        self.resultado = {"filas": self.nuevos, "origen": self.origen}
        self.destroy()


def fila_resultado(f: dict) -> list[str]:
    """Valores de una fila de resultado para mostrar en tabla."""
    return [f["codigo"], f["desc"], "—" if f["dif"] is None else fmt_num(f["dif"], 2), fmt_num(f["encontrado"], 2),
            "—" if f["nueva"] is None else fmt_num(f["nueva"], 2), fmt_num(f["extra"], 2) if f["extra"] else "",
            f["estado"]]
