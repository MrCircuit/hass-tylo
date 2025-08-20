"""RS485 protocol handler for Tylö-Helo sauna controllers."""
from __future__ import annotations

import asyncio
import datetime
import logging
import struct
from typing import Callable, Any

import serial
from crc import Calculator, Configuration

_LOGGER = logging.getLogger(__name__)


class MockSerial:
    """Mock serial interface for testing."""
    
    def __init__(self):
        self.is_open = True
        self._mock_state = {
            "temperature_actual": 70,
            "temperature_set": 80, 
            "heater_on": False,
            "light_on": False,
            "ready": True,
            "uptime": 12345,
            "bathing_time": 1800
        }
        
    def read(self, size=1):
        # Return empty bytes to simulate no data most of the time
        return b''
        
    def read_until(self, terminator=b'\x9c', size=None):
        # Return empty bytes to simulate no frame data
        return b''
        
    def write(self, data):
        _LOGGER.debug("Mock serial write: %s", data.hex())
        # Simulate command processing
        if len(data) >= 8:  # Basic packet structure
            # Toggle states based on commands
            if b'\x00\x70' in data:  # COMMAND packet
                if data[-2] == 0x01:  # Heater toggle
                    self._mock_state["heater_on"] = not self._mock_state["heater_on"]
                    _LOGGER.debug("Mock: Toggled heater to %s", self._mock_state["heater_on"])
                elif data[-2] == 0x02:  # Light toggle
                    self._mock_state["light_on"] = not self._mock_state["light_on"]
                    _LOGGER.debug("Mock: Toggled light to %s", self._mock_state["light_on"])
        return len(data)
        
    @property
    def timeout(self):
        return 1.0
        
    @timeout.setter 
    def timeout(self, value):
        pass
        
    @property
    def in_waiting(self):
        return 0
        
    def flush(self):
        pass
        
    def reset_input_buffer(self):
        pass
        
    def reset_output_buffer(self):
        pass
        
    def close(self):
        self.is_open = False
        _LOGGER.debug("Mock serial closed")

# Protocol constants
COMMAND_CODES = {
    "TEMPERATURE": 0x6000,
    "STATE": 0x3400, 
    "STATE_ACK": 0x7180,
    "COMMAND": 0x7000,
    "UPTIME": 0x9400,
    "BATHING_TIME": 0x9401,
}

# Command values for 0x7000
COMMANDS = {
    "HEATER_TOGGLE": 0x00000001,
    "LIGHT_TOGGLE": 0x00000002,
}


