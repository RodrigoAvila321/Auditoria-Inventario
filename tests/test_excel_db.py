import csv

from openpyxl import Workbook, load_workbook

from auditoria_inventario import calculo as c
from auditoria_inventario import excel
from auditoria_inventario.db import Repositorio


def _xlsx(ruta, filas, hoja="Inventario"):
    wb = Workbook()
    ws = wb.active
    ws.title = hoja
    for f in filas:
        ws.append(f)
    wb.save(ruta)


def test_lectura_con_titulo_sobre_encabezados(tmp_path):
    ruta = tmp_path / "base.xlsx"
    _xlsx(ruta, [["INVENTARIO BODEGA"], [], ["Código", "Descripción", "Diferencia"],
                 ["00123", "Filtro", -5], [456, "Correa", 0], [None, None, None], ["789", "Rodamiento", "-3"]])
    assert excel.hojas(ruta) == ["Inventario"]
    filas = excel.filas_crudas(ruta, "Inventario")
    fila = excel.detectar_encabezado(filas)
    assert fila == 3
    cols, datos = excel.tabla(filas, fila)
    assert cols == ["Código", "Descripción", "Diferencia"]
    assert len(datos) == 3
    assert excel.adivinar(cols, excel.CLAVES_DIF) == 2
    base, _ = c.preparar_base(excel.columna(datos, 0), excel.columna(datos, 2), excel.columna(datos, 1))
    assert base == {"123": {"desc": "Filtro", "dif": -5.0}, "456": {"desc": "Correa", "dif": 0.0},
                    "789": {"desc": "Rodamiento", "dif": -3.0}}


def test_lectura_csv_punto_y_coma(tmp_path):
    ruta = tmp_path / "h.csv"
    with open(ruta, "w", newline="", encoding="cp1252") as f:
        w = csv.writer(f, delimiter=";")
        w.writerows([["Código", "Cantidad"], ["123", "3"], ["Ñ-1", "1,5"]])
    filas = excel.filas_crudas(ruta, "CSV")
    cols, datos = excel.tabla(filas, excel.detectar_encabezado(filas))
    assert cols == ["Código", "Cantidad"]
    hall, _ = c.crear_hallazgos(excel.columna(datos, 0), excel.columna(datos, 1))
    assert hall == [{"codigo": "123", "cantidad": 3.0}, {"codigo": "Ñ-1", "cantidad": 1.5}]


def test_exportar(tmp_path):
    base, _ = c.preparar_base(["123", "789"], [-5, -3], ["Filtro", "Rodamiento"])
    hall = [{"codigo": "123", "cantidad": 7.0, "origen": "Manual", "fecha": "2026-01-01 10:00:00"},
            {"codigo": "9999", "cantidad": 1.0, "origen": "Manual", "fecha": "2026-01-01 10:01:00"}]
    res = c.calcular_resultado(base, hall)
    ruta = tmp_path / "salida.xlsx"
    excel.exportar(ruta, res, hall, {"archivo": "base.xlsx"})
    wb = load_workbook(ruta)
    assert wb.sheetnames == ["Resultado", "Extras", "Hallazgos"]
    ext = list(wb["Extras"].iter_rows(values_only=True))
    assert ext[-1][0] == "TOTAL EXTRA" and ext[-1][5] == 3
    assert wb["Hallazgos"].max_row == 3


def test_repositorio_persistencia(tmp_path):
    ruta = tmp_path / "datos.db"
    repo = Repositorio(ruta)
    repo.guardar_base({"123": {"desc": "Filtro", "dif": -5.0}}, {"archivo": "base.xlsx", "quitar_ceros": True})
    i = repo.agregar_hallazgo("123", 3, "Manual")
    repo.agregar_hallazgos([{"codigo": "123", "cantidad": 4}, {"codigo": "9", "cantidad": 1}], "Excel: h.xlsx")
    repo.cerrar()

    repo = Repositorio(ruta)  # reabrir: los datos siguen ahí
    base, info = repo.base()
    assert base["123"]["dif"] == -5.0 and info["archivo"] == "base.xlsx"
    assert len(repo.hallazgos()) == 3
    assert repo.origenes() == {"Manual", "Excel: h.xlsx"}
    repo.eliminar_hallazgos([i])
    assert sum(h["cantidad"] for h in repo.hallazgos()) == 5
    repo.nueva_auditoria()
    assert repo.base() == ({}, None) and repo.hallazgos() == []
