"""Interfaz gráfica principal (Tkinter), con el mismo diseño que Control de Aceites."""
from __future__ import annotations

import datetime as dt
import os
import subprocess
import sys
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from . import TITULO, __version__, tema
from .calculo import (ESTADO_CUADRA, ESTADO_EXTRA, ESTADO_NO_BASE, ESTADO_PARCIAL, ESTADOS, calcular_resultado,
                      extras, normalizar_codigo, resultado_codigo, resumen)
from .db import NOMBRE_DB, Repositorio, carpeta_datos
from .dialogos import DialogoBase, DialogoHallazgos, elegir_archivo, fila_resultado
from .excel import exportar
from .tema import (ACENTO, AZUL, FONDO, FUENTE, NAVY, NAVY_HOVER, ROJO, SUAVE, TARJETA, TEXTO, TITULO_C, VERDE)
from .util import fmt_fechahora, fmt_num, parse_num
from .widgets import FranjaSeguridad, Indicador, tabla, tarjeta

FILTROS = ("Con hallazgos", "Solo EXTRA", "Todos los códigos")

AYUDA = """\
CÓMO SE USA

1. CARGAR EXCEL BASE
   • Botón «Cargar Excel base»: elija el archivo con las diferencias del inventario (.xlsx, .xlsm o .csv).
   • Indique la hoja, la fila donde están los títulos y qué columna es el CÓDIGO y cuál la DIFERENCIA
     (opcional: la DESCRIPCIÓN). El programa propone las columnas automáticamente.
   • Los faltantes vienen en NEGATIVO: -5 significa que faltan 5 unidades.
   • El Excel original nunca se modifica: el programa guarda una copia de los datos.

2. REGISTRAR REPUESTOS ENCONTRADOS
   • De a uno: escriba (o escanee) el código, la cantidad y presione Enter o «Agregar».
     La cantidad vuelve a 1 después de cada registro. Si repite un código, las cantidades se suman.
   • Muchos a la vez: «Cargar Excel de hallazgos». Elija la columna de código y la de cantidad
     (si no hay columna de cantidad, cada fila cuenta como 1 unidad). Antes de agregar verá cómo quedan.
   • Al registrar, el programa avisa de inmediato si ese código ya tiene unidades EXTRA.

3. RESULTADO Y EXTRAS
   • Faltante          = la diferencia original si es negativa (en positivo).
   • Total encontrado  = suma de todo lo registrado para el código.
   • Nueva diferencia  = diferencia original + total encontrado.
   • EXTRA             = lo encontrado por sobre el faltante. Es la discrepancia que hay que revisar.
     Ejemplo: diferencia -5, se encuentran 3 y luego 4 (7 en total) → nueva diferencia +2 → 2 EXTRA.
   • Estados:
       No está en base   el código no existe en el Excel base: todo lo encontrado es EXTRA.
       EXTRA             se encontró más de lo que faltaba.
       Cuadrado          lo encontrado cubre exactamente el faltante.
       Faltante parcial  todavía faltan unidades.
       Sin hallazgos     no se ha registrado nada para ese código.
   • Doble clic en un código muestra sus registros en «Hallazgos registrados».

4. EXPORTAR
   • «Exportar Excel» genera un archivo con las hojas Resultado, Extras y Hallazgos.

HALLAZGOS REGISTRADOS
   • Lista de todo lo ingresado, con fecha y origen (Manual o el nombre del Excel cargado).
   • Seleccione filas (Ctrl o Shift para varias) y «Eliminar seleccionados» para corregir errores.

NUEVA AUDITORÍA
   • Borra el Excel base y los hallazgos para comenzar otra auditoría. Antes ofrece exportar el resultado.

DATOS
   • Todo se guarda automáticamente: al cerrar y volver a abrir el programa sigue donde quedó.
   • Se guardan en Documentos\\AuditoriaInventario\\AuditoriaInventario_datos.db
     (o junto al .exe si ahí existe ese archivo: modo portátil).
"""


def _abrir(ruta):
    try:
        if sys.platform.startswith("win"):
            os.startfile(ruta)  # noqa: S606
        elif sys.platform == "darwin":
            subprocess.Popen(["open", str(ruta)])
        else:
            subprocess.Popen(["xdg-open", str(ruta)])
    except OSError:
        pass


