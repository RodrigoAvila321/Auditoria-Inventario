import pandas as pd

import auditoria as au


def _base():
    df = pd.DataFrame({
        "Cod": ["00123", "456", "789", "1001"],
        "Desc": ["Filtro", "Correa", "Rodamiento", "Perno"],
        "Dif": [-5, 0, -3, 2],
    })
    base, avisos = au.preparar_base(df, "Cod", "Dif", "Desc")
    assert avisos == []
    return base


def _hall(pares):
    codigos = pd.Series([c for c, _ in pares])
    cant = pd.Series([q for _, q in pares])
    h, _ = au.crear_hallazgos(codigos, cant, "test")
    return h


def _fila(res, codigo):
    return res[res[au.COL_CODIGO] == codigo].iloc[0]


def test_normalizar_codigo():
    assert au.normalizar_codigo(" 00123 ") == "123"
    assert au.normalizar_codigo(123.0) == "123"
    assert au.normalizar_codigo("ab-12 ") == "AB-12"
    assert au.normalizar_codigo("00123", quitar_ceros=False) == "00123"
    assert au.normalizar_codigo(None) == ""


def test_dentro_del_faltante_no_hay_extra():
    res = au.calcular_resultado(_base(), _hall([("123", 3)]))
    f = _fila(res, "123")
    assert f[au.COL_EXTRA] == 0
    assert f[au.COL_NUEVA] == -2
    assert f[au.COL_ESTADO] == au.ESTADO_PARCIAL


def test_cuadra_exacto():
    f = _fila(au.calcular_resultado(_base(), _hall([("123", 5)])), "123")
    assert f[au.COL_EXTRA] == 0 and f[au.COL_NUEVA] == 0
    assert f[au.COL_ESTADO] == au.ESTADO_CUADRA


def test_hallazgos_acumulados_generan_extra():
    # faltan 5, se encuentran 3 + 4 = 7 -> 2 extra
    f = _fila(au.calcular_resultado(_base(), _hall([("123", 3), ("00123", 4)])), "123")
    assert f[au.COL_ENC] == 7
    assert f[au.COL_EXTRA] == 2
    assert f[au.COL_NUEVA] == 2
    assert f[au.COL_ESTADO] == au.ESTADO_EXTRA


def test_sin_faltante_todo_es_extra():
    res = au.calcular_resultado(_base(), _hall([("456", 2), ("1001", 1)]))
    assert _fila(res, "456")[au.COL_EXTRA] == 2
    assert _fila(res, "1001")[au.COL_EXTRA] == 1


def test_codigo_no_existente_en_base():
    f = _fila(au.calcular_resultado(_base(), _hall([("9999", 4)])), "9999")
    assert f[au.COL_EXTRA] == 4
    assert f[au.COL_ESTADO] == au.ESTADO_NO_BASE
    assert pd.isna(f[au.COL_DIF])


def test_base_no_se_modifica_y_sin_hallazgos():
    base = _base()
    copia = base.copy()
    res = au.calcular_resultado(base, au.hallazgos_vacios())
    pd.testing.assert_frame_equal(base, copia)
    assert (res[au.COL_ESTADO] == au.ESTADO_SIN).all()
    assert res[au.COL_EXTRA].sum() == 0


def test_carga_sin_columna_cantidad_cuenta_uno_por_fila():
    h, _ = au.crear_hallazgos(pd.Series(["789", "789", "789", "789"]), None, "x")
    f = _fila(au.calcular_resultado(_base(), h), "789")
    assert f[au.COL_ENC] == 4 and f[au.COL_EXTRA] == 1


def test_filas_invalidas_se_descartan():
    h, avisos = au.crear_hallazgos(pd.Series(["123", "", "456", "789"]), pd.Series([1, 2, "abc", 0]), "x")
    assert list(h[au.COL_CODIGO]) == ["123"]
    assert len(avisos) == 2


def test_coma_decimal_y_duplicados_en_base():
    df = pd.DataFrame({"c": ["A", "A", "B"], "d": ["-1,5", "-2", "x"]})
    base, avisos = au.preparar_base(df, "c", "d")
    assert _fila(base, "A")[au.COL_DIF] == -3.5
    assert _fila(base, "B")[au.COL_DIF] == 0
    assert len(avisos) == 2


def test_exportar_excel_tiene_tres_hojas():
    res = au.calcular_resultado(_base(), _hall([("123", 7), ("9999", 1)]))
    contenido = au.exportar_excel(res, _hall([("123", 7), ("9999", 1)]))
    import io
    hojas = pd.read_excel(io.BytesIO(contenido), sheet_name=None)
    assert list(hojas) == ["Resultado", "Extras", "Hallazgos"]
    assert hojas["Extras"]["EXTRA"].sum() == 3
