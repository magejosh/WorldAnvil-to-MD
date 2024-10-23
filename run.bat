@echo off
SETLOCAL

REM Check if the venv directory exists
IF NOT EXIST "venv" (
    ECHO Creating a new virtual environment...
    python -m venv venv

    REM Activate the newly created virtual environment
    CALL venv\Scripts\activate.bat

    ECHO Installing dependencies from requirements.txt...
    pip install -r requirements.txt
)

REM Activate the virtual environment (in case it was already existing)
CALL venv\Scripts\activate.bat

REM Run the Python script  
python WA-Parser.py

ENDLOCAL
