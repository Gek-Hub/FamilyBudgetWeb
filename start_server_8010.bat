@echo off
cd /d "%~dp0"
call venv\Scripts\activate.bat
echo Starting Django server at http://127.0.0.1:8010
python manage.py runserver 127.0.0.1:8010
pause
