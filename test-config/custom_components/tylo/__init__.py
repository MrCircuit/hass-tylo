"""The Tylö-Helo Sauna integration."""
from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_PORT, Platform
from homeassistant.core import HomeAssistant

from .const import DOMAIN
from .hub import Hub

PLATFORMS: list[Platform] = [Platform.SWITCH, Platform.SENSOR, Platform.BINARY_SENSOR]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Tylö-Helo Sauna from a config entry."""
    port = entry.data[CONF_PORT]
    
    hub = Hub(hass, "localhost", port)  # Host not needed for serial
    
    # Initialize the hub connection
    if not await hub.initialize():
        return False
    
    # Store the hub instance
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = hub
    
    # Set up platforms
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    
    if unload_ok:
        hub = hass.data[DOMAIN].pop(entry.entry_id)
        await hub.async_close()

    return unload_ok
