"""Lectura de Excel/CSV (solo lectura: el archivo original nunca se modifica) y exportación del resultado."""
from __future__ import annotations

import csv
from pathlib import Path

from openpyxl import Workbook, load_workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter

from .calculo import ESTADO_CUADRA, ESTADO_EXTRA, ESTADO_NO_BASE, ESTADO_PARCIAL, extras

EXTENSIONES = (("Excel", "*.xlsx *.xlsm"), ("CSV", "*.csv"), ("Todos los archivos", "*.*"))
CLAVES_CODIGO = ("código", "codigo", "cód", "cod", "sku", "material", "n° parte", "nro parte", "parte", "item")
CLAVES_DIF = ("diferencia", "dif", "desv", "ajuste")
CLAVES_DESC = ("descrip", "detalle", "nombre", "glosa", "texto")
CLAVES_CANT = ("cantidad", "cant", "qty", "unid", "encontrad")


class ErrorArchivo(Exception):
    pass


def _es_csv(ruta) -> bool:
    return str(ruta).lower().endswith(".csv")


def _filas_csv(ruta) -> list[list]:
    datos = None
    for cod in ("utf-8-sig", "cp1252", "latin-1"):
        try:
            datos = Path(ruta).read_text(encoding=cod)
            break
        except UnicodeDecodeError:
            continue
    try:
        dialecto = csv.Sniffer().sniff(datos[:4096], delimiters=";,\t|")
    except csv.Error:
        class dialecto(csv.excel):
            delimiter = ";" if datos.count(";") > datos.count(",") else ","
    return [fila for fila in csv.reader(datos.splitlines(), dialecto)]


def hojas(ruta) -> list[str]:
    if _es_csv(ruta):
        return ["CSV"]
    if str(ruta).lower().endswith(".xls"):
        raise ErrorArchivo("El formato .xls antiguo no es compatible. Ábralo en Excel y guárdelo como .xlsx.")
    try:
        wb = load_workbook(ruta, read_only=True, data_only=True)
    except Exception as e:  # noqa: BLE001
        raise ErrorArchivo(f"No se pudo abrir el archivo: {e}") from e
    try:
        return list(wb.sheetnames)
    finally:
        wb.close()


def filas_crudas(ruta, hoja: str, max_filas: int | None = None) -> list[list]:
    """Todas las filas de la hoja como listas de valores (sin filas totalmente vacías al final)."""
    if _es_csv(ruta):
        filas = _filas_csv(ruta)
    else:
        try:
            wb = load_workbook(ruta, read_only=True, data_only=True)
        except Exception as e:  # noqa: BLE001
            raise ErrorArchivo(f"No se pudo abrir el archivo: {e}") from e
        try:
            ws = wb[hoja]
            filas = []
            for i, fila in enumerate(ws.iter_rows(values_only=True)):
                if max_filas and i >= max_filas:
                    break
                filas.append(list(fila))
        finally:
            wb.close()
    while filas and all(v in (None, "") for v in filas[-1]):
        filas.pop()
    return filas


def detectar_encabezado(filas: list[list], limite: int = 20) -> int:
    """Fila (1 = primera) que parece encabezado: la primera que menciona un código, si no la primera con datos."""
    for i, fila in enumerate(filas[:limite]):
        textos = [str(v).strip().lower() for v in fila if isinstance(v, str)]
        if any(any(c in t for c in CLAVES_CODIGO) for t in textos) and len(textos) >= 2:
            return i + 1
    for i, fila in enumerate(filas[:limite]):
        if sum(1 for v in fila if v not in (None, "")) >= 2:
            return i + 1
    return 1


