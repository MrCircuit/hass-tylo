@echo off
echo =============================================================
echo  Testing Tylö Integration with Real Hardware
echo =============================================================
echo.
echo Docker containers cannot access Windows COM ports directly.
echo For real hardware testing, you have two options:
echo.
echo 1. PYTHON VIRTUAL ENVIRONMENT (Recommended)
echo    - Run: setup-test-env.bat
echo    - Then: start-test-ha.bat
echo    - Your COM ports will be accessible
echo.
echo 2. NATIVE HOME ASSISTANT INSTANCE
echo    - Install on your main Home Assistant
echo    - Copy custom_components/tylo folder
echo    - Restart Home Assistant
echo.
echo =============================================================
echo Current hardware detection:
echo =============================================================

python check_ports.py

echo.
echo Press any key to continue...
pause > nul