class App(tk.Tk):
    def __init__(self, ruta_db: str | Path | None = None):
        super().__init__()
        self.withdraw()
        self.title(f"{TITULO} - Repuestos encontrados y extras")
        tema.aplicar(self)
        try:
            self._icono_ventana = tema.icono(self, "logo", 64, "#FFFFFF")
            self.iconphoto(True, self._icono_ventana)
        except tk.TclError:
            pass
        self.ruta_db = Path(ruta_db) if ruta_db else carpeta_datos() / NOMBRE_DB
        self.repo = Repositorio(self.ruta_db)
        self.base, self.info_base = self.repo.base()
        self.hallazgos = self.repo.hallazgos()
        self.resultado: list[dict] = []
        self._ultimo_id: int | None = None

        self.geometry("1320x820")
        self.minsize(1080, 680)
        self._construir()
        self.mostrar("auditoria")
        self.deiconify()
        if sys.platform.startswith("win"):
            try:
                self.state("zoomed")
            except tk.TclError:
                pass
        self.after(150, lambda: self.e_codigo.focus_set())

    @property
    def quitar_ceros(self) -> bool:
        return bool((self.info_base or {}).get("quitar_ceros", True))

    # ---------------------------------------------------------- estructura
    def _construir(self):
        barra = tk.Frame(self, background=NAVY, height=68)
        barra.pack(side="top", fill="x")
        barra.pack_propagate(False)
        logo = tk.Frame(barra, background=NAVY)
        logo.pack(side="left", padx=(18, 26))
        self._img_logo = tema.icono(self, "logo", 42)
        tk.Label(logo, image=self._img_logo, background=NAVY).pack(side="left")
        t = tk.Frame(logo, background=NAVY)
        t.pack(side="left", padx=10)
        tk.Label(t, text="AUDITORÍA DE INVENTARIO", background=NAVY, foreground=TITULO_C,
                 font=(FUENTE, 13, "bold")).pack(anchor="w")
        tk.Label(t, text="Repuestos encontrados · diferencias · extras", background=NAVY, foreground=ACENTO,
                 font=(FUENTE, 8)).pack(anchor="w")
        tk.Frame(barra, background=tema.BORDE, width=1).pack(side="left", fill="y", pady=16)

        pest = tk.Frame(barra, background=NAVY)
        pest.pack(side="left", fill="y", padx=(14, 0))
        self._nav = {}
        for clave, texto, ico in (("auditoria", "Auditoría", "panel"), ("hallazgos", "Hallazgos registrados", "lista"),
                                  ("ayuda", "Ayuda", "ayuda")):
            self._nav[clave] = self._boton_nav(pest, texto, ico, lambda c=clave: self.mostrar(c))

        der = tk.Frame(barra, background=NAVY)
        der.pack(side="right", padx=18)
        self.lbl_estado_lat = tk.Label(der, text="", background=NAVY, foreground=SUAVE, font=(FUENTE, 8),
                                       justify="right", anchor="e")
        self.lbl_estado_lat.pack(anchor="e")
        tk.Label(der, text=f"v{__version__}", background=NAVY, foreground=tema.GRIS,
                 font=(FUENTE, 8, "bold")).pack(anchor="e")
        FranjaSeguridad(self, alto=3).pack(side="top", fill="x")

        self.contenedor = tk.Frame(self, background=FONDO)
        self.contenedor.pack(fill="both", expand=True)
        self.paginas = {
            "auditoria": self._pagina_auditoria(),
            "hallazgos": self._pagina_hallazgos(),
            "ayuda": self._pagina_ayuda(),
        }

    def _boton_nav(self, master, texto, ico, cmd):
        """Pestaña superior: ícono + texto, subrayado ámbar cuando está activa."""
        f = tk.Frame(master, background=NAVY, cursor="hand2")
        f.pack(side="left", fill="y")
        img = tema.icono(self, ico, 16, SUAVE)
        img_a = tema.icono(self, ico, 16, ACENTO)
        cuerpo = tk.Frame(f, background=NAVY)
        cuerpo.pack(fill="both", expand=True, padx=16)
        li = tk.Label(cuerpo, image=img, background=NAVY)
        li.pack(side="left", padx=(0, 7))
        lt = tk.Label(cuerpo, text=texto, background=NAVY, foreground=SUAVE, font=(FUENTE, 10))
        lt.pack(side="left")
        linea = tk.Frame(f, background=NAVY, height=3)
        linea.pack(side="bottom", fill="x")
        widgets = (f, cuerpo, li, lt)

        def fijar(activo):
            for w in widgets:
                w.configure(background=NAVY_HOVER if activo else NAVY)
            linea.configure(background=ACENTO if activo else NAVY)
            li.configure(image=img_a if activo else img)
            lt.configure(foreground=TITULO_C if activo else SUAVE, font=(FUENTE, 10, "bold" if activo else "normal"))
            f.activo = activo

        def hover(on):
            if not getattr(f, "activo", False):
                lt.configure(foreground=TEXTO if on else SUAVE)
                linea.configure(background=tema.GRIS if on else NAVY)

        for w in widgets:
            w.bind("<Button-1>", lambda e: cmd())
            w.bind("<Enter>", lambda e: hover(True))
            w.bind("<Leave>", lambda e: hover(False))
        f.fijar = fijar
        return f

    def mostrar(self, clave):
        for k, p in self.paginas.items():
            p.pack_forget()
            self._nav[k].fijar(k == clave)
        self.paginas[clave].pack(fill="both", expand=True)
        self.refrescar()

    def _titulo_pagina(self, master, titulo, nota):
        cab = tk.Frame(master, background=FONDO)
        cab.pack(fill="x", padx=22, pady=(14, 8))
        tk.Label(cab, text=titulo, background=FONDO, foreground=TITULO_C, font=(FUENTE, 17, "bold")).pack(anchor="w")
        lb = tk.Label(cab, text=nota, background=FONDO, foreground=SUAVE, font=(FUENTE, 9))
        lb.pack(anchor="w")
        return cab, lb

    def _boton_accion(self, master, texto, ico, estilo, cmd, grande=True):
        img = tema.icono(self, ico, 20 if grande else 16, NAVY if estilo == "Naranja" else "#FFFFFF")
        b = ttk.Button(master, text=" " + texto, image=img, compound="left",
                       style=f"{estilo}{'Grande' if grande else ''}.TButton", command=cmd)
        b.image = img
        return b

    # ---------------------------------------------------- página auditoría
    def _pagina_auditoria(self):
        p = tk.Frame(self.contenedor, background=FONDO)
        cab, self.lbl_nota = self._titulo_pagina(p, "Auditoría de repuestos", "")
        sec = tk.Frame(cab, background=FONDO)
        sec.place(relx=1.0, rely=0.5, anchor="e")
        self.b_exportar = self._boton_accion(sec, "Exportar Excel", "exportar", "Verde", self.exportar, grande=False)
        self.b_nueva = self._boton_accion(sec, "Nueva auditoría", "nuevo", "Navy", self.nueva_auditoria, grande=False)
        self.b_exportar.pack(side="left")
        self.b_nueva.pack(side="left", padx=(8, 0))

        fila = tk.Frame(p, background=FONDO)
        fila.pack(fill="x", padx=22, pady=(0, 10))
        fila.columnconfigure(0, weight=2, uniform="f")
        fila.columnconfigure(1, weight=3, uniform="f")

        # -- Excel base
        cb = tarjeta(fila, "1   Excel base", "excel")
        cb.grid(row=0, column=0, sticky="nsew")
        self.lbl_base = tk.Label(cb.inner, text="", background=TARJETA, foreground=TEXTO, font=(FUENTE, 9),
                                 justify="left", anchor="nw")
        self.lbl_base.pack(fill="both", expand=True)
        cb.inner.bind("<Configure>", lambda e: self.lbl_base.configure(wraplength=max(200, e.width - 10)))
        self.b_base = self._boton_accion(cb.inner, "Cargar Excel base", "excel", "Naranja", self.cargar_base)
        self.b_base.pack(fill="x", pady=(8, 0))

        # -- registro
        cr = tarjeta(fila, "2   Registrar repuesto encontrado", "caja")
        cr.grid(row=0, column=1, sticky="nsew", padx=(10, 0))
        f = tk.Frame(cr.inner, background=TARJETA)
        f.pack(fill="x")
        f.columnconfigure(0, weight=1)
        for col, txt in ((0, "CÓDIGO"), (1, "CANTIDAD")):
            tk.Label(f, text=txt, background=TARJETA, foreground=SUAVE, font=(FUENTE, 9, "bold"),
                     anchor="w").grid(row=0, column=col, sticky="w", padx=(0 if col == 0 else 10, 0))
        self.v_codigo = tk.StringVar()
        self.e_codigo = ttk.Entry(f, textvariable=self.v_codigo, font=(FUENTE, 13))
        self.e_codigo.grid(row=1, column=0, sticky="ew")
        self.v_cantidad = tk.StringVar(value="1")
        self.e_cantidad = ttk.Entry(f, textvariable=self.v_cantidad, font=(FUENTE, 13), width=8, justify="center")
        self.e_cantidad.grid(row=1, column=1, sticky="w", padx=(10, 0))
        self.b_agregar = self._boton_accion(f, "Agregar", "agregar", "Naranja", self.agregar_manual)
        self.b_agregar.grid(row=1, column=2, sticky="ns", padx=(10, 0))
        self.b_masivo = self._boton_accion(f, "Cargar Excel de hallazgos", "cargar", "Morado", self.cargar_hallazgos)
        self.b_masivo.grid(row=1, column=3, sticky="ns", padx=(10, 0))
        for e in (self.e_codigo, self.e_cantidad):
            e.bind("<Return>", lambda ev: self.agregar_manual())
            e.bind("<KP_Enter>", lambda ev: self.agregar_manual())
        tk.Label(cr.inner, text="Enter agrega el repuesto (funciona con lector de código de barras). "
                                "La cantidad vuelve a 1 después de cada registro.",
                 background=TARJETA, foreground=SUAVE, font=(FUENTE, 8), anchor="w").pack(fill="x", pady=(4, 0))
        msg = tk.Frame(cr.inner, background=tema.TARJETA2)
        msg.pack(fill="x", pady=(8, 0))
        self.barra_msg = tk.Frame(msg, background=tema.TARJETA2, width=5)
        self.barra_msg.pack(side="left", fill="y")
        self.lbl_msg = tk.Label(msg, text="", background=tema.TARJETA2, foreground=TEXTO, font=(FUENTE, 10),
                                justify="left", anchor="w")
        self.lbl_msg.pack(side="left", fill="x", expand=True, padx=10, pady=8)
        self.b_deshacer = ttk.Button(msg, text="Deshacer", style="Gris.TButton", command=self.deshacer_ultimo)
        cr.inner.bind("<Configure>", lambda e: self.lbl_msg.configure(wraplength=max(200, e.width - 140)))

        # -- indicadores
        ind = tk.Frame(p, background=FONDO)
        ind.pack(fill="x", padx=22, pady=(0, 10))
        self.ind = {}
        for i, (k, tit, ico, col) in enumerate((("extra", "Unidades EXTRA", "extra", ROJO),
                                                ("cextra", "Códigos con EXTRA", "alerta", ACENTO),
                                                ("nobase", "No están en el Excel base", "buscar", tema.AMARILLO),
                                                ("enc", "Unidades encontradas", "caja", AZUL),
                                                ("pend", "Faltante pendiente", "faltante", tema.MORADO))):
            w = Indicador(ind, tit, ico, col)
            w.grid(row=0, column=i, sticky="nsew", padx=(0 if i == 0 else 8, 0))
            ind.columnconfigure(i, weight=1, uniform="ind")
            self.ind[k] = w

        # -- tabla de resultado
        t = tarjeta(p, "Resultado por código", "panel")
        t.pack(fill="both", expand=True, padx=22, pady=(0, 16))
        ctrl = tk.Frame(t.cab, background=TARJETA)
        ctrl.pack(side="right")
        self.v_filtro = tk.StringVar(value=FILTROS[0])
        for fl in FILTROS:
            ttk.Radiobutton(ctrl, text=fl, value=fl, variable=self.v_filtro,
                            command=self.refrescar_tabla).pack(side="left", padx=(0, 12))
        self._img_buscar = tema.icono(self, "buscar", 14, SUAVE)
        tk.Label(ctrl, image=self._img_buscar, background=TARJETA).pack(side="left", padx=(8, 4))
        self.v_buscar = tk.StringVar()
        self.v_buscar.trace_add("write", lambda *a: self.refrescar_tabla())
        ttk.Entry(ctrl, textvariable=self.v_buscar, width=24).pack(side="left")

        cols = [("cod", "Código", 120, "w"), ("desc", "Descripción", 320, "w"),
                ("dif", "Diferencia\noriginal", 100, "e"), ("enc", "Total\nencontrado", 100, "e"),
                ("nueva", "Nueva\ndiferencia", 100, "e"), ("extra", "EXTRA", 90, "e"),
                ("est", "Estado", 140, "center")]
        self.tv = tabla(t.inner, cols, alto=10)
        self.tv.marco.pack(fill="both", expand=True)
        self.tv.tag_configure(ESTADO_EXTRA, foreground="#FFD7D5")
        self.tv.bind("<Double-1>", self._ver_hallazgos_codigo)
        pie = tk.Frame(t.inner, background=TARJETA)
        pie.pack(fill="x", pady=(6, 0))
        for est in (ESTADO_NO_BASE, ESTADO_EXTRA, ESTADO_CUADRA, ESTADO_PARCIAL):
            tk.Label(pie, text="  ", background=tema.FONDO_ESTADO[est], highlightthickness=1,
                     highlightbackground=tema.COLOR_ESTADO[est]).pack(side="left", padx=(0, 4))
            tk.Label(pie, text=est, background=TARJETA, foreground=SUAVE, font=(FUENTE, 8)).pack(side="left",
                                                                                                padx=(0, 14))
        self.lbl_conteo = tk.Label(pie, text="", background=TARJETA, foreground=SUAVE, font=(FUENTE, 8))
        self.lbl_conteo.pack(side="right")
        return p

    # ---------------------------------------------------- página hallazgos
    def _pagina_hallazgos(self):
        p = tk.Frame(self.contenedor, background=FONDO)
        cab, self.lbl_nota_h = self._titulo_pagina(p, "Hallazgos registrados", "")
        sec = tk.Frame(cab, background=FONDO)
        sec.place(relx=1.0, rely=0.5, anchor="e")
        self.b_eliminar = self._boton_accion(sec, "Eliminar seleccionados", "borrar", "Rojo", self.eliminar_sel,
                                             grande=False)
        self.b_eliminar.pack(side="left")
        self._boton_accion(sec, "Borrar todos", "borrar", "Gris", self.borrar_todos, grande=False).pack(
            side="left", padx=(8, 0))

        t = tarjeta(p, "Registros (más recientes primero)", "lista")
        t.pack(fill="both", expand=True, padx=22, pady=(0, 16))
        ctrl = tk.Frame(t.cab, background=TARJETA)
        ctrl.pack(side="right")
        self._img_buscar2 = tema.icono(self, "buscar", 14, SUAVE)
        tk.Label(ctrl, image=self._img_buscar2, background=TARJETA).pack(side="left", padx=(8, 4))
        self.v_buscar_h = tk.StringVar()
        self.v_buscar_h.trace_add("write", lambda *a: self.refrescar_hallazgos())
        ttk.Entry(ctrl, textvariable=self.v_buscar_h, width=24).pack(side="left")
        cols = [("n", "N°", 60, "center"), ("fecha", "Fecha registro", 140, "center"), ("cod", "Código", 130, "w"),
                ("desc", "Descripción", 320, "w"), ("cant", "Cantidad", 90, "e"), ("origen", "Origen", 300, "w")]
        self.tv_h = tabla(t.inner, cols, alto=18)
        self.tv_h.configure(selectmode="extended")
        self.tv_h.marco.pack(fill="both", expand=True)
        self.tv_h.bind("<Delete>", lambda e: self.eliminar_sel())
        self.tv_h.bind("<<TreeviewSelect>>", lambda e: self._estado_eliminar())
        return p

    # ---------------------------------------------------- página ayuda
    def _pagina_ayuda(self):
        p = tk.Frame(self.contenedor, background=FONDO)
        cab, lb = self._titulo_pagina(p, "Ayuda", f"{TITULO} v{__version__}")
        sec = tk.Frame(cab, background=FONDO)
        sec.place(relx=1.0, rely=0.5, anchor="e")
        self._boton_accion(sec, "Abrir carpeta de datos", "lista", "Navy",
                           lambda: _abrir(self.ruta_db.parent), grande=False).pack(side="left")
        self._boton_accion(sec, "Respaldar datos", "exportar", "Gris", self.respaldar, grande=False).pack(
            side="left", padx=(8, 0))
        t = tarjeta(p, "Guía de uso", "ayuda")
        t.pack(fill="both", expand=True, padx=22, pady=(0, 16))
        txt = tk.Text(t.inner, wrap="word", relief="flat", background=TARJETA, foreground=TEXTO,
                      font=(FUENTE, 10), padx=6, pady=6, highlightthickness=0)
        sb = ttk.Scrollbar(t.inner, orient="vertical", command=txt.yview)
        txt.configure(yscrollcommand=sb.set)
        sb.pack(side="right", fill="y")
        txt.pack(fill="both", expand=True)
        txt.insert("1.0", AYUDA + f"\n   • Archivo actual: {self.ruta_db}\n")
        txt.configure(state="disabled")
        return p

    # ---------------------------------------------------------- refresco
    def recalcular(self):
        self.hallazgos = self.repo.hallazgos()
        self.resultado = calcular_resultado(self.base, self.hallazgos)

    def refrescar(self):
        self.recalcular()
        hay_base = bool(self.base)
        r = resumen(self.base, self.resultado)

        if hay_base:
            ib = self.info_base or {}
            self.lbl_nota.configure(text=f"Excel base: {ib.get('archivo', '')}  ·  hoja «{ib.get('hoja', '')}»  ·  "
                                         f"cargado {fmt_fechahora(ib.get('cargado', ''))}")
            self.lbl_base.configure(
                text=f"{ib.get('archivo', '')}\n"
                     f"Columnas: código «{ib.get('col_codigo', '')}» · diferencia «{ib.get('col_diferencia', '')}»\n"
                     f"{fmt_num(r['codigos_base'], 0)} códigos · {fmt_num(r['codigos_faltante'], 0)} con faltante · "
                     f"{fmt_num(r['faltante_inicial'], 2)} unidades faltantes",
                foreground=TEXTO)
            self.b_base.configure(text=" Cambiar Excel base")
        else:
            self.lbl_nota.configure(text="Comience cargando el Excel base con las diferencias del inventario.")
            self.lbl_base.configure(text="Aún no se ha cargado el Excel base.\n"
                                         "Faltantes en negativo: -5 = faltan 5 unidades.", foreground=SUAVE)
            self.b_base.configure(text=" Cargar Excel base")
        estado = ["!disabled"] if hay_base else ["disabled"]
        for w in (self.e_codigo, self.e_cantidad, self.b_agregar, self.b_masivo):
            w.state(estado)
        self.b_exportar.state(["!disabled"] if hay_base or self.hallazgos else ["disabled"])
        if not hay_base and not self.lbl_msg.cget("text"):
            self._mensaje("Cargue el Excel base para comenzar a registrar repuestos.", SUAVE)

        ue = r["unidades_extra"]
        self.ind["extra"].fijar(fmt_num(ue, 2) if hay_base else "—", "unidades a revisar" if ue else "sin extras",
                                ROJO if ue else None)
        self.ind["cextra"].fijar(fmt_num(r["codigos_extra"], 0) if hay_base else "—", "incluye los que no están en base",
                                 ACENTO if r["codigos_extra"] else None)
        self.ind["nobase"].fijar(fmt_num(r["no_en_base"], 0) if hay_base else "—", "códigos encontrados sin registro",
                                 tema.AMARILLO if r["no_en_base"] else None)
        self.ind["enc"].fijar(fmt_num(r["unidades_encontradas"], 2) if hay_base else "—",
                              f"en {fmt_num(r['codigos_con_hallazgos'], 0)} código(s) · {len(self.hallazgos)} registros")
        self.ind["pend"].fijar(fmt_num(r["faltante_pendiente"], 2) if hay_base else "—",
                               f"de {fmt_num(r['faltante_inicial'], 2)} faltantes iniciales")
        self.lbl_estado_lat.configure(text=(f"Base: {(self.info_base or {}).get('archivo', '—')}\n"
                                            f"{len(self.hallazgos)} hallazgos registrados"))
        self.refrescar_tabla()
        self.refrescar_hallazgos()

    def _filtrar(self, filas, texto, claves):
        b = texto.strip().upper()
        if not b:
            return filas
        return [f for f in filas if any(b in str(f.get(k, "")).upper() for k in claves)]

    def refrescar_tabla(self):
        filtro = self.v_filtro.get()
        if filtro == FILTROS[0]:
            filas = [f for f in self.resultado if f["encontrado"] > 0]
        elif filtro == FILTROS[1]:
            filas = extras(self.resultado)
        else:
            filas = self.resultado
        filas = self._filtrar(filas, self.v_buscar.get(), ("codigo", "desc"))
        self.tv.delete(*self.tv.get_children())
        for i, f in enumerate(filas):
            tags = (f["estado"],) if f["estado"] in tema.FONDO_ESTADO else (("par",) if i % 2 else ())
            self.tv.insert("", "end", iid=f"r{i}", values=fila_resultado(f), tags=tags)
        if not filas:
            vacio = ("Cargue el Excel base" if not self.base else
                     "Aún no hay repuestos registrados" if filtro == FILTROS[0] and not self.hallazgos else
                     "Sin resultados para este filtro")
            self.tv.insert("", "end", values=("", vacio, "", "", "", "", ""))
        self.lbl_conteo.configure(text=f"{len(filas)} código(s) mostrados")

    def refrescar_hallazgos(self):
        filas = list(reversed(self.hallazgos))
        for n, h in zip(range(len(filas), 0, -1), filas):
            h["n"] = n
            h["desc"] = self.base.get(h["codigo"], {}).get("desc", "(no está en base)")
        filas = self._filtrar(filas, self.v_buscar_h.get(), ("codigo", "desc", "origen"))
        self.tv_h.delete(*self.tv_h.get_children())
        for i, h in enumerate(filas):
            self.tv_h.insert("", "end", iid=str(h["id"]), tags=("par",) if i % 2 else (),
                             values=(h["n"], fmt_fechahora(h["fecha"]), h["codigo"], h["desc"],
                                     fmt_num(h["cantidad"], 2), h["origen"]))
        total = sum(h["cantidad"] for h in filas)
        self.lbl_nota_h.configure(text=f"{len(filas)} registro(s) · {fmt_num(total, 2)} unidades. "
                                       "Seleccione filas (Ctrl o Shift para varias) para eliminar errores.")
        self._estado_eliminar()

    def _estado_eliminar(self):
        self.b_eliminar.state(["!disabled"] if self.tv_h.selection() else ["disabled"])

    def _mensaje(self, texto, color, deshacer=False):
        self.lbl_msg.configure(text=texto, foreground=TITULO_C if color != SUAVE else SUAVE)
        self.barra_msg.configure(background=color)
        if deshacer:
            self.b_deshacer.pack(side="right", padx=8)
        else:
            self.b_deshacer.pack_forget()

    # ---------------------------------------------------------- acciones
    def cargar_base(self):
        ruta = elegir_archivo(self, "Seleccione el Excel base")
        if not ruta:
            return
        res = DialogoBase(self, ruta, self.quitar_ceros).mostrar()
        if not res:
            return
        if self.base and self.hallazgos:
            if not messagebox.askyesno(TITULO, "Ya hay hallazgos registrados.\n\n¿Reemplazar el Excel base y "
                                               "mantener los hallazgos registrados?\n(Para empezar de cero use "
                                               "«Nueva auditoría»)", parent=self):
                return
        self.base, self.info_base = res["base"], res["info"]
        self.repo.guardar_base(self.base, self.info_base)
        self._mensaje(f"Excel base cargado: {res['info']['archivo']} ({fmt_num(len(self.base), 0)} códigos). "
                      "Ya puede registrar repuestos encontrados.", VERDE)
        self.refrescar()
        self.e_codigo.focus_set()

    def agregar_manual(self):
        if not self.base:
            return
        codigo = normalizar_codigo(self.v_codigo.get(), self.quitar_ceros)
        if not codigo:
            self._mensaje("Ingrese un código.", ROJO)
            self.e_codigo.focus_set()
            return
        cant = parse_num(self.v_cantidad.get())
        if cant is None or cant <= 0:
            self._mensaje("La cantidad debe ser un número mayor que 0.", ROJO)
            self.e_cantidad.focus_set()
            self.e_cantidad.select_range(0, "end")
            return
        if codigo not in self.base and not messagebox.askyesno(
                TITULO, f"El código «{codigo}» NO existe en el Excel base.\n\n"
                        "¿Registrarlo de todas formas? Contará completo como EXTRA.\n"
                        "(Elija «No» si fue un error de digitación)", parent=self, icon="warning"):
            self.e_codigo.focus_set()
            self.e_codigo.select_range(0, "end")
            return
        self._ultimo_id = self.repo.agregar_hallazgo(codigo, cant, "Manual")
        self.v_codigo.set("")
        self.v_cantidad.set("1")
        self.refrescar()
        r = resultado_codigo(self.base, self.hallazgos, codigo)
        desc = f" ({r['desc']})" if r["desc"] else ""
        if r["estado"] == ESTADO_NO_BASE:
            self._mensaje(f"⚠  {codigo} NO está en el Excel base. Encontrado acumulado: {fmt_num(r['encontrado'], 2)} "
                          f"→ {fmt_num(r['extra'], 2)} unidad(es) EXTRA a revisar.", tema.AMARILLO, True)
        elif r["extra"] > 0:
            self._mensaje(f"🚩  {codigo}{desc}: diferencia original {fmt_num(r['dif'], 2)}, encontrado acumulado "
                          f"{fmt_num(r['encontrado'], 2)} → {fmt_num(r['extra'], 2)} unidad(es) EXTRA. "
                          "Revisar discrepancia.", ROJO, True)
        else:
            estado = "cuadrado" if r["estado"] == ESTADO_CUADRA else f"aún faltan {fmt_num(-r['nueva'], 2)}"
            self._mensaje(f"✔  {codigo}{desc}: +{fmt_num(cant, 2)} · diferencia original {fmt_num(r['dif'], 2)}, "
                          f"encontrado acumulado {fmt_num(r['encontrado'], 2)} → nueva diferencia "
                          f"{fmt_num(r['nueva'], 2)} ({estado}). Sin extras.",
                          VERDE if r["estado"] == ESTADO_CUADRA else AZUL, True)
        self.e_codigo.focus_set()

    def deshacer_ultimo(self):
        if self._ultimo_id is None:
            return
        self.repo.eliminar_hallazgos([self._ultimo_id])
        self._ultimo_id = None
        self._mensaje("Último registro deshecho.", SUAVE)
        self.refrescar()
        self.e_codigo.focus_set()

    def cargar_hallazgos(self):
        if not self.base:
            return
        ruta = elegir_archivo(self, "Seleccione el Excel de repuestos encontrados")
        if not ruta:
            return
        res = DialogoHallazgos(self, ruta, self.base, self.hallazgos, self.quitar_ceros, self.repo.origenes()).mostrar()
        if not res:
            return
        n = self.repo.agregar_hallazgos(res["filas"], res["origen"])
        self._ultimo_id = None
        self.refrescar()
        r = resumen(self.base, self.resultado)
        if r["unidades_extra"]:
            self._mensaje(f"Se agregaron {n} hallazgo(s) desde {res['origen'][7:]}. Total actual: "
                          f"{fmt_num(r['unidades_extra'], 2)} unidades EXTRA en {r['codigos_extra']} código(s).", ROJO)
            self.v_filtro.set(FILTROS[1])
            self.refrescar_tabla()
        else:
            self._mensaje(f"Se agregaron {n} hallazgo(s) desde {res['origen'][7:]}. Sin extras.", VERDE)

    def _ver_hallazgos_codigo(self, _=None):
        sel = self.tv.selection()
        if not sel:
            return
        codigo = self.tv.item(sel[0], "values")[0]
        if codigo:
            self.v_buscar_h.set(codigo)
            self.mostrar("hallazgos")

    def eliminar_sel(self):
        ids = self.tv_h.selection()
        if not ids:
            return
        if not messagebox.askyesno(TITULO, f"¿Eliminar {len(ids)} registro(s) seleccionado(s)?", parent=self):
            return
        self.repo.eliminar_hallazgos(ids)
        self._ultimo_id = None
        self.refrescar()

    def borrar_todos(self):
        if not self.hallazgos:
            return
        if not messagebox.askyesno(TITULO, f"¿Borrar los {len(self.hallazgos)} hallazgos registrados?\n\n"
                                           "El Excel base se mantiene.", parent=self, icon="warning"):
            return
        self.repo.borrar_hallazgos()
        self._ultimo_id = None
        self._mensaje("Se borraron todos los hallazgos.", SUAVE)
        self.refrescar()

    def exportar(self) -> bool:
        carpeta = self.ruta_db.parent / "Reportes"
        try:
            carpeta.mkdir(parents=True, exist_ok=True)
        except OSError:
            carpeta = self.ruta_db.parent
        ruta = filedialog.asksaveasfilename(
            parent=self, title="Exportar resultado", initialdir=str(carpeta), defaultextension=".xlsx",
            initialfile=f"Auditoria_resultado_{dt.datetime.now():%Y%m%d_%H%M}.xlsx",
            filetypes=(("Excel", "*.xlsx"),))
        if not ruta:
            return False
        self.recalcular()
        try:
            exportar(ruta, self.resultado, self.hallazgos, self.info_base)
        except PermissionError:
            messagebox.showerror(TITULO, "No se pudo guardar: el archivo está abierto en Excel. Ciérrelo e intente "
                                         "de nuevo.", parent=self)
            return False
        except OSError as e:
            messagebox.showerror(TITULO, f"No se pudo guardar el archivo:\n{e}", parent=self)
            return False
        if messagebox.askyesno(TITULO, f"Excel exportado:\n{ruta}\n\n¿Desea abrirlo?", parent=self):
            _abrir(ruta)
        return True

    def nueva_auditoria(self):
        if not self.base and not self.hallazgos:
            return
        resp = messagebox.askyesnocancel(
            TITULO, "Nueva auditoría: se borrarán el Excel base cargado y todos los hallazgos.\n\n"
                    "¿Desea exportar el resultado actual antes de continuar?", parent=self, icon="warning")
        if resp is None:
            return
        if resp and not self.exportar():
            return
        if not messagebox.askyesno(TITULO, "¿Confirma comenzar una nueva auditoría?", parent=self):
            return
        self.repo.nueva_auditoria()
        self.base, self.info_base = {}, None
        self._ultimo_id = None
        self.v_buscar.set("")
        self.v_buscar_h.set("")
        self.v_filtro.set(FILTROS[0])
        self._mensaje("", SUAVE)
        self.refrescar()

    def respaldar(self):
        ruta = filedialog.asksaveasfilename(
            parent=self, title="Respaldar datos", defaultextension=".db",
            initialfile=f"AuditoriaInventario_respaldo_{dt.datetime.now():%Y%m%d_%H%M}.db",
            filetypes=(("Base de datos", "*.db"),))
        if ruta:
            self.repo.respaldar(ruta)
            messagebox.showinfo(TITULO, f"Respaldo guardado en:\n{ruta}", parent=self)


def main():
    if sys.platform.startswith("win"):
        try:
            import ctypes
            ctypes.windll.shcore.SetProcessDpiAwareness(1)
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("AuditoriaInventario")
        except (AttributeError, OSError):
            pass
    app = App()
    app.mainloop()


__all__ = ["App", "main", "ESTADOS"]
