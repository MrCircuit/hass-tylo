"""Config flow for Tylö-Helo Sauna integration."""
from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol
import serial.tools.list_ports

from homeassistant import config_entries, exceptions
from homeassistant.core import HomeAssistant
from homeassistant.const import CONF_PORT

from .const import DOMAIN
from .hub import Hub

_LOGGER = logging.getLogger(__name__)


async def get_serial_ports(hass: HomeAssistant) -> dict[str, str]:
    """Get available serial ports."""
    ports = {}
    try:
        # Run the blocking call in executor
        comports = await hass.async_add_executor_job(serial.tools.list_ports.comports)
        for port in comports:
            # Create a user-friendly description
            description = port.description
            if port.manufacturer:
                description += f" ({port.manufacturer})"
            ports[port.device] = f"{port.device} - {description}"
    except Exception as err:
        _LOGGER.error("Error discovering serial ports: %s", err)
    
    # Always add manual entry and mock options
    ports["manual"] = "Manual entry..."
    ports["mock"] = "Mock/Test mode (no hardware required)"
    
    return ports


async def validate_input(hass: HomeAssistant, data: dict) -> dict[str, Any]:
    """Validate the user input allows us to connect.

    Data has the keys from DATA_SCHEMA with values provided by the user.
    """
    port = data[CONF_PORT]
    
    # Handle manual entry case
    if port == "manual":
        if "manual_port" not in data:
            raise InvalidPort
        port = data["manual_port"]
    
    # Validate the serial port path
    if not port or not port.strip():
        raise InvalidPort
    
    # Basic validation for common port patterns
    if port.lower() != "mock" and not (port.startswith(("/dev/", "COM")) or port.startswith("\\\\.\\COM")):
        raise InvalidPort

    hub = Hub(hass, "localhost", port)  # Host not needed for serial
    
    # Test connection to the sauna controller
    result = await hub.test_connection()
    if not result:
        raise CannotConnect

    # Store the actual port used (not "manual")
    final_data = {CONF_PORT: port}
    if "manual_port" in final_data:
        del final_data["manual_port"]

    # Return info that you want to store in the config entry
    return {"title": f"Tylö Sauna ({port})", "data": final_data}


class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Tylö-Helo Sauna."""

    VERSION = 1
    
    def __init__(self):
        """Initialize the config flow."""
        self._user_input = {}

    async def async_step_user(self, user_input=None):
        """Handle the initial step."""
        errors = {}
        
        # Get available serial ports
        serial_ports = await get_serial_ports(self.hass)
        
        # Always show dropdown if we have any options (including mock/manual)
        
        data_schema = vol.Schema({
            vol.Required(CONF_PORT): vol.In(serial_ports),
        })
        
        if user_input is not None:
            # Handle manual entry selection
            if user_input.get(CONF_PORT) == "manual":
                self._user_input = {}
                return await self.async_step_manual()
            
            # Handle mock mode selection
            if user_input.get(CONF_PORT) == "mock":
                user_input[CONF_PORT] = "mock"
            
            try:
                info = await validate_input(self.hass, user_input)
                return self.async_create_entry(title=info["title"], data=info["data"])
            except CannotConnect:
                errors["base"] = "cannot_connect"
            except InvalidPort:
                errors[CONF_PORT] = "invalid_port"
            except Exception:  # pylint: disable=broad-except
                _LOGGER.exception("Unexpected exception")
                errors["base"] = "unknown"

        return self.async_show_form(
            step_id="user", data_schema=data_schema, errors=errors
        )

    async def async_step_manual(self, user_input=None):
        """Handle manual port entry."""
        errors = {}
        
        data_schema = vol.Schema({
            vol.Required("manual_port"): str,
        })
        
        if user_input is not None:
            # Combine with previous input
            combined_input = {
                **self._user_input,
                CONF_PORT: "manual",
                "manual_port": user_input["manual_port"]
            }
            
            try:
                info = await validate_input(self.hass, combined_input)
                return self.async_create_entry(title=info["title"], data=info["data"])
            except CannotConnect:
                errors["base"] = "cannot_connect"
            except InvalidPort:
                errors["manual_port"] = "invalid_port"
            except Exception:  # pylint: disable=broad-except
                _LOGGER.exception("Unexpected exception")
                errors["base"] = "unknown"


        return self.async_show_form(
            step_id="manual", data_schema=data_schema, errors=errors
        )


class CannotConnect(exceptions.HomeAssistantError):
    """Error to indicate we cannot connect."""


class InvalidPort(exceptions.HomeAssistantError):
    """Error to indicate there is an invalid serial port."""
