"""Base de datos local (SQLite): Excel base cargado, configuración y hallazgos registrados."""
from __future__ import annotations

import json
import os
import sqlite3
import sys
from pathlib import Path

from .util import ahora_iso

NOMBRE_DB = "AuditoriaInventario_datos.db"
CARPETA = "AuditoriaInventario"

ESQUEMA = """
CREATE TABLE IF NOT EXISTS config (clave TEXT PRIMARY KEY, valor TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS hallazgos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    codigo TEXT NOT NULL,
    cantidad REAL NOT NULL,
    origen TEXT,
    fecha TEXT
);
"""


def carpeta_datos() -> Path:
    """Si junto al ejecutable ya existe la base de datos, se usa esa (modo portátil).
    Si no, Documentos\\AuditoriaInventario."""
    junto = Path(sys.executable).parent if getattr(sys, "frozen", False) else Path.cwd()
    if (junto / NOMBRE_DB).exists():
        return junto
    docs = Path.home() / "Documents"
    if not docs.exists():
        docs = Path.home()
    destino = docs / CARPETA
    try:
        destino.mkdir(parents=True, exist_ok=True)
        return destino
    except OSError:
        alt = Path(os.environ.get("APPDATA") or Path.home()) / CARPETA
        alt.mkdir(parents=True, exist_ok=True)
        return alt


class Repositorio:
    def __init__(self, ruta: str | Path):
        self.ruta = Path(ruta)
        self.ruta.parent.mkdir(parents=True, exist_ok=True)
        self.cx = sqlite3.connect(self.ruta)
        self.cx.row_factory = sqlite3.Row
        self.cx.executescript(ESQUEMA)
        self.cx.commit()

    def cerrar(self):
        self.cx.close()

    # ---------------------------------------------------------- configuración
    def get(self, clave: str, defecto=None):
        fila = self.cx.execute("SELECT valor FROM config WHERE clave=?", (clave,)).fetchone()
        return json.loads(fila["valor"]) if fila else defecto

    def set(self, clave: str, valor):
        self.cx.execute("INSERT INTO config(clave, valor) VALUES(?, ?) "
                        "ON CONFLICT(clave) DO UPDATE SET valor=excluded.valor",
                        (clave, json.dumps(valor, ensure_ascii=False)))
        self.cx.commit()

    def borrar(self, clave: str):
        self.cx.execute("DELETE FROM config WHERE clave=?", (clave,))
        self.cx.commit()

    # ---------------------------------------------------------- Excel base
    def base(self) -> tuple[dict, dict | None]:
        """({código: {"desc", "dif"}}, información del archivo) o ({}, None) si no hay base cargada."""
        return self.get("base", {}), self.get("info_base")

    def guardar_base(self, base: dict, info: dict):
        self.set("base", base)
        self.set("info_base", info)

    # ---------------------------------------------------------- hallazgos
    def hallazgos(self) -> list[dict]:
        return [dict(f) for f in self.cx.execute(
            "SELECT id, codigo, cantidad, origen, fecha FROM hallazgos ORDER BY id")]

    def agregar_hallazgo(self, codigo: str, cantidad: float, origen: str) -> int:
        """Registra un hallazgo y devuelve su id (para poder deshacerlo)."""
        cur = self.cx.execute("INSERT INTO hallazgos(codigo, cantidad, origen, fecha) VALUES(?, ?, ?, ?)",
                              (codigo, float(cantidad), origen, ahora_iso()))
        self.cx.commit()
        return int(cur.lastrowid)

    def agregar_hallazgos(self, filas: list[dict], origen: str) -> int:
        fecha = ahora_iso()
        self.cx.executemany("INSERT INTO hallazgos(codigo, cantidad, origen, fecha) VALUES(?, ?, ?, ?)",
                            [(f["codigo"], float(f["cantidad"]), origen, fecha) for f in filas])
        self.cx.commit()
        return len(filas)

    def eliminar_hallazgos(self, ids):
        self.cx.executemany("DELETE FROM hallazgos WHERE id=?", [(int(i),) for i in ids])
        self.cx.commit()

    def borrar_hallazgos(self):
        self.cx.execute("DELETE FROM hallazgos")
        self.cx.commit()

    def origenes(self) -> set[str]:
        return {f[0] for f in self.cx.execute("SELECT DISTINCT origen FROM hallazgos")}

    def nueva_auditoria(self):
        self.borrar_hallazgos()
        self.borrar("base")
        self.borrar("info_base")

    def respaldar(self, destino: str | Path):
        dst = sqlite3.connect(destino)
        with dst:
            self.cx.backup(dst)
        dst.close()
