@echo off
REM Install dependencies
pip install -r requirements.txt

REM Run Django migrations
python manage.py migrate

pause