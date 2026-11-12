@echo off
rem Sobe o Shiplog com um comando no Windows nativo. Equivale a `make run`.
cd /d "%~dp0"
where uv >nul 2>nul || (echo Instale o uv: https://docs.astral.sh/uv/ & exit /b 1)
if not exist .venv uv sync
if not exist frontend\dist\index.html (
  pushd frontend
  call npm install || exit /b 1
  call npm run build || exit /b 1
  popd
)
uv run shiplog %*
