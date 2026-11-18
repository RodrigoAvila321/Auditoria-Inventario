# Auditoría de Inventario: programa de escritorio

Programa en Python con interfaz gráfica, distribuible como ejecutable de Windows (`AuditoriaInventario.exe`). Sirve para
registrar los repuestos **encontrados después** del conteo de inventario y cruzarlos con la columna de diferencias del
Excel base, para detectar las unidades **EXTRA**: lo encontrado por sobre lo que faltaba, que es la discrepancia a
revisar. El Excel base **nunca se modifica**.

Usa el mismo diseño «grafito + ámbar» que **Control de Aceites**: fondo oscuro, acentos ámbar y navegación por pestañas
superiores.

## Obtener el ejecutable

Cada `push` compila el `.exe` en GitHub Actions con el workflow **Compilar ejecutable Windows**. Hay dos formas de
descargarlo:

- **Release:** en la pestaña *Releases* del repositorio, descargue `AuditoriaInventario.exe` desde «Assets».
- **Artefacto:** en la pestaña *Actions*, abra la última ejecución correcta y descargue **AuditoriaInventario-windows**.

No requiere instalar Python: se abre con doble clic. La primera vez Windows puede mostrar «Windows protegió su PC»,
porque el ejecutable no está firmado. En ese caso elija *Más información → Ejecutar de todas formas*.

Para compilarlo en Windows sin GitHub, instale Python 3.12 desde python.org (marque «Add python.exe to PATH») y haga
doble clic en `compilar_windows.bat`. El ejecutable queda en `dist\AuditoriaInventario.exe`. Equivale a:

```bash
pip install -r requirements-dev.txt
python -c "from auditoria_inventario.tema import guardar_ico; guardar_ico('icono.ico')"
pyinstaller --noconfirm --onefile --windowed --hidden-import PIL._tkinter_finder --icon icono.ico --name AuditoriaInventario main.py
```

Para ejecutarlo sin compilar: `pip install -r requirements.txt` y luego `python main.py`.

## Flujo de uso (pantalla «Auditoría»)

| Paso | Botón | Qué hace |
|---|---|---|
| 1 | **Cargar Excel base** | Elige el archivo (`.xlsx`, `.xlsm` o `.csv`), la hoja, la fila de títulos y qué columna es el **código**, la **diferencia** y, opcionalmente, la **descripción**. Las columnas y la fila de títulos se detectan solas. Los faltantes vienen en **negativo** (−5 = faltan 5). |
| 2 | **Agregar** | Registra un repuesto encontrado (código + cantidad). Enter también agrega, así que sirve con lector de código de barras. Si el código ya suma unidades EXTRA, avisa en el momento. Si el código no está en la base, pide confirmación antes de registrarlo (puede ser un error de digitación). Incluye **Deshacer** para el último registro. |
| 2 | **Cargar Excel de hallazgos** | Agrega muchos repuestos a la vez desde un Excel: se elige la columna de código y la de cantidad (sin columna de cantidad, cada fila cuenta 1). Antes de agregar muestra cómo quedaría cada código y cuántos extras se generarían. Avisa si el mismo archivo ya se había cargado. |
| — | **Exportar Excel** | Genera un archivo con tres hojas: **Resultado**, **Extras** (con el total) y **Hallazgos**. |
| — | **Nueva auditoría** | Borra el Excel base y los hallazgos para empezar otra auditoría. Antes ofrece exportar. |

Indicadores: **Unidades EXTRA**, **Códigos con EXTRA**, **No están en el Excel base**, **Unidades encontradas** y
**Faltante pendiente**. La tabla «Resultado por código» se puede filtrar (Con hallazgos, Solo EXTRA, Todos) y buscar por
código o descripción. Con doble clic en un código se ven sus registros.

La pestaña **Hallazgos registrados** lista cada ingreso con fecha y origen (Manual o el nombre del Excel). Ahí se pueden
seleccionar filas y eliminarlas.

## Reglas de cálculo

| Concepto | Fórmula |
|---|---|
| Faltante | `−Diferencia original` si es negativa; si no, 0 |
| Total encontrado | Suma de todo lo registrado para el código |
| Nueva diferencia | `Diferencia original + Total encontrado` |
| **EXTRA** | `Total encontrado − Faltante` (mínimo 0) |

Ejemplo: diferencia −5. Se encuentran 3 y luego 4 (7 en total), así que la nueva diferencia es +2 y hay **2 EXTRA**.

Estados:

| Estado | Significado |
|---|---|
| **No está en base** | El código no existe en el Excel base, así que todo lo encontrado es EXTRA. |
| **EXTRA** | Se encontró más de lo que faltaba. |
| **Cuadrado** | Lo encontrado cubre exactamente el faltante. |
| **Faltante parcial** | Todavía faltan unidades. |
| **Sin hallazgos** | El código no tiene registros. |

Los códigos se comparan sin espacios y sin distinguir mayúsculas de minúsculas. Por defecto también se ignoran los ceros
a la izquierda en códigos numéricos (`00123` = `123`); esto se puede desactivar al cargar el Excel base. Si un código
aparece repetido en el Excel base, sus diferencias se suman y el programa lo avisa.

## Datos

- Todo se guarda automáticamente en `Documentos\AuditoriaInventario\AuditoriaInventario_datos.db`. Al cerrar y volver a
  abrir, el programa sigue donde quedó.
- Si junto al `.exe` existe un `AuditoriaInventario_datos.db`, se usa ese (modo portátil).
- Los Excel exportados se proponen en `Documentos\AuditoriaInventario\Reportes`.
- En **Ayuda** están los botones *Abrir carpeta de datos* y *Respaldar datos*.

## Estructura

```
main.py                         punto de entrada
auditoria_inventario/
  calculo.py                    cruce base vs. hallazgos: nueva diferencia, EXTRA y estados
  excel.py                      lectura de Excel/CSV (solo lectura) y exportación del resultado
  db.py                         base de datos SQLite local
  app.py, dialogos.py,
  widgets.py, tema.py, util.py  interfaz gráfica (Tkinter) y diseño
ejemplos/                       Excel base y Excel de hallazgos para probar
tests/                          pruebas (pytest)
```

```bash
python -m pytest -q tests
```
