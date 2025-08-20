@echo off
echo =============================================================
echo  Setting Up USB Passthrough for Docker + Home Assistant
echo =============================================================
echo.
echo Docker Desktop's WSL2 doesn't support USBIP by default.
echo We need to use a regular WSL2 Ubuntu distribution instead.
echo.
echo Step 1: Install Ubuntu WSL2 Distribution
echo =============================================================
echo Run this command to install Ubuntu:
echo   wsl --install Ubuntu-22.04
echo.
echo Step 2: Enable USBIP in WSL2
echo =============================================================
echo After Ubuntu is installed, run these commands in Ubuntu:
echo   sudo apt update
echo   sudo apt install linux-tools-virtual hwdata
echo   sudo update-alternatives --install /usr/local/bin/usbip usbip `ls /usr/lib/linux-tools/*/usbip | tail -n1` 20
echo.
echo Step 3: Attach USB Device
echo =============================================================
echo From Windows Command Prompt:
echo   usbipd list
echo   usbipd wsl attach --busid YOUR-BUSID --distribution Ubuntu-22.04
echo.
echo Step 4: Run Home Assistant in WSL2
echo =============================================================
echo In Ubuntu WSL2:
echo   # Install Docker
echo   curl -fsSL https://get.docker.com -o get-docker.sh
echo   sudo sh get-docker.sh
echo   sudo usermod -aG docker $USER
echo   
echo   # Clone your integration
echo   # Run docker-compose with device access
echo.
echo Alternative: Use production installation instead
echo =============================================================
echo If this seems too complex, use: install-production.bat
echo.
pause