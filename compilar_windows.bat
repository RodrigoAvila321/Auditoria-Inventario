@echo off
REM Compila AuditoriaInventario.exe (requiere Python 3.10 o superior instalado desde python.org)
cd /d "%~dp0"
python -m pip install --upgrade pip
python -m pip install -r requirements-dev.txt
python -c "from auditoria_inventario.tema import guardar_ico; guardar_ico('icono.ico')"
pyinstaller --noconfirm --onefile --windowed --hidden-import PIL._tkinter_finder --icon icono.ico --name AuditoriaInventario main.py
echo.
echo Listo: el ejecutable quedo en la carpeta dist\AuditoriaInventario.exe
pause
