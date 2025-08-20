# Tylö Integration Testing Guide

## Quick Test Setup

### Docker Test Instance (Recommended)

1. **Start test environment:**
   ```bash
   # Run the test script
   test-script.bat
   
   # Or manually:
   docker-compose -f docker-compose.test.yml up
   ```

2. **Access test instance:**
   - URL: http://localhost:8124
   - This runs on a different port to avoid conflicts with your live HA

3. **Add integration:**
   - Go to Settings > Devices & Services
   - Click "Add Integration"  
   - Search for "Tylö"
   - Configure with your COM port (or use mock for testing)

### Protocol Testing Without Hardware

```bash
cd custom_components/tylo
python test_protocol.py
```

### Safe Testing Tips

- ✅ Test instance uses port 8124 (not 8123)
- ✅ Separate config directory (`test-config/`)
- ✅ Debug logging enabled
- ✅ Your live HA remains untouched

### Testing with Real Hardware

**Important:** Home Assistant Core doesn't run natively on Windows, and Docker containers cannot access Windows COM ports directly.

For real hardware testing on Windows:

1. **WSL2 with USB Passthrough (Advanced):**
   - Install WSL2 with Ubuntu
   - Use `usbipd-win` to pass COM port to WSL
   - Install HA in WSL2
   - Complex but gives full control

2. **Home Assistant OS on VM:**
   - Use VirtualBox/VMware with USB passthrough
   - Install Home Assistant OS
   - Pass through USB-to-RS485 adapter
   - Most reliable for testing

3. **Main Home Assistant Instance:**
   - Copy `custom_components/tylo/` to your production HA
   - Test carefully with mock mode first
   - Use a backup before testing

4. **Check Hardware (Windows):**
   ```bash
   # See available COM ports
   test-hardware.bat
   ```

### Cleanup

```bash
# Stop test instance
docker-compose -f docker-compose.test.yml down

# Remove test containers
docker-compose -f docker-compose.test.yml down --volumes
```

## Troubleshooting

Check logs in the test instance:
```bash
docker logs ha-tylo-test -f
```