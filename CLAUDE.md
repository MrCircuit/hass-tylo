# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a Home Assistant custom integration for Tylö-Helo sauna controls using RS485 interface communication. The integration monitors sauna state and temperature data via RS485 protocol and publishes to MQTT.

## Development Commands

This project does not use standard build tools like npm, pip, or cargo. It's a pure Python Home Assistant custom component with no specific build, test, or lint commands configured.

## Architecture

### Core Components

- **RS485 Protocol Handler** (`rs485.py`): Contains the core protocol implementation for communicating with Tylö-Helo sauna controllers. Implements packet parsing, CRC validation, and MQTT publishing. Key data points decoded:
  - Temperature readings (0x6000): actual vs set point temperatures
  - State codes (0x3400): ready/light/heater status
  - Operating time counters (0x9400/0x9401): total uptime and remaining bathing time

- **Hub** (`hub.py`): Currently contains template/dummy implementation with roller devices. This needs to be replaced with actual sauna device management.

- **Home Assistant Integration**:
  - `__init__.py`: Entry point, sets up platforms (cover, sensor)
  - `config_flow.py`: UI configuration flow for adding the integration
  - `cover.py`: Currently implements dummy cover entities (needs sauna-specific implementation)
  - `sensor.py`: Currently implements dummy sensors (needs temperature/state sensors)
  - `const.py`: Domain constant definition

### Integration Type

- **Domain**: "tylo"
- **Type**: Hub integration with local push updates
- **Platforms**: cover, sensor
- **Config Flow**: Enabled for UI-based setup

### Protocol Details

The RS485 implementation in `rs485.py` contains extensive protocol documentation:
- Uses 19200 baud, even parity serial communication
- Custom frame escaping (0x91 escape sequences)
- 16-bit CRC validation (polynomial 0x90d9)
- MQTT publishing to configurable broker and topic

### Development Notes

- The current implementation is based on Home Assistant's "Hello World" template
- Most entities (Hub, Cover, Sensor classes) contain template code that needs replacement with sauna-specific functionality
- The actual sauna protocol implementation exists in `rs485.py` but is not yet integrated with the HA components
- Serial port configuration is currently commented out in `rs485.py` (lines 182-189)

### Key Integration Points

To connect the RS485 protocol with Home Assistant:
1. Replace dummy Hub class with sauna controller management
2. Implement sauna-specific Cover entity (for heater/light control)
3. Implement temperature and state Sensor entities
4. Connect RS485 data parsing to entity state updates