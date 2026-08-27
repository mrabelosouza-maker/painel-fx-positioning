@echo off
REM ── Atualiza o dashboard e faz push para GitHub Pages ──

SET "WD=R:\Macro EMs\Chile\7. Fiscal\DadosPensiones\painel_novo"
SET "PYTHON=C:\Users\mrabelo\AppData\Local\Microsoft\WindowsApps\python.exe"
SET "GIT=C:\Users\mrabelo\AppData\Local\Programs\Git\cmd\git.exe"

pushd "%WD%"

echo [%date% %time%] Iniciando build... >> "%WD%\update_log.txt"

"%PYTHON%" "%WD%\src\build.py" >> "%WD%\update_log.txt" 2>&1

IF %ERRORLEVEL% NEQ 0 (
    echo [%date% %time%] ERRO no build >> "%WD%\update_log.txt"
    popd
    exit /b 1
)

"%GIT%" add docs/index.html data/afp_flow_daily.csv >> "%WD%\update_log.txt" 2>&1
"%GIT%" diff --staged --quiet
IF %ERRORLEVEL% NEQ 0 (
    "%GIT%" commit -m "Update dashboard %date:~6,4%-%date:~3,2%-%date:~0,2%" >> "%WD%\update_log.txt" 2>&1
    "%GIT%" push >> "%WD%\update_log.txt" 2>&1
    echo [%date% %time%] Push realizado com sucesso >> "%WD%\update_log.txt"
) ELSE (
    echo [%date% %time%] Sem alteracoes para commit >> "%WD%\update_log.txt"
)

popd
