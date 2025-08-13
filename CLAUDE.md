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