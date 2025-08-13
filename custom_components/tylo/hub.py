"""Hub for Tylö-Helo sauna integration."""
from __future__ import annotations

import asyncio
import logging
from typing import Callable

from homeassistant.core import HomeAssistant

from .protocol import TyloProtocolHandler

_LOGGER = logging.getLogger(__name__)


class Hub:
    """Hub for Tylö-Helo sauna integration."""

    def __init__(self, hass: HomeAssistant, host: str, port: str) -> None:
        """Initialize the hub."""
        self._hass = hass
        self._host = host
        self._port = port
        self._id = f"tylo_{host.replace('.', '_')}"
        self._callbacks: set[Callable[[], None]] = set()
        self._protocol = TyloProtocolHandler(port)
        self._monitoring_task: asyncio.Task | None = None
        
        # Register protocol callback
        self._protocol.register_callback("state_change", self._on_protocol_update)

    @property
    def hub_id(self) -> str:
        """Return hub ID."""
        return self._id

    @property
    def online(self) -> bool:
        """Return if hub is online."""
        return self._protocol.is_connected

    @property
    def heater_on(self) -> bool:
        """Return if heater is on."""
        return self._protocol.heater_on

    @property
    def light_on(self) -> bool:
        """Return if light is on."""
        return self._protocol.light_on

    @property
    def ready(self) -> bool:
        """Return if sauna is ready."""
        return self._protocol.ready

    @property
    def temperature_actual(self) -> float | None:
        """Return actual temperature."""
        return self._protocol.temperature_actual

    @property
    def temperature_set(self) -> float | None:
        """Return set temperature."""
        return self._protocol.temperature_set

    @property
    def bathing_time(self) -> int | None:
        """Return remaining bathing time in minutes."""
        return self._protocol.bathing_time

    @property
    def uptime(self) -> int | None:
        """Return uptime in minutes."""
        return self._protocol.uptime

    async def test_connection(self) -> bool:
        """Test connectivity to the sauna controller."""
        try:
            _LOGGER.debug("Testing connection to %s on %s", self._host, self._port)
            success = await self._protocol.connect()
            if success:
                # Start monitoring in background
                self._monitoring_task = self._hass.async_create_task(
                    self._protocol.start_monitoring()
                )
                _LOGGER.info("Successfully connected and started monitoring")
            return success
        except Exception as err:
            _LOGGER.error("Connection test failed: %s", err)
            return False

    async def set_heater(self, state: bool) -> None:
        """Toggle heater state."""
        if not self.online:
            _LOGGER.error("Cannot set heater: not connected")
            return
        
        # Only toggle if state is different
        if state != self.heater_on:
            _LOGGER.debug("Toggling heater (current: %s, target: %s)", self.heater_on, state)
            await self._protocol.toggle_heater()

    async def set_light(self, state: bool) -> None:
        """Toggle light state."""
        if not self.online:
            _LOGGER.error("Cannot set light: not connected")
            return
        
        # Only toggle if state is different
        if state != self.light_on:
            _LOGGER.debug("Toggling light (current: %s, target: %s)", self.light_on, state)
            await self._protocol.toggle_light()

    def register_callback(self, callback: Callable[[], None]) -> None:
        """Register callback for state changes."""
        self._callbacks.add(callback)

    def remove_callback(self, callback: Callable[[], None]) -> None:
        """Remove previously registered callback."""
        self._callbacks.discard(callback)

    def _on_protocol_update(self, protocol: TyloProtocolHandler) -> None:
        """Handle protocol state updates."""
        _LOGGER.debug("Protocol state updated, notifying %d callbacks", len(self._callbacks))
        self._publish_updates()

    def _publish_updates(self) -> None:
        """Notify all registered callbacks of state changes."""
        for callback in self._callbacks:
            try:
                callback()
            except Exception as err:
                _LOGGER.error("Error in callback: %s", err)

    async def async_close(self) -> None:
        """Close the hub connection."""
        _LOGGER.debug("Closing hub connection")
        
        # Cancel monitoring task
        if self._monitoring_task and not self._monitoring_task.done():
            self._monitoring_task.cancel()
            try:
                await self._monitoring_task
            except asyncio.CancelledError:
                pass
        
        # Disconnect protocol
        await self._protocol.disconnect()
        _LOGGER.debug("Hub connection closed")


