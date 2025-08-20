#!/bin/bash
echo "============================================================="
echo " Testing Tylö Integration in WSL2 with USB Passthrough"
echo "============================================================="
echo

echo "Step 1: Check if USB device is attached"
echo "============================================================="
if ls /dev/ttyUSB* 2>/dev/null || ls /dev/ttyACM* 2>/dev/null; then
    echo "✅ USB serial devices found:"
    ls -la /dev/tty{USB,ACM}* 2>/dev/null || echo "No devices found"
else
    echo "❌ No USB serial devices found"
    echo "Make sure you've attached the device with:"
    echo "  usbipd wsl attach --busid YOUR-BUSID --distribution Ubuntu-22.04"
    exit 1
fi

echo
echo "Step 2: Check Docker"
echo "============================================================="
if ! command -v docker &> /dev/null; then
    echo "❌ Docker not installed. Run:"
    echo "  curl -fsSL https://get.docker.com -o get-docker.sh"
    echo "  sudo sh get-docker.sh"
    echo "  sudo usermod -aG docker $USER"
    exit 1
fi

if ! docker ps &> /dev/null; then
    echo "❌ Docker daemon not running or no permissions"
    echo "Run: sudo service docker start"
    echo "Or logout/login after adding user to docker group"
    exit 1
fi

echo "✅ Docker is working"

echo
echo "Step 3: Start Home Assistant with USB access"
echo "============================================================="
docker-compose -f docker-compose.wsl.yml up

echo
echo "Access Home Assistant at: http://localhost:8124"