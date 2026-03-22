@echo off
REM ── Atualiza o dashboard e faz push para GitHub Pages ──

cd /d "R:\Macro EMs\Chile\7. Fiscal\DadosPensiones\painel_novo"

echo [%date% %time%] Iniciando build... >> update_log.txt

REM Rodar o build
python src\build.py >> update_log.txt 2>&1

IF %ERRORLEVEL% NEQ 0 (
    echo [%date% %time%] ERRO no build >> update_log.txt
    exit /b 1
)

REM Git add, commit e push
git add docs\index.html >> update_log.txt 2>&1
git diff --staged --quiet
IF %ERRORLEVEL% NEQ 0 (
    git commit -m "Update dashboard %date:~6,4%-%date:~3,2%-%date:~0,2%" >> update_log.txt 2>&1
    git push >> update_log.txt 2>&1
    echo [%date% %time%] Push realizado com sucesso >> update_log.txt
) ELSE (
    echo [%date% %time%] Sem alteracoes para commit >> update_log.txt
)
