# Auditoría de Inventario

App en Python (Streamlit) para registrar los repuestos **encontrados después** del conteo y detectar
las unidades **EXTRA**: lo encontrado que supera el faltante original del Excel base.
El Excel base **nunca se modifica**.

## Instalación (una sola vez)

Requiere Python 3.10 o superior.

```bash
pip install -r requirements.txt
```

## Cómo abrirla

```bash
streamlit run app.py
```

Se abre en el navegador (http://localhost:8501). En Windows también puedes hacer doble clic en `iniciar_app.bat`.

## Uso

1. **Excel base** (barra lateral): sube el archivo y elige la hoja, la fila de encabezados y las columnas de
   **Código**, **Diferencia** y, opcionalmente, **Descripción**.
   Los faltantes van en **negativo** (−5 = faltan 5 unidades).
2. **Registrar repuesto**: ingresa el código y la cantidad, uno a uno (también sirve con un lector de códigos de barra).
   Al agregar, la app te avisa en el momento si ese código ya tiene unidades EXTRA.
3. **Cargar Excel de hallazgos**: si encontraste muchos repuestos, sube un Excel y elige la columna de código y la
   de cantidad. Si no tiene columna de cantidad, cada fila cuenta como 1 unidad. Antes de agregar, ves una vista
   previa con los extras que se generarían.
4. **Resultado y extras**: muestra el total de unidades EXTRA y el detalle por código. Desde ahí descargas el Excel.
5. **Hallazgos registrados**: lista de todo lo ingresado. Selecciona filas para eliminar errores de digitación.

## Cálculo

| Concepto | Fórmula |
|---|---|
| Faltante | `-Diferencia original` si es negativa; si no, 0 |
| Total encontrado | Suma de todas las cantidades registradas para el código |
| Nueva diferencia | `Diferencia original + Total encontrado` |
| **EXTRA** | `Total encontrado − Faltante` (mínimo 0) |

Ejemplo: diferencia −5. Se encuentran 3 y luego 4 (7 en total), así que la nueva diferencia es +2 y hay **2 EXTRA**.

Estados posibles:

- **EXTRA - revisar**: se encontró más de lo que faltaba.
- **No existe en base - revisar**: el código no está en el Excel base, así que todo lo encontrado es extra.
- **Cuadrado**: lo encontrado cubre exactamente el faltante.
- **Faltante cubierto parcialmente**: todavía faltan unidades.
- **Sin hallazgos**: el código no tiene registros.

Los códigos se comparan sin espacios y sin distinguir mayúsculas de minúsculas. Por defecto también se ignoran los
ceros a la izquierda en códigos numéricos (`00123` = `123`); esto se puede desactivar en la barra lateral.

## Excel exportado

Trae tres hojas:

- **Resultado**: todos los códigos.
- **Extras**: solo lo que hay que revisar.
- **Hallazgos**: el detalle de cada ingreso.

Los hallazgos duran mientras la app esté abierta. Para continuar otro día, carga la hoja **Hallazgos** del Excel
exportado en la pestaña *Cargar Excel de hallazgos*.

## Archivos de ejemplo

En `ejemplos/` hay un Excel base y uno de hallazgos para probar la app.

## Pruebas

```bash
python -m pytest tests
```
