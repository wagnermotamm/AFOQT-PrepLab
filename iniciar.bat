@echo off
cd /d "%~dp0"
echo.
echo Simulado AFOQT
echo Banco: data\questions.json
echo Endereco: http://127.0.0.1:8765/
echo.
echo Feche esta janela para encerrar o servidor.
echo.
start "" cmd /c "timeout /t 1 /nobreak >nul & start http://127.0.0.1:8765/"
python -m http.server 8765
if errorlevel 1 (
  echo.
  echo Nao foi possivel iniciar o Python. Instale o Python e tente de novo.
  pause
)
