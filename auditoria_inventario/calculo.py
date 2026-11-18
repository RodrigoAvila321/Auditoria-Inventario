"""Cruce entre el Excel base de diferencias y los repuestos encontrados después.

Convención: en el Excel base la diferencia es NEGATIVA cuando falta stock (-5 = faltan 5 unidades).
El Excel base nunca se modifica.

    faltante          = -diferencia original si es negativa; si no, 0
    total encontrado  = suma de todos los hallazgos del código
    nueva diferencia  = diferencia original + total encontrado
    EXTRA             = total encontrado - faltante (mínimo 0)
"""
from __future__ import annotations

from .util import parse_num

ESTADO_SIN = "Sin hallazgos"
ESTADO_PARCIAL = "Faltante parcial"
ESTADO_CUADRA = "Cuadrado"
ESTADO_EXTRA = "EXTRA"
ESTADO_NO_BASE = "No está en base"

ESTADOS = (ESTADO_NO_BASE, ESTADO_EXTRA, ESTADO_CUADRA, ESTADO_PARCIAL, ESTADO_SIN)
_ORDEN = {e: i for i, e in enumerate(ESTADOS)}

EPS = 1e-9


def normalizar_codigo(valor, quitar_ceros: bool = True) -> str:
    """Código comparable: sin espacios, en mayúsculas, sin el «.0» que agrega Excel y (opcional)
    sin ceros a la izquierda en códigos solo numéricos (00123 = 123)."""
    if valor is None:
        return ""
    if isinstance(valor, float):
        if valor != valor:  # NaN
            return ""
        if valor.is_integer():
            valor = int(valor)
    texto = str(valor).strip().upper()
    if texto.endswith(".0") and texto[:-2].isdigit():
        texto = texto[:-2]
    if quitar_ceros and texto.isdigit():
        texto = texto.lstrip("0") or "0"
    return texto


def a_numero(valor) -> float | None:
    """Número desde Excel o texto («-5», «1,5», «1.234»). None si está vacío o no es número."""
    if valor is None or isinstance(valor, bool):
        return None
    if isinstance(valor, (int, float)):
        return None if valor != valor else float(valor)
    if str(valor).strip() == "":
        return None
    return parse_num(valor)


def preparar_base(codigos, diferencias, descripciones=None, quitar_ceros: bool = True):
    """Devuelve ({código: {"desc", "dif"}}, avisos). Los códigos repetidos se suman."""
    avisos: list[str] = []
    base: dict[str, dict] = {}
    sin_codigo = invalidas = 0
    repetidos: set[str] = set()
    descripciones = descripciones if descripciones is not None else [None] * len(codigos)
    for cod, dif, desc in zip(codigos, diferencias, descripciones):
        c = normalizar_codigo(cod, quitar_ceros)
        if not c:
            sin_codigo += 1 if (dif is not None or desc not in (None, "")) else 0
            continue
        d = a_numero(dif)
        if d is None:
            invalidas += 1
            d = 0.0
        texto = "" if desc is None else str(desc).strip()
        if c in base:
            repetidos.add(c)
            base[c]["dif"] += d
            if not base[c]["desc"]:
                base[c]["desc"] = texto
        else:
            base[c] = {"desc": texto, "dif": d}
    if sin_codigo:
        avisos.append(f"{sin_codigo} fila(s) sin código fueron ignoradas.")
    if invalidas:
        avisos.append(f"{invalidas} fila(s) con diferencia vacía o no numérica se tomaron como 0.")
    if repetidos:
        lista = sorted(repetidos)
        muestra = ", ".join(lista[:10]) + (" …" if len(lista) > 10 else "")
        avisos.append(f"{len(lista)} código(s) repetidos en el Excel base; se sumaron sus diferencias: {muestra}")
    return base, avisos


def crear_hallazgos(codigos, cantidades=None, quitar_ceros: bool = True):
    """Devuelve ([{"codigo", "cantidad"}], avisos). Sin columna de cantidad, cada fila cuenta 1."""
    avisos: list[str] = []
    filas: list[dict] = []
    malas = 0
    cantidades = cantidades if cantidades is not None else [1] * len(codigos)
    for cod, cant in zip(codigos, cantidades):
        c = normalizar_codigo(cod, quitar_ceros)
        if not c:
            continue
        q = a_numero(cant)
        if q is None or q <= 0:
            malas += 1
            continue
        filas.append({"codigo": c, "cantidad": q})
    if malas:
        avisos.append(f"{malas} fila(s) con cantidad vacía, no numérica o menor o igual a 0 fueron descartadas.")
    return filas, avisos


def totales_encontrados(hallazgos) -> dict[str, float]:
    tot: dict[str, float] = {}
    for h in hallazgos:
        tot[h["codigo"]] = tot.get(h["codigo"], 0.0) + float(h["cantidad"])
    return tot


def _fila(codigo: str, info: dict | None, encontrado: float) -> dict:
    if info is None:
        return {"codigo": codigo, "desc": "", "dif": None, "encontrado": encontrado, "nueva": None,
                "extra": encontrado, "estado": ESTADO_NO_BASE}
    dif = info["dif"]
    faltante = max(-dif, 0.0)
    extra = max(encontrado - faltante, 0.0)
    nueva = dif + encontrado
    if encontrado <= EPS:
        estado = ESTADO_SIN
    elif extra > EPS:
        estado = ESTADO_EXTRA
    elif abs(nueva) <= EPS:
        estado = ESTADO_CUADRA
    else:
        estado = ESTADO_PARCIAL
    return {"codigo": codigo, "desc": info["desc"], "dif": dif, "encontrado": encontrado, "nueva": nueva,
            "extra": extra, "estado": estado}


def calcular_resultado(base: dict, hallazgos) -> list[dict]:
    """Una fila por código (base + códigos encontrados que no están en la base), ordenadas:
    no está en base, EXTRA (mayor primero), cuadrado, parcial, sin hallazgos."""
    enc = totales_encontrados(hallazgos)
    filas = [_fila(c, info, enc.get(c, 0.0)) for c, info in base.items()]
    filas += [_fila(c, None, q) for c, q in enc.items() if c not in base]
    filas.sort(key=lambda f: (_ORDEN[f["estado"]], -f["extra"], f["codigo"]))
    return filas


def resultado_codigo(base: dict, hallazgos, codigo: str) -> dict:
    enc = sum(float(h["cantidad"]) for h in hallazgos if h["codigo"] == codigo)
    return _fila(codigo, base.get(codigo), enc)


def extras(resultado) -> list[dict]:
    return [f for f in resultado if f["extra"] > EPS]


def resumen(base: dict, resultado) -> dict:
    ext = extras(resultado)
    con = [f for f in resultado if f["encontrado"] > EPS]
    faltante_ini = sum(max(-i["dif"], 0.0) for i in base.values())
    faltante_pend = sum(max(-(f["nueva"] or 0.0), 0.0) for f in resultado if f["dif"] is not None)
    return {
        "codigos_base": len(base),
        "codigos_faltante": sum(1 for i in base.values() if i["dif"] < -EPS),
        "faltante_inicial": faltante_ini,
        "faltante_pendiente": faltante_pend,
        "unidades_extra": sum(f["extra"] for f in ext),
        "codigos_extra": len(ext),
        "no_en_base": sum(1 for f in resultado if f["estado"] == ESTADO_NO_BASE),
        "codigos_con_hallazgos": len(con),
        "unidades_encontradas": sum(f["encontrado"] for f in con),
    }
