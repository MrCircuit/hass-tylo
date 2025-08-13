"""Platform for binary sensor integration."""
from __future__ import annotations

from homeassistant.components.binary_sensor import (
    BinarySensorEntity,
    BinarySensorDeviceClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN, ENTITY_READY


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Add binary sensors for passed config_entry in HA."""
    hub = hass.data[DOMAIN][config_entry.entry_id]

    entities = [
        TyloReadySensor(hub),
    ]
    async_add_entities(entities)


class TyloReadySensor(BinarySensorEntity):
    """Ready state binary sensor for Tylö sauna."""

    _attr_has_entity_name = True
    _attr_should_poll = False
    _attr_device_class = BinarySensorDeviceClass.RUNNING
    _attr_icon = "mdi:thermometer-check"

    def __init__(self, hub) -> None:
        """Initialize the sensor."""
        self._hub = hub
        self._attr_unique_id = f"{hub.hub_id}_{ENTITY_READY}"
        self._attr_name = ENTITY_READY.replace("_", " ").title()

    @property
    def device_info(self) -> DeviceInfo:
        """Return device information."""
        return DeviceInfo(
            identifiers={(DOMAIN, self._hub.hub_id)},
        )

    @property
    def available(self) -> bool:
        """Return True if entity is available."""
        return self._hub.online

    @property
    def is_on(self) -> bool:
        """Return true if the sauna is ready."""
        return self._hub.ready

    async def async_added_to_hass(self) -> None:
        """Entity added to hass."""
        self._hub.register_callback(self.async_write_ha_state)

    async def async_will_remove_from_hass(self) -> None:
        """Entity removed from hass."""
        self._hub.remove_callback(self.async_write_ha_state)