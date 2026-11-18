"""Lógica de cruce entre el Excel base de diferencias y los repuestos encontrados.

Convención: en el Excel base la diferencia es NEGATIVA cuando falta stock
(ej. -5 = faltan 5 unidades). El Excel base nunca se modifica.
"""

from __future__ import annotations

import io
from datetime import datetime

import pandas as pd

COL_CODIGO = "Código"
COL_DESC = "Descripción"
COL_DIF = "Diferencia original"
COL_ENC = "Total encontrado"
COL_NUEVA = "Nueva diferencia"
COL_EXTRA = "EXTRA"
COL_ESTADO = "Estado"
COL_CANT = "Cantidad"
COL_ORIGEN = "Origen"
COL_FECHA = "Fecha registro"

ESTADO_SIN = "Sin hallazgos"
ESTADO_PARCIAL = "Faltante cubierto parcialmente"
ESTADO_CUADRA = "Cuadrado"
ESTADO_EXTRA = "EXTRA - revisar"
ESTADO_NO_BASE = "No existe en base - revisar"

COLUMNAS_HALLAZGOS = [COL_CODIGO, COL_CANT, COL_ORIGEN, COL_FECHA]


def normalizar_codigo(valor, quitar_ceros: bool = True) -> str:
    """Convierte un código a texto comparable: sin espacios, mayúsculas,
    sin '.0' de Excel y (opcional) sin ceros a la izquierda en códigos numéricos."""
    if valor is None or (isinstance(valor, float) and pd.isna(valor)):
        return ""
    if isinstance(valor, float) and valor.is_integer():
        valor = int(valor)
    texto = str(valor).strip().upper()
    if texto.endswith(".0") and texto[:-2].isdigit():
        texto = texto[:-2]
    if quitar_ceros and texto.isdigit():
        texto = texto.lstrip("0") or "0"
    return texto


def a_numero(serie: pd.Series) -> pd.Series:
    """Convierte a número aceptando coma decimal ('1,5'). Lo inválido queda NaN."""
    if pd.api.types.is_numeric_dtype(serie):
        return serie.astype(float)
    texto = serie.astype(str).str.strip().str.replace(" ", "", regex=False)
    con_coma = texto.str.contains(",", regex=False) & ~texto.str.contains(".", regex=False)
    texto = texto.where(~con_coma, texto.str.replace(",", ".", regex=False))
    return pd.to_numeric(texto, errors="coerce")


def preparar_base(
    df: pd.DataFrame,
    col_codigo: str,
    col_diferencia: str,
    col_descripcion: str | None = None,
    quitar_ceros: bool = True,
) -> tuple[pd.DataFrame, list[str]]:
    """Devuelve la base normalizada (una fila por código) y una lista de avisos."""
    avisos: list[str] = []
    base = pd.DataFrame()
    base[COL_CODIGO] = df[col_codigo].map(lambda v: normalizar_codigo(v, quitar_ceros))
    base[COL_DESC] = df[col_descripcion].astype(str).str.strip() if col_descripcion else ""
    base[COL_DIF] = a_numero(df[col_diferencia])

    vacios = base[COL_CODIGO] == ""
    if vacios.any():
        avisos.append(f"{int(vacios.sum())} fila(s) del Excel base sin código fueron ignoradas.")
    base = base[~vacios]

    invalidas = base[COL_DIF].isna()
    if invalidas.any():
        avisos.append(
            f"{int(invalidas.sum())} fila(s) con diferencia vacía o no numérica se tomaron como 0."
        )
    base[COL_DIF] = base[COL_DIF].fillna(0)

    duplicados = base[COL_CODIGO].duplicated(keep=False)
    if duplicados.any():
        codigos = sorted(base.loc[duplicados, COL_CODIGO].unique())
        muestra = ", ".join(codigos[:10]) + (" ..." if len(codigos) > 10 else "")
        avisos.append(
            f"{len(codigos)} código(s) aparecen repetidos en el Excel base; "
            f"sus diferencias se sumaron: {muestra}"
        )
    base = (
        base.groupby(COL_CODIGO, as_index=False, sort=False)
        .agg({COL_DESC: "first", COL_DIF: "sum"})
    )
    return base, avisos


def hallazgos_vacios() -> pd.DataFrame:
    return pd.DataFrame(columns=COLUMNAS_HALLAZGOS)


def crear_hallazgos(
    codigos: pd.Series,
    cantidades: pd.Series | None,
    origen: str,
    quitar_ceros: bool = True,
) -> tuple[pd.DataFrame, list[str]]:
    """Arma filas de hallazgos. Si no hay columna de cantidad, cada fila cuenta 1."""
    avisos: list[str] = []
    nuevo = pd.DataFrame()
    nuevo[COL_CODIGO] = codigos.map(lambda v: normalizar_codigo(v, quitar_ceros)).values
    if cantidades is None:
        nuevo[COL_CANT] = 1.0
    else:
        nuevo[COL_CANT] = a_numero(cantidades).values

    sin_codigo = nuevo[COL_CODIGO] == ""
    sin_cant = nuevo[COL_CANT].isna() | (nuevo[COL_CANT] <= 0)
    descartar = sin_codigo | sin_cant
    if (sin_cant & ~sin_codigo).any():
        avisos.append(
            f"{int((sin_cant & ~sin_codigo).sum())} fila(s) con cantidad vacía, "
            "no numérica o menor/igual a 0 fueron descartadas."
        )
    if sin_codigo.any():
        avisos.append(f"{int(sin_codigo.sum())} fila(s) sin código fueron descartadas.")
    nuevo = nuevo[~descartar].copy()
    nuevo[COL_ORIGEN] = origen
    nuevo[COL_FECHA] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    return nuevo[COLUMNAS_HALLAZGOS].reset_index(drop=True), avisos


