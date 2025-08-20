@echo off
echo Starting Home Assistant test instance...

REM Activate virtual environment
call ha-test-env\Scripts\activate.bat

REM Set test config path
set HASS_CONFIG_PATH=%CD%\test-config

REM Start Home Assistant (port configured in configuration.yaml)
hass --config test-config --verbose

pause