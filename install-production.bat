@echo off
echo =============================================================
echo  Installing Tylö Integration to Production Home Assistant
echo =============================================================
echo.
echo WARNING: This will install the integration to your main HA instance.
echo Make sure you have tested with mock mode first!
echo.
set /p "continue=Continue? (y/N): "
if /i not "%continue%"=="y" (
    echo Installation cancelled.
    goto :end
)
echo.
echo Please enter your Home Assistant config directory path.
echo Examples:
echo   \\server\config
echo   C:\ProgramData\homeassistant
echo   \\192.168.1.100\config
echo.
set /p "ha_config=HA Config Path: "

if "%ha_config%"=="" (
    echo Error: No path entered
    goto :end
)

if not exist "%ha_config%" (
    echo Error: Path does not exist: %ha_config%
    goto :end
)

echo.
echo Installing integration...
xcopy /E /I /Y "custom_components\tylo" "%ha_config%\custom_components\tylo\"

if errorlevel 1 (
    echo Error: Failed to copy files
    goto :end
)

echo.
echo ✅ Integration installed successfully!
echo.
echo Next steps:
echo 1. Restart Home Assistant
echo 2. Go to Settings ^> Devices ^& Services
echo 3. Click "Add Integration"
echo 4. Search for "Tylö"
echo 5. Test with mock mode first, then try real hardware
echo.

:end
pause