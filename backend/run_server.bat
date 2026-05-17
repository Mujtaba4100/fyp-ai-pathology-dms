@echo off
cd /d %~dp0

if exist venv\Scripts\activate.bat (
	call venv\Scripts\activate.bat
) else (
	echo [WARN] venv not found at %cd%\venv. Create one with: python -m venv venv
)

uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