def _estado(fila) -> str:
    if not fila["_en_base"]:
        return ESTADO_NO_BASE
    if fila[COL_ENC] == 0:
        return ESTADO_SIN
    if fila[COL_EXTRA] > 0:
        return ESTADO_EXTRA
    if fila[COL_NUEVA] == 0:
        return ESTADO_CUADRA
    return ESTADO_PARCIAL


def calcular_resultado(base: pd.DataFrame, hallazgos: pd.DataFrame) -> pd.DataFrame:
    """Cruza la base con los hallazgos.

    faltante = unidades que faltaban (-diferencia si es negativa, si no 0)
    EXTRA    = lo encontrado por sobre el faltante
    """
    if hallazgos.empty:
        encontrados = pd.DataFrame(columns=[COL_CODIGO, COL_ENC])
    else:
        h = hallazgos[[COL_CODIGO, COL_CANT]].copy()
        h[COL_CANT] = pd.to_numeric(h[COL_CANT], errors="coerce").fillna(0)
        encontrados = h.groupby(COL_CODIGO, as_index=False)[COL_CANT].sum()
        encontrados = encontrados.rename(columns={COL_CANT: COL_ENC})

    base = base.assign(_en_base=True)
    res = base.merge(encontrados, on=COL_CODIGO, how="outer")
    res["_en_base"] = res["_en_base"].fillna(False).astype(bool)
    res[COL_ENC] = pd.to_numeric(res[COL_ENC], errors="coerce").fillna(0.0)
    res[COL_DESC] = res[COL_DESC].fillna("")

    dif = pd.to_numeric(res[COL_DIF], errors="coerce").fillna(0.0)
    faltante = (-dif).clip(lower=0)
    res[COL_EXTRA] = (res[COL_ENC] - faltante).clip(lower=0)
    res[COL_NUEVA] = (dif + res[COL_ENC]).where(res["_en_base"])
    res[COL_DIF] = res[COL_DIF].where(res["_en_base"])
    res[COL_ESTADO] = res.apply(_estado, axis=1)

    orden = {ESTADO_NO_BASE: 0, ESTADO_EXTRA: 1, ESTADO_CUADRA: 2, ESTADO_PARCIAL: 3, ESTADO_SIN: 4}
    res["_orden"] = res[COL_ESTADO].map(orden)
    res = res.sort_values(["_orden", COL_EXTRA, COL_CODIGO], ascending=[True, False, True])
    columnas = [COL_CODIGO, COL_DESC, COL_DIF, COL_ENC, COL_NUEVA, COL_EXTRA, COL_ESTADO]
    return res[columnas].reset_index(drop=True)


def extras(resultado: pd.DataFrame) -> pd.DataFrame:
    return resultado[resultado[COL_EXTRA] > 0].reset_index(drop=True)


def resumen_codigo(base: pd.DataFrame, hallazgos: pd.DataFrame, codigo: str) -> dict:
    """Situación actual de un código, para avisar al momento de registrarlo."""
    res = calcular_resultado(base[base[COL_CODIGO] == codigo], hallazgos[hallazgos[COL_CODIGO] == codigo])
    fila = res.iloc[0]
    return {k: fila[k] for k in res.columns}


def exportar_excel(resultado: pd.DataFrame, hallazgos: pd.DataFrame) -> bytes:
    """Genera el Excel de salida con hojas Resultado, Extras y Hallazgos."""
    from openpyxl.styles import Font, PatternFill
    from openpyxl.utils import get_column_letter

    rojo = PatternFill("solid", fgColor="F8CBAD")
    amarillo = PatternFill("solid", fgColor="FFE699")
    verde = PatternFill("solid", fgColor="C6EFCE")
    negrita = Font(bold=True)

    buffer = io.BytesIO()
    hojas = {
        "Resultado": resultado,
        "Extras": extras(resultado),
        "Hallazgos": hallazgos[COLUMNAS_HALLAZGOS],
    }
    with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
        for nombre, df in hojas.items():
            df.to_excel(writer, sheet_name=nombre, index=False)
            ws = writer.sheets[nombre]
            ws.freeze_panes = "A2"
            for celda in ws[1]:
                celda.font = negrita
            for i, col in enumerate(df.columns, start=1):
                largo = max([len(str(col))] + [len(str(v)) for v in df[col].head(500)])
                ws.column_dimensions[get_column_letter(i)].width = min(max(largo + 2, 10), 50)
            if COL_ESTADO in df.columns:
                idx_estado = list(df.columns).index(COL_ESTADO)
                for fila in ws.iter_rows(min_row=2):
                    estado = fila[idx_estado].value
                    color = {
                        ESTADO_EXTRA: rojo,
                        ESTADO_NO_BASE: amarillo,
                        ESTADO_CUADRA: verde,
                    }.get(estado)
                    if color:
                        for celda in fila:
                            celda.fill = color
    return buffer.getvalue()
