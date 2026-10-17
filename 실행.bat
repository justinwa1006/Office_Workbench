@echo off
chcp 65001 > nul
cd /d "%~dp0"
python -c "import PySide6, openpyxl" 2>nul || python -m pip install -r requirements.txt
python office_workbench_global_specs.py
if errorlevel 1 pause
