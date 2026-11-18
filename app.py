"""Auditoría de Inventario - control de repuestos encontrados vs. diferencias.

Ejecutar con:  streamlit run app.py
"""

from __future__ import annotations

import io
from datetime import datetime

import pandas as pd
import streamlit as st

import auditoria as au

st.set_page_config(page_title="Auditoría de Inventario", page_icon="📦", layout="wide")

SIN_COLUMNA = "(ninguna)"
SIN_CANTIDAD = "(sin columna: cada fila cuenta 1)"


# ---------------------------------------------------------------- utilidades
@st.cache_data(show_spinner=False)
def leer_hojas(contenido: bytes, nombre: str) -> list[str]:
    if nombre.lower().endswith(".csv"):
        return ["CSV"]
    return pd.ExcelFile(io.BytesIO(contenido)).sheet_names


@st.cache_data(show_spinner=False)
def leer_tabla(contenido: bytes, nombre: str, hoja: str, fila_encabezado: int) -> pd.DataFrame:
    if nombre.lower().endswith(".csv"):
        df = pd.read_csv(io.BytesIO(contenido), header=fila_encabezado - 1, sep=None, engine="python", dtype=str)
    else:
        df = pd.read_excel(io.BytesIO(contenido), sheet_name=hoja, header=fila_encabezado - 1)
    df = df.dropna(how="all")
    df.columns = [str(c).strip() for c in df.columns]
    return df


def adivinar(columnas: list[str], claves: list[str], defecto: int = 0) -> int:
    """Índice de la primera columna cuyo nombre contiene alguna de las claves."""
    for clave in claves:
        for i, col in enumerate(columnas):
            if clave in col.lower():
                return i
    return defecto


def cargar_tabla(prefijo: str, etiqueta: str, contenedor):
    """Widget de carga de archivo + hoja + fila de encabezado. Devuelve (df, nombre) o (None, None)."""
    archivo = contenedor.file_uploader(etiqueta, type=["xlsx", "xlsm", "xls", "csv"], key=f"{prefijo}_archivo")
    if archivo is None:
        return None, None
    contenido = archivo.getvalue()
    try:
        hojas = leer_hojas(contenido, archivo.name)
        c1, c2 = contenedor.columns(2)
        hoja = c1.selectbox("Hoja", hojas, key=f"{prefijo}_hoja")
        fila = c2.number_input("Fila de encabezados", min_value=1, value=1, step=1, key=f"{prefijo}_fila")
        df = leer_tabla(contenido, archivo.name, hoja, int(fila))
    except Exception as e:  # noqa: BLE001 - se muestra al usuario
        contenedor.error(f"No se pudo leer el archivo: {e}")
        return None, None
    if df.empty or len(df.columns) == 0:
        contenedor.warning("La hoja seleccionada no tiene datos.")
        return None, None
    return df, archivo.name


def fmt(n) -> str:
    if n is None or pd.isna(n):
        return "-"
    n = float(n)
    return f"{int(n):,}".replace(",", ".") if n.is_integer() else f"{n:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


# ---------------------------------------------------------------- estado
if "hallazgos" not in st.session_state:
    st.session_state.hallazgos = au.hallazgos_vacios()
if "mensaje_manual" not in st.session_state:
    st.session_state.mensaje_manual = None

# ---------------------------------------------------------------- barra lateral: Excel base
st.sidebar.header("1. Excel base")
df_base_raw, nombre_base = cargar_tabla("base", "Sube el Excel base con las diferencias", st.sidebar)