def tabla(filas: list[list], fila_encabezado: int) -> tuple[list[str], list[list]]:
    """Separa encabezados y datos. Las columnas sin título se llaman «Columna X»."""
    if not filas or fila_encabezado > len(filas):
        return [], []
    cab = filas[fila_encabezado - 1]
    datos = [f for f in filas[fila_encabezado:] if any(v not in (None, "") for v in f)]
    ancho = max([len(cab)] + [len(f) for f in datos]) if datos else len(cab)
    columnas, vistos = [], {}
    for j in range(ancho):
        v = cab[j] if j < len(cab) else None
        nombre = str(v).strip() if v not in (None, "") else f"Columna {get_column_letter(j + 1)}"
        if nombre in vistos:
            vistos[nombre] += 1
            nombre = f"{nombre} ({vistos[nombre]})"
        else:
            vistos[nombre] = 1
        columnas.append(nombre)
    datos = [list(f) + [None] * (ancho - len(f)) for f in datos]
    # quitar columnas completamente vacías y sin título
    utiles = [j for j, c in enumerate(columnas) if not c.startswith("Columna ") or any(f[j] not in (None, "") for f in datos)]
    return [columnas[j] for j in utiles], [[f[j] for j in utiles] for f in datos]


def columna(datos: list[list], indice: int) -> list:
    return [f[indice] for f in datos]


def adivinar(columnas: list[str], claves, defecto: int | None = 0) -> int | None:
    for clave in claves:
        for i, c in enumerate(columnas):
            if clave in c.lower():
                return i
    return defecto


# ------------------------------------------------------------------ exportación
_ROJO = PatternFill("solid", fgColor="F8CBAD")
_AMARILLO = PatternFill("solid", fgColor="FFE699")
_VERDE = PatternFill("solid", fgColor="C6EFCE")
_AZUL = PatternFill("solid", fgColor="DDEBF7")
_CAB = PatternFill("solid", fgColor="23272E")
_BORDE = Border(*(Side(style="thin", color="BFBFBF"),) * 4)
_COLOR = {ESTADO_EXTRA: _ROJO, ESTADO_NO_BASE: _AMARILLO, ESTADO_CUADRA: _VERDE, ESTADO_PARCIAL: _AZUL}


def _hoja(wb, titulo, columnas, filas, col_estado=None, anchos=None):
    ws = wb.create_sheet(titulo)
    ws.append(columnas)
    for c in ws[1]:
        c.font = Font(bold=True, color="F2A62B")
        c.fill = _CAB
        c.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
    for f in filas:
        ws.append(f)
    for fila in ws.iter_rows(min_row=2):
        color = _COLOR.get(fila[col_estado].value) if col_estado is not None else None
        for c in fila:
            c.border = _BORDE
            if color:
                c.fill = color
            if isinstance(c.value, float):
                c.number_format = "#,##0.##"
    for i, ancho in enumerate(anchos or [], start=1):
        ws.column_dimensions[get_column_letter(i)].width = ancho
    ws.freeze_panes = "A2"
    if filas:
        ws.auto_filter.ref = ws.dimensions
    return ws


def _num(v):
    if v is None:
        return None
    return int(v) if float(v).is_integer() else round(float(v), 4)


COLUMNAS_RESULTADO = ["Código", "Descripción", "Diferencia original", "Total encontrado", "Nueva diferencia",
                      "EXTRA", "Estado"]


def exportar(ruta, resultado: list[dict], hallazgos: list[dict], info_base: dict | None = None):
    """Excel con hojas Resultado, Extras y Hallazgos."""
    wb = Workbook()
    wb.remove(wb.active)
    anchos = [16, 40, 12, 12, 12, 10, 18]

    def filas(lista):
        return [[f["codigo"], f["desc"], _num(f["dif"]), _num(f["encontrado"]), _num(f["nueva"]),
                 _num(f["extra"]), f["estado"]] for f in lista]

    _hoja(wb, "Resultado", COLUMNAS_RESULTADO, filas(resultado), 6, anchos)
    ws = _hoja(wb, "Extras", COLUMNAS_RESULTADO, filas(extras(resultado)), 6, anchos)
    total = sum(f["extra"] for f in extras(resultado))
    ws.append([])
    ws.append(["TOTAL EXTRA", None, None, None, None, _num(total)])
    for c in ws[ws.max_row]:
        c.font = Font(bold=True)
    _hoja(wb, "Hallazgos", ["Código", "Cantidad", "Origen", "Fecha registro"],
          [[h["codigo"], _num(h["cantidad"]), h.get("origen", ""), h.get("fecha", "")] for h in hallazgos],
          None, [16, 10, 40, 20])
    if info_base:
        wb["Resultado"].oddFooter.left.text = f"Excel base: {info_base.get('archivo', '')}"
    wb.save(ruta)
