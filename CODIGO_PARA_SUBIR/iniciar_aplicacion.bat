@echo off
title Sistema de Control de Cartera y Vencimientos
echo ==============================================================
echo     INICIANDO SISTEMA DE CONTROL DE CARTERA Y ALERTAS
echo              Agroindustriales Canaveralejo S.A.S
echo ==============================================================
echo.
cd /d "C:\Users\fasud\.gemini\antigravity\scratch\cartera-app"

echo Acceso desde este computador:  http://localhost:8050
echo Acceso desde celular (Wi-Fi):  http://192.168.80.20:8050
echo.
start "" "http://localhost:8050"

echo Servidor activo. Presione Ctrl+C en cualquier momento para detenerlo.
python -m uvicorn app:app --host 0.0.0.0 --port 8050
pause