base = None
if df_base_raw is not None:
    cols = list(df_base_raw.columns)
    col_codigo = st.sidebar.selectbox("Columna de CÓDIGO", cols, index=adivinar(cols, ["código", "codigo", "cod", "sku", "material", "nro", "parte"]))
    col_dif = st.sidebar.selectbox("Columna de DIFERENCIA", cols, index=adivinar(cols, ["diferencia", "dif", "desv"], min(1, len(cols) - 1)))
    opciones_desc = [SIN_COLUMNA] + cols
    col_desc = st.sidebar.selectbox("Columna de DESCRIPCIÓN (opcional)", opciones_desc, index=adivinar(opciones_desc, ["descrip", "detalle", "nombre", "glosa"]))
    st.sidebar.caption("Faltantes en negativo: -5 = faltan 5 unidades.")
    quitar_ceros = st.sidebar.checkbox("Ignorar ceros a la izquierda en códigos numéricos (00123 = 123)", value=True)
    st.session_state.quitar_ceros = quitar_ceros

    base, avisos_base = au.preparar_base(
        df_base_raw, col_codigo, col_dif, None if col_desc == SIN_COLUMNA else col_desc, quitar_ceros
    )
    for a in avisos_base:
        st.sidebar.warning(a)
    falt = base[base[au.COL_DIF] < 0]
    st.sidebar.success(
        f"{len(base)} códigos cargados · {len(falt)} con faltante "
        f"({fmt(-falt[au.COL_DIF].sum())} unidades faltantes)."
    )

quitar_ceros = st.session_state.get("quitar_ceros", True)

st.sidebar.divider()
st.sidebar.header("Hallazgos registrados")
n_hall = len(st.session_state.hallazgos)
st.sidebar.metric("Registros", n_hall, help="Cada ingreso manual o fila de Excel agregada.")
if n_hall and st.sidebar.button("🗑️ Borrar todos los hallazgos", use_container_width=True):
    st.session_state.confirmar_borrado = True
if st.session_state.get("confirmar_borrado"):
    st.sidebar.warning("¿Seguro? Se borrarán todos los hallazgos de esta sesión.")
    b1, b2 = st.sidebar.columns(2)
    if b1.button("Sí, borrar"):
        st.session_state.hallazgos = au.hallazgos_vacios()
        st.session_state.confirmar_borrado = False
        st.session_state.mensaje_manual = None
        st.rerun()
    if b2.button("Cancelar"):
        st.session_state.confirmar_borrado = False
        st.rerun()

# ---------------------------------------------------------------- cuerpo
st.title("📦 Auditoría de Inventario")
st.caption("Registra los repuestos encontrados después del conteo y detecta las unidades EXTRA respecto a la diferencia original.")

if base is None:
    st.info(
        "👈 Empieza subiendo el **Excel base** en la barra lateral y elige qué columna es el código "
        "y cuál la diferencia. El archivo original no se modifica."
    )
    st.stop()

tab_manual, tab_excel, tab_resultado, tab_lista = st.tabs(
    ["✍️ Registrar repuesto", "📄 Cargar Excel de hallazgos", "📊 Resultado y extras", "📋 Hallazgos registrados"]
)

# ---- registro manual
with tab_manual:
    st.subheader("Registrar repuesto encontrado")
    st.caption("Escribe (o escanea) el código y la cantidad encontrada. Si repites un código, las cantidades se suman.")
    with st.form("form_manual", clear_on_submit=True):
        c1, c2, c3 = st.columns([3, 1, 1])
        codigo_in = c1.text_input("Código", placeholder="Ej: 12345")
        cantidad_in = c2.number_input("Cantidad", min_value=1, value=1, step=1)
        c3.write("")
        c3.write("")
        enviado = c3.form_submit_button("➕ Agregar", use_container_width=True, type="primary")

    if enviado:
        codigo = au.normalizar_codigo(codigo_in, quitar_ceros)
        if not codigo:
            st.session_state.mensaje_manual = ("error", "Ingresa un código.")
        else:
            nuevo, _ = au.crear_hallazgos(pd.Series([codigo]), pd.Series([cantidad_in]), "Manual", quitar_ceros)
            st.session_state.hallazgos = pd.concat([st.session_state.hallazgos, nuevo], ignore_index=True)
            r = au.resumen_codigo(base, st.session_state.hallazgos, codigo)
            desc = f" ({r[au.COL_DESC]})" if r[au.COL_DESC] else ""
            if r[au.COL_ESTADO] == au.ESTADO_NO_BASE:
                st.session_state.mensaje_manual = (
                    "warning",
                    f"⚠️ **{codigo}** NO existe en el Excel base. Encontrado acumulado: **{fmt(r[au.COL_ENC])}** "
                    f"→ **{fmt(r[au.COL_EXTRA])} unidad(es) EXTRA** a revisar.",
                )
            elif r[au.COL_EXTRA] > 0:
                st.session_state.mensaje_manual = (
                    "error",
                    f"🚩 **{codigo}**{desc}: diferencia original **{fmt(r[au.COL_DIF])}**, encontrado acumulado "
                    f"**{fmt(r[au.COL_ENC])}** → **{fmt(r[au.COL_EXTRA])} unidad(es) EXTRA**. Revisar discrepancia.",
                )
            else:
                tipo = "success" if r[au.COL_ESTADO] == au.ESTADO_CUADRA else "info"
                st.session_state.mensaje_manual = (
                    tipo,
                    f"✅ **{codigo}**{desc}: diferencia original **{fmt(r[au.COL_DIF])}**, encontrado acumulado "
                    f"**{fmt(r[au.COL_ENC])}**, nueva diferencia **{fmt(r[au.COL_NUEVA])}**. Sin extras.",
                )
        st.rerun()

    if st.session_state.mensaje_manual:
        tipo, texto = st.session_state.mensaje_manual
        getattr(st, tipo)(texto)

    if not st.session_state.hallazgos.empty:
        st.caption("Últimos registros:")
        st.dataframe(st.session_state.hallazgos.tail(5).iloc[::-1], hide_index=True, use_container_width=True)

