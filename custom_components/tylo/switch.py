"""Platform for switch integration."""
from __future__ import annotations

from typing import Any

from homeassistant.components.switch import SwitchEntity, SwitchDeviceClass
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN, ENTITY_HEATER, ENTITY_LIGHT


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Add switches for passed config_entry in HA."""
    hub = hass.data[DOMAIN][config_entry.entry_id]

    entities = [
        TyloHeaterSwitch(hub),
        TyloLightSwitch(hub),
    ]
    async_add_entities(entities)


class TyloSwitchBase(SwitchEntity):
    """Base class for Tylö switches."""
    
    _attr_has_entity_name = True
    _attr_should_poll = False

    def __init__(self, hub, entity_name: str) -> None:
        """Initialize the switch."""
        self._hub = hub
        self._attr_unique_id = f"{hub.hub_id}_{entity_name}"
        self._attr_name = entity_name.replace("_", " ").title()

    @property
    def device_info(self) -> DeviceInfo:
        """Return device information."""
        return DeviceInfo(
            identifiers={(DOMAIN, self._hub.hub_id)},
            name="Tylö Sauna",
            manufacturer="Tylö-Helo",
            model="RS485 Controller",
            sw_version="1.0",
        )

    @property
    def available(self) -> bool:
        """Return True if entity is available."""
        return self._hub.online

    async def async_added_to_hass(self) -> None:
        """Entity added to hass."""
        self._hub.register_callback(self.async_write_ha_state)

    async def async_will_remove_from_hass(self) -> None:
        """Entity removed from hass."""
        self._hub.remove_callback(self.async_write_ha_state)


class TyloHeaterSwitch(TyloSwitchBase):
    """Heater switch for Tylö sauna."""

    _attr_device_class = SwitchDeviceClass.SWITCH
    _attr_icon = "mdi:heat-wave"

    def __init__(self, hub) -> None:
        """Initialize the heater switch."""
        super().__init__(hub, ENTITY_HEATER)

    @property
    def is_on(self) -> bool:
        """Return if the heater is on."""
        return self._hub.heater_on

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn heater on."""
        await self._hub.set_heater(True)

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn heater off."""
        await self._hub.set_heater(False)


class TyloLightSwitch(TyloSwitchBase):
    """Light switch for Tylö sauna."""

    _attr_device_class = SwitchDeviceClass.SWITCH
    _attr_icon = "mdi:lightbulb"

    def __init__(self, hub) -> None:
        """Initialize the light switch."""
        super().__init__(hub, ENTITY_LIGHT)

    @property
    def is_on(self) -> bool:
        """Return if the light is on."""
        return self._hub.light_on

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn light on."""
        await self._hub.set_light(True)

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn light off."""
        await self._hub.set_light(False)
