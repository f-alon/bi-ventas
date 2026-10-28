@echo off
title LABFIX ERP - Taller de Reparaciones, POS & BI
cd /d "%~dp0"

echo ==============================================================
echo        INICIANDO LABFIX ERP - REPARACIONES, POS & CAJA
echo ==============================================================
echo.

set STREAMLIT_BROWSER_GATHER_USAGE_STATS=false

if not exist ".venv\Scripts\python.exe" (
    echo [ERROR] No se encontro el archivo .venv\Scripts\python.exe
    pause
    exit /b 1
)

echo [INFO] Iniciando el dashboard y abriendo tu navegador...
echo (Podes cerrar esta ventana con Ctrl + C cuando termines de usarlo)
echo.

".venv\Scripts\python.exe" -m streamlit run app.py

if errorlevel 1 (
    echo.
    echo [ERROR] Ocurrio un error al ejecutar la aplicacion.
    pause
)