# ---- carga masiva
with tab_excel:
    st.subheader("Cargar varios repuestos desde un Excel")
    st.caption(
        "Sirve para listas de repuestos encontrados en conjunto, o para retomar una sesión "
        "subiendo la hoja **Hallazgos** de un Excel exportado anteriormente."
    )
    n_carga = st.session_state.get("n_carga", 0)
    df_h_raw, nombre_h = cargar_tabla(f"hall{n_carga}", "Sube el Excel de repuestos encontrados", st)
    if df_h_raw is not None:
        cols_h = list(df_h_raw.columns)
        c1, c2 = st.columns(2)
        col_cod_h = c1.selectbox("Columna de CÓDIGO", cols_h, index=adivinar(cols_h, ["código", "codigo", "cod", "sku", "material"]), key=f"h_cod{n_carga}")
        opciones_cant = [SIN_CANTIDAD] + cols_h
        col_cant_h = c2.selectbox("Columna de CANTIDAD", opciones_cant, index=adivinar(opciones_cant, ["cantidad", "cant", "qty", "unid"]), key=f"h_cant{n_carga}")

        nuevos, avisos_h = au.crear_hallazgos(
            df_h_raw[col_cod_h],
            None if col_cant_h == SIN_CANTIDAD else df_h_raw[col_cant_h],
            f"Excel: {nombre_h}",
            quitar_ceros,
        )
        for a in avisos_h:
            st.warning(a)

        if nuevos.empty:
            st.error("No hay filas válidas para agregar.")
        else:
            # Vista previa de cómo quedaría el cruce SOLO con estos códigos
            combinado = pd.concat([st.session_state.hallazgos, nuevos], ignore_index=True)
            previa = au.calcular_resultado(base, combinado)
            previa = previa[previa[au.COL_CODIGO].isin(nuevos[au.COL_CODIGO])]
            ext = au.extras(previa)

            m1, m2, m3 = st.columns(3)
            m1.metric("Filas válidas", len(nuevos))
            m2.metric("Unidades a agregar", fmt(nuevos[au.COL_CANT].sum()))
            m3.metric("Unidades EXTRA resultantes", fmt(ext[au.COL_EXTRA].sum()), delta=f"{len(ext)} código(s)", delta_color="inverse" if len(ext) else "off")

            with st.expander("Vista previa del cruce de estos códigos", expanded=True):
                st.dataframe(previa, hide_index=True, use_container_width=True)

            ya_cargado = (st.session_state.hallazgos[au.COL_ORIGEN] == f"Excel: {nombre_h}").any()
            permitir = True
            if ya_cargado:
                st.warning(f"Ya agregaste un archivo llamado **{nombre_h}**. Agregarlo de nuevo duplicaría las cantidades.")
                permitir = st.checkbox("Agregarlo de todas formas")
            if st.button(f"➕ Agregar {len(nuevos)} hallazgo(s)", type="primary", disabled=not permitir):
                st.session_state.hallazgos = combinado
                st.session_state.n_carga = n_carga + 1  # limpia el cargador de archivos
                st.session_state.mensaje_excel = f"Se agregaron {len(nuevos)} hallazgo(s) desde **{nombre_h}**. Revisa la pestaña **Resultado y extras**."
                st.rerun()
    if st.session_state.get("mensaje_excel"):
        st.success(st.session_state.pop("mensaje_excel"))