class TyloProtocolHandler:
    """Handler for Tylö-Helo RS485 protocol communication."""

    def __init__(self, port: str, baudrate: int = 19200, mock_mode: bool = False) -> None:
        """Initialize the protocol handler."""
        self._port = port
        self._baudrate = baudrate
        self._serial: serial.Serial | None = None
        self._running = False
        self._callbacks: dict[str, Callable[[Any], None]] = {}
        self._mock_mode = mock_mode or port.lower() == "mock"
        
        # CRC calculator
        self._crc_calc = Calculator(
            Configuration(
                width=16,
                polynomial=0x90d9,
                init_value=0xffff,
                final_xor_value=0,
                reverse_input=False,
                reverse_output=False
            ),
            optimized=True
        )
        
        # Track unique CRC errors for debugging
        self._crc_error_cache = set()
        
        # Frame buffer for assembling complete frames
        self._frame_buffer = bytearray()
        
        # Current state
        self._temperature_actual: float | None = None
        self._temperature_set: float | None = None
        self._heater_on = False
        self._light_on = False
        self._ready = False
        self._uptime: int | None = None
        self._bathing_time: int | None = None

    @property
    def temperature_actual(self) -> float | None:
        """Get actual temperature."""
        return self._temperature_actual

    @property
    def temperature_set(self) -> float | None:
        """Get set temperature."""
        return self._temperature_set

    @property
    def heater_on(self) -> bool:
        """Get heater state."""
        return self._heater_on

    @property
    def light_on(self) -> bool:
        """Get light state."""
        return self._light_on

    @property
    def ready(self) -> bool:
        """Get ready state."""
        return self._ready

    @property
    def uptime(self) -> int | None:
        """Get uptime in minutes."""
        return self._uptime

    @property
    def bathing_time(self) -> int | None:
        """Get remaining bathing time in minutes."""
        return self._bathing_time

    @property
    def is_connected(self) -> bool:
        """Check if connection is active."""
        return self._serial is not None and self._serial.is_open

    def register_callback(self, event_type: str, callback: Callable[[Any], None]) -> None:
        """Register a callback for specific events."""
        self._callbacks[event_type] = callback

    def remove_callback(self, event_type: str) -> None:
        """Remove a callback."""
        self._callbacks.pop(event_type, None)

    async def connect(self) -> bool:
        """Connect to the serial port."""
        if self._mock_mode:
            _LOGGER.info("Mock mode enabled - simulating connection to %s", self._port)
            self._serial = MockSerial()
            return True
            
        try:
            self._serial = serial.Serial(
                self._port,
                self._baudrate,
                timeout=1,
                parity=serial.PARITY_EVEN
            )
            _LOGGER.info("Connected to %s at %d baud", self._port, self._baudrate)
            return True
        except Exception as err:
            _LOGGER.error("Failed to connect to %s: %s", self._port, err)
            self._serial = None
            return False

    async def disconnect(self) -> None:
        """Disconnect from the serial port."""
        self._running = False
        if self._serial and self._serial.is_open:
            self._serial.close()
            _LOGGER.info("Disconnected from %s", self._port)
        self._serial = None

    async def start_monitoring(self) -> None:
        """Start monitoring for incoming packets."""
        if not self.is_connected:
            raise RuntimeError("Not connected to serial port")
        
        self._running = True
        _LOGGER.info("Starting packet monitoring")
        
        while self._running and self.is_connected:
            try:
                if self._mock_mode:
                    # In mock mode, just sleep and don't try to read frames
                    await asyncio.sleep(1.0)
                    continue
                    
                # Read small chunks and buffer them
                try:
                    # Run small reads in executor to avoid blocking the event loop
                    loop = asyncio.get_event_loop()
                    chunk = await loop.run_in_executor(
                        None, 
                        self._serial.read,
                        16  # Read small chunks
                    )
                    
                    if len(chunk) > 0:
                        # Add to frame buffer
                        self._frame_buffer.extend(chunk)
                        _LOGGER.debug("Added %d bytes to buffer, buffer size: %d", len(chunk), len(self._frame_buffer))
                        
                        # Process any complete frames in the buffer
                        await self._process_buffer()
                    else:
                        # No data received, small sleep to prevent busy loop
                        await asyncio.sleep(0.1)
                except Exception as frame_err:
                    _LOGGER.error("Error processing frame: %s", frame_err)
                    await asyncio.sleep(0.1)
                    
            except Exception as err:
                _LOGGER.error("Error in monitoring loop: %s", err)
                await asyncio.sleep(1.0)

    async def send_command(self, command: int, data: int = 0) -> bool:
        """Send a command to the sauna controller."""
        if not self.is_connected:
            _LOGGER.error("Cannot send command: not connected")
            return False

        try:
            # Build packet: address(0x40) + type(0x07) + command + data
            packet = struct.pack(">BBHI", 0x40, 0x07, command, data)
            
            # Calculate and append CRC
            crc = self._crc_calc.checksum(packet)
            packet_with_crc = packet + struct.pack(">H", crc)
            
            # Escape and frame the packet
            frame = self._escape_packet(packet_with_crc)
            
            self._serial.write(frame)
            _LOGGER.debug("Sent command 0x%04x with data 0x%08x", command, data)
            return True
            
        except Exception as err:
            _LOGGER.error("Failed to send command: %s", err)
            return False

    async def toggle_heater(self) -> bool:
        """Toggle heater state."""
        return await self.send_command(COMMAND_CODES["COMMAND"], COMMANDS["HEATER_TOGGLE"])

    async def toggle_light(self) -> bool:
        """Toggle light state."""
        return await self.send_command(COMMAND_CODES["COMMAND"], COMMANDS["LIGHT_TOGGLE"])

    def _escape_packet(self, packet: bytes) -> bytes:
        """Escape packet data and add SOF/EOF markers."""
        escaped = bytearray([0x98])  # SOF
        
        for byte in packet:
            if byte == 0x9c:  # EOF
                escaped.extend([0x91, 0x63])
            elif byte == 0x98:  # SOF  
                escaped.extend([0x91, 0x67])
            elif byte == 0x91:  # ESC
                escaped.extend([0x91, 0x6E])
            else:
                escaped.append(byte)
        
        escaped.append(0x9c)  # EOF
        return bytes(escaped)

    async def _process_buffer(self) -> None:
        """Process the frame buffer and extract complete frames."""
        try:
            while True:
                # Look for SOF marker (0x98) in buffer
                sof_pos = self._frame_buffer.find(0x98)
                if sof_pos == -1:
                    # No SOF marker, clear buffer of any junk
                    self._frame_buffer.clear()
                    break
                
                # Remove any data before SOF
                if sof_pos > 0:
                    _LOGGER.debug("Removing %d bytes of junk before SOF", sof_pos)
                    self._frame_buffer = self._frame_buffer[sof_pos:]
                
                # Now find EOF marker (0x9c) after SOF, respecting escape sequences
                frame_end = self._find_frame_end(self._frame_buffer)
                if frame_end == -1:
                    # Incomplete frame, wait for more data
                    break
                
                # Extract complete frame
                frame = bytes(self._frame_buffer[:frame_end + 1])
                self._frame_buffer = self._frame_buffer[frame_end + 1:]
                
                _LOGGER.debug("Extracted complete frame: %s", frame.hex())
                await self._handle_frame(frame)
                
        except Exception as err:
            _LOGGER.error("Error processing buffer: %s", err)

    def _find_frame_end(self, buffer: bytearray) -> int:
        """Find the end of frame marker, respecting escape sequences."""
        i = 1  # Start after SOF
        in_escape = False
        
        while i < len(buffer):
            if in_escape:
                in_escape = False
                i += 1
            elif buffer[i] == 0x91:
                in_escape = True
                i += 1
            elif buffer[i] == 0x9c:
                return i  # Found EOF
            else:
                i += 1
        
        return -1  # EOF not found

    async def _process_raw_data(self, data: bytes) -> None:
        """Process raw data and extract individual frames."""
        try:
            # Process data to find complete frames considering escape sequences
            frames = []
            i = 0
            
            while i < len(data):
                # Look for SOF marker (0x98)
                if data[i] == 0x98:
                    # Start of frame found, now find the end
                    frame_start = i
                    i += 1
                    in_escape = False
                    
                    while i < len(data):
                        if in_escape:
                            # Skip escaped byte
                            in_escape = False
                            i += 1
                        elif data[i] == 0x91:
                            # Escape sequence
                            in_escape = True
                            i += 1
                        elif data[i] == 0x9c:
                            # End of frame found
                            frame = data[frame_start:i + 1]
                            if len(frame) >= 4:  # Minimum frame size
                                frames.append(frame)
                            i += 1
                            break
                        else:
                            i += 1
                else:
                    i += 1
            
            # Process each complete frame
            for frame in frames:
                _LOGGER.debug("Processing individual frame: %s", frame.hex())
                await self._handle_frame(frame)
                
        except Exception as err:
            _LOGGER.error("Error processing raw data: %s", err)

    async def _handle_frame(self, frame: bytes) -> None:
        """Handle received frame."""
        try:
            _LOGGER.debug("Processing frame: %s", frame.hex())
            
            packet = self._unescape_frame(frame)
            _LOGGER.debug("Unescaped packet: %s", packet.hex())
            
            if len(packet) < 2:
                _LOGGER.warning("Packet too short: %s", packet.hex())
                return
                
            if self._validate_crc(packet):
                # Temporary: log good frames too for analysis
                if len(packet) >= 2:
                    data_part = packet[:-2]
                    received_crc = int.from_bytes(packet[-2:], 'big')
                    calculated_crc = self._crc_calc.checksum(data_part)
                    _LOGGER.info("CRC validation PASSED for frame: %s (unescaped: %s) - CRC: 0x%04x", 
                               frame.hex(), packet.hex(), received_crc)
                await self._handle_packet(packet[:-2])  # Remove CRC
            else:
                # Debug CRC calculation (only log unique errors)
                if len(packet) >= 2:
                    data_part = packet[:-2]
                    received_crc = int.from_bytes(packet[-2:], 'big')
                    calculated_crc = self._crc_calc.checksum(data_part)
                    error_key = (packet.hex(), received_crc, calculated_crc)
                    if error_key not in self._crc_error_cache:
                        self._crc_error_cache.add(error_key)
                        _LOGGER.warning("CRC error in frame: %s (unescaped: %s) - received CRC: 0x%04x, calculated: 0x%04x", 
                                      frame.hex(), packet.hex(), received_crc, calculated_crc)
                else:
                    if packet.hex() not in self._crc_error_cache:
                        self._crc_error_cache.add(packet.hex())
                        _LOGGER.warning("CRC error in frame: %s (unescaped: %s) - packet too short", frame.hex(), packet.hex())
        except Exception as err:
            _LOGGER.error("Error handling frame %s: %s", frame.hex(), err)
            import traceback
            _LOGGER.error("Traceback: %s", traceback.format_exc())

    def _unescape_frame(self, frame: bytes) -> bytearray:
        """Unescape frame data."""
        packet = bytearray()
        is_escaped = False
        
        # Skip SOF and EOF markers
        for i in range(1, len(frame) - 1):
            byte = frame[i]
            if byte == 0x91:
                is_escaped = True
                continue
            elif is_escaped:
                is_escaped = False
                if byte == 0x63:
                    packet.append(0x9c)  # EOF
                elif byte == 0x67:
                    packet.append(0x98)  # SOF
                elif byte == 0x6E:
                    packet.append(0x91)  # ESC
                else:
                    _LOGGER.warning("Unknown escape sequence: 91 %02x", byte)
                    packet.extend([0x91, byte])
            else:
                packet.append(byte)
        
        return packet

    def _validate_crc(self, packet: bytearray) -> bool:
        """Validate packet CRC."""
        return self._crc_calc.checksum(packet) == 0

    async def _handle_packet(self, packet: bytearray) -> None:
        """Handle decoded packet."""
        if len(packet) < 2:
            return

        address = packet[0]
        packet_type = packet[1]
        
        # Only process packets from control to heater (07/09) or heater to control (06/08)
        if packet_type not in [0x06, 0x07, 0x08, 0x09]:
            return

        if len(packet) < 4:
            return

        code = (packet[2] << 8) | packet[3]
        data = int.from_bytes(packet[4:], 'big') if len(packet) > 4 else 0

        _LOGGER.debug("Packet: addr=0x%02x type=0x%02x code=0x%04x data=0x%08x", 
                     address, packet_type, code, data)

        await self._process_data_packet(code, data)

    async def _process_data_packet(self, code: int, data: int) -> None:
        """Process data from packet."""
        changed = False

        if code == COMMAND_CODES["TEMPERATURE"]:
            # Temperature data: bits 0-10 = actual, bits 11-20 = set point
            actual = (data & 0x7FF) / 9.0
            set_point = ((data >> 11) & 0x7FF) / 9.0
            
            if actual != self._temperature_actual or set_point != self._temperature_set:
                self._temperature_actual = actual
                self._temperature_set = set_point
                changed = True
                _LOGGER.debug("Temperature: actual=%.1f°C set=%.1f°C", actual, set_point)

        elif code == COMMAND_CODES["STATE"]:
            # State bits
            ready = (data & 0x01) != 0
            light = (data & 0x08) != 0
            heater = (data & 0x10) != 0
            
            if (ready != self._ready or light != self._light_on or heater != self._heater_on):
                self._ready = ready
                self._light_on = light
                self._heater_on = heater
                changed = True
                _LOGGER.debug("State: ready=%s light=%s heater=%s", ready, light, heater)

        elif code == COMMAND_CODES["STATE_ACK"]:
            # State acknowledgment bits (different encoding)
            light = (data & 0x020000) != 0
            heater = (data & 0x01C000) != 0
            
            if light != self._light_on or heater != self._heater_on:
                self._light_on = light
                self._heater_on = heater
                changed = True
                _LOGGER.debug("State ACK: light=%s heater=%s", light, heater)

        elif code == COMMAND_CODES["UPTIME"]:
            # Total uptime in minutes
            if data != self._uptime:
                self._uptime = data
                changed = True
                _LOGGER.debug("Uptime: %d minutes", data)

        elif code == COMMAND_CODES["BATHING_TIME"]:
            # Remaining bathing time in minutes
            if data != self._bathing_time:
                self._bathing_time = data
                changed = True
                _LOGGER.debug("Bathing time: %d minutes", data)

        # Notify callbacks if state changed
        if changed:
            for callback in self._callbacks.values():
                try:
                    callback(self)
                except Exception as err:
                    _LOGGER.error("Error in callback: %s", err)