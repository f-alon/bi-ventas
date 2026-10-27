@echo off
title BI Ventas - Dashboard
cd /d "%~dp0"

echo ==============================================
echo        Iniciando BI Ventas Dashboard...
echo ==============================================
echo.

if not exist ".venv\Scripts\python.exe" (
    echo [ERROR] No se encontro el entorno virtual en .venv
    echo Creando entorno virtual...
    python -m venv .venv
    if errorlevel 1 (
        echo [ERROR] No se pudo crear el entorno virtual. Asegurate de tener Python instalado.
        pause
        exit /b 1
    )
    echo Instalando paquetes requeridos...
    ".venv\Scripts\python.exe" -m pip install -r requirements.txt
)

:: Generar datos de ejemplo si no existen aun
if not exist "data\bi.duckdb" (
    echo [INFO] Creando base de datos inicial con seed_data.py...
    ".venv\Scripts\python.exe" "scripts\seed_data.py"
    if errorlevel 1 (
        echo [ERROR] Fallo la creacion de la base de datos inicial.
        pause
        exit /b 1
    )
)

echo Abriendo el panel en tu navegador web...
echo (Presiona Ctrl+C en esta consola cuando quieras detener el servidor)
echo.

:: Se usa python -m streamlit para evitar rutas absolutas fijas de streamlit.exe
".venv\Scripts\python.exe" -m streamlit run app.py

if errorlevel 1 (
    echo.
    echo ================================================================
    echo [AVISO] Si el error persiste debido a que la carpeta cambio de
    echo disco (de C: a E:), el entorno .venv puede requerir regenerarse.
    echo ================================================================
    echo.
    pause
)
