@echo off
chcp 65001 >nul
title E-commerce Data Hub

cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
    echo [1/3] Tao moi truong ao Python...
    python -m venv .venv
    if errorlevel 1 (
        echo LOI: Can cai Python 3.10+ va them vao PATH.
        pause
        exit /b 1
    )
    echo [2/3] Cai dat thu vien...
    .venv\Scripts\pip install -r backend\requirements.txt
    if errorlevel 1 (
        echo LOI: Khong the cai dat requirements.
        pause
        exit /b 1
    )
) else (
    echo Da co .venv — bo qua cai dat.
)

echo [3/3] Khoi dong server tai http://127.0.0.1:8000 ...
start "" http://localhost:8000
cd backend
..\.venv\Scripts\python.exe -m uvicorn main:app --host 127.0.0.1 --port 8000