# ---- resultado
resultado = au.calcular_resultado(base, st.session_state.hallazgos)
tabla_extras = au.extras(resultado)

with tab_resultado:
    st.subheader("Resultado del cruce")
    con_hallazgo = resultado[resultado[au.COL_ENC] > 0]
    no_base = resultado[resultado[au.COL_ESTADO] == au.ESTADO_NO_BASE]
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("🚩 Unidades EXTRA", fmt(tabla_extras[au.COL_EXTRA].sum()))
    m2.metric("Códigos con EXTRA", len(tabla_extras))
    m3.metric("Códigos que no están en la base", len(no_base))
    m4.metric("Códigos con hallazgos", len(con_hallazgo))

    if len(tabla_extras):
        st.error(
            f"Se encontraron **{fmt(tabla_extras[au.COL_EXTRA].sum())} unidades extra** en "
            f"**{len(tabla_extras)} código(s)**. Revisa esta discrepancia:"
        )
        st.dataframe(
            tabla_extras.style.format({au.COL_DIF: fmt, au.COL_ENC: fmt, au.COL_NUEVA: fmt, au.COL_EXTRA: fmt}, na_rep="no está en base")
            .map(lambda _: "background-color: #f8cbad; color: #000; font-weight: bold", subset=[au.COL_EXTRA]),
            hide_index=True,
            use_container_width=True,
        )
    elif not con_hallazgo.empty:
        st.success("Sin extras: todo lo encontrado está dentro de los faltantes originales.")

    st.divider()
    filtro = st.radio(
        "Mostrar",
        ["Solo códigos con hallazgos", "Solo extras", "Todos los códigos de la base"],
        horizontal=True,
    )
    vista = {"Solo códigos con hallazgos": con_hallazgo, "Solo extras": tabla_extras}.get(filtro, resultado)
    buscar = st.text_input("Buscar código o descripción", "")
    if buscar:
        b = buscar.strip().upper()
        vista = vista[vista[au.COL_CODIGO].str.contains(b, regex=False) | vista[au.COL_DESC].str.upper().str.contains(b, regex=False)]

    colores = {au.ESTADO_EXTRA: "#f8cbad", au.ESTADO_NO_BASE: "#ffe699", au.ESTADO_CUADRA: "#c6efce"}
    st.dataframe(
        vista.style.format({au.COL_DIF: fmt, au.COL_ENC: fmt, au.COL_NUEVA: fmt, au.COL_EXTRA: fmt}, na_rep="no está en base").apply(
            lambda fila: [f"background-color: {colores[fila[au.COL_ESTADO]]}; color: #000" if fila[au.COL_ESTADO] in colores else ""] * len(fila),
            axis=1,
        ),
        hide_index=True,
        use_container_width=True,
        height=min(600, 38 + 35 * max(len(vista), 1)),
    )

    st.download_button(
        "⬇️ Descargar resultado en Excel",
        data=au.exportar_excel(resultado, st.session_state.hallazgos),
        file_name=f"auditoria_resultado_{datetime.now():%Y%m%d_%H%M}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        type="primary",
    )
    st.caption("El Excel incluye las hojas **Resultado**, **Extras** y **Hallazgos**. La hoja Hallazgos se puede volver a cargar para continuar otro día.")

# ---- lista editable
with tab_lista:
    st.subheader("Hallazgos registrados")
    h = st.session_state.hallazgos
    if h.empty:
        st.info("Aún no hay hallazgos registrados.")
    else:
        st.caption("Selecciona filas (casilla a la izquierda) para eliminarlas si te equivocaste.")
        sel = st.dataframe(
            h, use_container_width=True, on_select="rerun", selection_mode="multi-row", key="tabla_hallazgos"
        )
        filas = sel.selection.rows if sel else []
        if st.button(f"🗑️ Eliminar {len(filas)} fila(s) seleccionada(s)", disabled=not filas):
            st.session_state.hallazgos = h.drop(h.index[filas]).reset_index(drop=True)
            st.session_state.mensaje_manual = None
            st.rerun()
