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

    def __init__(self, port: str, baudrate: int = 19200) -> None:
        """Initialize the protocol handler."""
        self._port = port
        self._baudrate = baudrate
        self._serial: serial.Serial | None = None
        self._running = False
        self._callbacks: dict[str, Callable[[Any], None]] = {}
        
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
                # Read until EOF marker
                frame = self._serial.read_until(bytes.fromhex('9c'))
                if len(frame) > 0 and frame[0] == 0x98:  # SOF marker
                    await self._handle_frame(frame)
            except Exception as err:
                _LOGGER.error("Error reading frame: %s", err)
                await asyncio.sleep(0.1)

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

    async def _handle_frame(self, frame: bytes) -> None:
        """Handle received frame."""
        try:
            packet = self._unescape_frame(frame)
            if self._validate_crc(packet):
                await self._handle_packet(packet[:-2])  # Remove CRC
            else:
                _LOGGER.warning("CRC error in frame: %s", frame.hex())
        except Exception as err:
            _LOGGER.error("Error handling frame: %s", err)

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