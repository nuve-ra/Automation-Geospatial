@echo off
cd /d "%~dp0.."
python scripts/automated_pipeline.py
if errorlevel 1 (
    echo Pipeline failed with errors. Check logs for details.
    exit /b 1
) else (
    echo Pipeline completed successfully.
    exit /b 0
)
