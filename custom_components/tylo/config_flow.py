"""Config flow for Tylö-Helo Sauna integration."""
from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol
import serial.tools.list_ports

from homeassistant import config_entries, exceptions
from homeassistant.core import HomeAssistant
from homeassistant.const import CONF_HOST, CONF_PORT

from .const import DOMAIN
from .hub import Hub

_LOGGER = logging.getLogger(__name__)


def get_serial_ports() -> dict[str, str]:
    """Get available serial ports."""
    ports = {}
    try:
        for port in serial.tools.list_ports.comports():
            # Create a user-friendly description
            description = port.description
            if port.manufacturer:
                description += f" ({port.manufacturer})"
            ports[port.device] = f"{port.device} - {description}"
    except Exception as err:
        _LOGGER.error("Error discovering serial ports: %s", err)
    
    # Always add manual entry option
    ports["manual"] = "Manual entry..."
    
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
    if not (port.startswith(("/dev/", "COM")) or port.startswith("\\\\.\\COM")):
        raise InvalidPort

    hub = Hub(hass, data[CONF_HOST], port)
    
    # Test connection to the sauna controller
    result = await hub.test_connection()
    if not result:
        raise CannotConnect

    # Store the actual port used (not "manual")
    final_data = {**data, CONF_PORT: port}
    if "manual_port" in final_data:
        del final_data["manual_port"]

    # Return info that you want to store in the config entry
    return {"title": f"Tylö Sauna ({data[CONF_HOST]})", "data": final_data}


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
        serial_ports = get_serial_ports()
        
        # If no ports found, only show manual entry
        if not serial_ports or serial_ports == {"manual": "Manual entry..."}:
            return await self.async_step_manual()
        
        data_schema = vol.Schema({
            vol.Required(CONF_HOST): str,
            vol.Required(CONF_PORT): vol.In(serial_ports),
        })
        
        if user_input is not None:
            # Handle manual entry selection
            if user_input.get(CONF_PORT) == "manual":
                self._user_input = {CONF_HOST: user_input[CONF_HOST]}
                return await self.async_step_manual()
            
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
        
        # Pre-fill host if we came from the first step
        if self._user_input and CONF_HOST not in self._user_input and user_input:
            self._user_input[CONF_HOST] = user_input.get(CONF_HOST, "")
        
        if user_input is not None:
            # Combine with previous input
            combined_input = {
                **self._user_input,
                CONF_PORT: "manual",
                "manual_port": user_input["manual_port"]
            }
            
            # If host is missing, add it to the schema
            if CONF_HOST not in combined_input:
                data_schema = vol.Schema({
                    vol.Required(CONF_HOST): str,
                    vol.Required("manual_port"): str,
                })
                if CONF_HOST in user_input:
                    combined_input[CONF_HOST] = user_input[CONF_HOST]
            
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

        # Add host field if not already provided
        if not self._user_input or CONF_HOST not in self._user_input:
            data_schema = vol.Schema({
                vol.Required(CONF_HOST): str,
                vol.Required("manual_port"): str,
            })

        return self.async_show_form(
            step_id="manual", data_schema=data_schema, errors=errors
        )


class CannotConnect(exceptions.HomeAssistantError):
    """Error to indicate we cannot connect."""


class InvalidPort(exceptions.HomeAssistantError):
    """Error to indicate there is an invalid serial port."""
