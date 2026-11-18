from auditoria_inventario import calculo as c


def _base():
    base, avisos = c.preparar_base(["00123", "456", "789", "1001"], [-5, 0, -3, 2],
                                   ["Filtro", "Correa", "Rodamiento", "Perno"])
    assert avisos == []
    return base


def _hall(pares):
    filas, _ = c.crear_hallazgos([a for a, _ in pares], [b for _, b in pares])
    return filas


def _fila(res, codigo):
    return next(f for f in res if f["codigo"] == codigo)


def test_normalizar_codigo():
    assert c.normalizar_codigo(" 00123 ") == "123"
    assert c.normalizar_codigo(123.0) == "123"
    assert c.normalizar_codigo("123.0") == "123"
    assert c.normalizar_codigo("ab-12 ") == "AB-12"
    assert c.normalizar_codigo("00123", quitar_ceros=False) == "00123"
    assert c.normalizar_codigo("000") == "0"
    assert c.normalizar_codigo(None) == ""
    assert c.normalizar_codigo(float("nan")) == ""


def test_dentro_del_faltante_no_hay_extra():
    f = _fila(c.calcular_resultado(_base(), _hall([("123", 3)])), "123")
    assert f["extra"] == 0 and f["nueva"] == -2
    assert f["estado"] == c.ESTADO_PARCIAL


def test_cuadra_exacto():
    f = _fila(c.calcular_resultado(_base(), _hall([("123", 5)])), "123")
    assert f["extra"] == 0 and f["nueva"] == 0
    assert f["estado"] == c.ESTADO_CUADRA


def test_hallazgos_acumulados_generan_extra():
    # faltan 5; se encuentran 3 + 4 = 7 -> 2 extra
    f = _fila(c.calcular_resultado(_base(), _hall([("123", 3), ("00123", 4)])), "123")
    assert f["encontrado"] == 7 and f["extra"] == 2 and f["nueva"] == 2
    assert f["estado"] == c.ESTADO_EXTRA


def test_sin_faltante_todo_es_extra():
    res = c.calcular_resultado(_base(), _hall([("456", 2), ("1001", 1)]))
    assert _fila(res, "456")["extra"] == 2
    assert _fila(res, "1001")["extra"] == 1  # diferencia +2: no faltaba nada


def test_codigo_no_existente_en_base():
    f = _fila(c.calcular_resultado(_base(), _hall([("9999", 4)])), "9999")
    assert f["extra"] == 4 and f["dif"] is None and f["nueva"] is None
    assert f["estado"] == c.ESTADO_NO_BASE


def test_orden_y_sin_hallazgos():
    base = _base()
    res = c.calcular_resultado(base, [])
    assert all(f["estado"] == c.ESTADO_SIN for f in res)
    res = c.calcular_resultado(base, _hall([("9999", 1), ("123", 9), ("789", 3)]))
    assert [f["estado"] for f in res[:3]] == [c.ESTADO_NO_BASE, c.ESTADO_EXTRA, c.ESTADO_CUADRA]


def test_carga_sin_columna_cantidad_cuenta_uno_por_fila():
    filas, _ = c.crear_hallazgos(["789"] * 4)
    f = _fila(c.calcular_resultado(_base(), filas), "789")
    assert f["encontrado"] == 4 and f["extra"] == 1


def test_filas_invalidas_se_descartan():
    filas, avisos = c.crear_hallazgos(["123", "", "456", "789", None], [1, 2, "abc", 0, 5])
    assert [f["codigo"] for f in filas] == ["123"]
    assert len(avisos) == 1


def test_coma_decimal_texto_y_duplicados_en_base():
    base, avisos = c.preparar_base(["A", "A", "B"], ["-1,5", "-2", "x"])
    assert base["A"]["dif"] == -3.5
    assert base["B"]["dif"] == 0
    assert len(avisos) == 2


def test_resumen():
    base = _base()
    res = c.calcular_resultado(base, _hall([("123", 7), ("9999", 1), ("789", 1)]))
    r = c.resumen(base, res)
    assert r["unidades_extra"] == 3          # 2 de 123 + 1 de 9999
    assert r["codigos_extra"] == 2
    assert r["no_en_base"] == 1
    assert r["faltante_inicial"] == 8        # 5 + 3
    assert r["faltante_pendiente"] == 2      # 789: faltan 2
    assert r["unidades_encontradas"] == 9
