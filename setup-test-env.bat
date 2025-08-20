@echo off
echo Setting up Home Assistant test environment...

REM Create virtual environment
python -m venv ha-test-env

REM Activate virtual environment
call ha-test-env\Scripts\activate.bat

REM Install Home Assistant
pip install homeassistant

REM Create test directory structure
if not exist "test-config\custom_components" mkdir test-config\custom_components

REM Copy integration to test config
xcopy /E /I custom_components test-config\custom_components

echo.
echo Test environment setup complete!
echo.
echo To start Home Assistant test instance:
echo   1. Run: start-test-ha.bat
echo   2. Open: http://localhost:8124
echo.