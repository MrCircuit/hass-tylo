# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a Home Assistant custom integration for Tylö-Helo sauna controls using RS485 interface communication. The integration monitors sauna state and temperature data via RS485 protocol and exposes them as Home Assistant entities.

## Development Commands

This project does not use standard build tools like npm, pip, or cargo. It's a pure Python Home Assistant custom component with no specific build, test, or lint commands configured.

The integration follows modern Home Assistant development patterns and uses:
- Python 3.11+ type hints
- Modern entity patterns with `_attr_` properties
- Platform.SWITCH and Platform.SENSOR enum usage

## Architecture

### Core Components

- **RS485 Protocol Handler** (`protocol.py`): Contains the core protocol implementation for communicating with Tylö-Helo sauna controllers. Implements packet parsing, CRC validation, and real-time state monitoring. Key data points decoded:
  - Temperature readings (0x6000): actual vs set point temperatures
  - State codes (0x3400): ready/light/heater status
  - Operating time counters (0x9400/0x9401): total uptime and remaining bathing time


- **Home Assistant Integration**:
  - `__init__.py`: Entry point, sets up platforms (switch, sensor, binary_sensor)
  - `config_flow.py`: UI configuration flow with COM port selection (modernized)
  - `switch.py`: Sauna heater and light switch entities with RS485 commands
  - `sensor.py`: Temperature and time sensor entities with live data
  - `binary_sensor.py`: Ready state sensor
  - `protocol.py`: RS485 protocol handler with packet processing
  - `const.py`: Domain constants and entity definitions
  - `hub.py`: Sauna controller hub with integrated RS485 communication

### Integration Type

- **Domain**: "tylo"
- **Type**: Hub integration with local push updates
- **Platforms**: switch, sensor, binary_sensor
- **Config Flow**: Enabled for UI-based setup with host and COM port selection

### Protocol Details

The RS485 implementation in `protocol.py` contains extensive protocol documentation:
- Uses 19200 baud, even parity serial communication
- Custom frame escaping (0x91 escape sequences)
- 16-bit CRC validation (polynomial 0x90d9)
- Real-time packet monitoring and state updates

### Development Notes

- **Updated to modern HA patterns**: Uses 2024-2025 integration standards
- **Switch entities**: Heater and light controls using modern SwitchEntity
- **Sensor entities**: Temperature, bathing time, and uptime sensors with proper device classes
- **Modern entity patterns**: Uses `_attr_has_entity_name = True` and declarative attributes
- **Type hints**: Full Python 3.11+ type annotation support
- **Device info**: Proper device registry integration

### Integration Status

✅ **Fully Integrated Components**:
- manifest.json with proper requirements (removed MQTT)
- Config flow with COM port discovery and selection
- Switch platform for heater/light control with RS485 commands
- Sensor platform for temperature and time monitoring with live data
- Binary sensor platform for ready state
- Hub class with integrated RS485 protocol handler
- Real-time packet monitoring and state synchronization
- Complete RS485 protocol implementation with CRC validation

🚀 **Ready for Use**:
- All entities are wired to live RS485 data
- Switch controls send actual RS485 commands
- Real-time monitoring of sauna state
- Automatic entity updates on protocol state changes

## Critical Implementation Details

### Async Serial Communication
**CRITICAL**: The integration uses `loop.run_in_executor()` to run blocking serial operations in separate threads to prevent Home Assistant event loop blocking. This was essential to fix the integration hanging issue.

```python
# Correct approach - run blocking serial reads in executor
frame = await loop.run_in_executor(None, self._serial.read, 16)
```

**Never use blocking serial calls directly in async methods** - this will freeze the entire Home Assistant instance.

### Frame Processing Architecture
The protocol uses a sophisticated buffering system to handle RS485 data:

1. **Small chunk reads** (16 bytes) to avoid concatenated frames
2. **Frame buffer** that accumulates data gradually
3. **Escape sequence aware** frame boundary detection
4. **Individual frame extraction** with proper SOF/EOF handling

This approach prevents the frame concatenation issues that caused CRC errors.

### CRC Validation
**VERIFIED WORKING**: The CRC calculation is correct:
- **Polynomial**: 0x90d9 
- **Parameters**: 16-bit, init 0xffff, no XOR, no reversal
- **Validation**: Frame `9840066d3a9c` validates perfectly (data: `4006`, CRC: `0x6d3a`)

### Testing Setup
**Production Testing**: Docker containers cannot access Windows COM ports directly. For real hardware testing:

1. **Mock Mode**: Use "Mock/Test mode" in config flow for safe testing
2. **Real Hardware**: Install directly to main Home Assistant instance or use WSL2 with USB passthrough
3. **Test Environment**: Created Docker + Python virtual environment scripts for safe testing

### Known Issues & Solutions
1. **Integration Hanging**: Fixed by using executor for serial reads
2. **CRC Errors**: Mix of good and corrupted frames is normal - good frames process correctly
3. **Frame Concatenation**: Fixed by chunked reading and proper buffer management
4. **Config Flow Host Field**: Removed unnecessary CONF_HOST for serial-only setup

### Protocol Communication
**Frame Structure**:
- SOF: 0x98
- Data: Address + Command + Payload  
- CRC: 16-bit checksum
- EOF: 0x9c
- Escaping: 0x91 + modified byte

**Example Valid Frame**: `9840066d3a9c`
- SOF: 0x98
- Address: 0x40
- Command: 0x0060 (temperature reading)
- CRC: 0x6d3a (validates correctly)
- EOF: 0x9c

### Troubleshooting
- **No COM ports in Docker**: Expected - use mock mode or install to main HA
- **CRC warnings**: Normal - corrupted frames mixed with good ones
- **Integration hangs**: Ensure executor is used for all blocking serial operations
- **No entities**: Check serial device mapping and permissions