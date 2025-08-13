"""Platform for sensor integration."""
from __future__ import annotations

from homeassistant.components.sensor import (
    SensorEntity,
    SensorDeviceClass,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfTemperature, UnitOfTime
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import (
    DOMAIN,
    ENTITY_TEMPERATURE_ACTUAL,
    ENTITY_TEMPERATURE_SET,
    ENTITY_BATHING_TIME,
    ENTITY_UPTIME,
)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Add sensors for passed config_entry in HA."""
    hub = hass.data[DOMAIN][config_entry.entry_id]

    entities = [
        TyloTemperatureActualSensor(hub),
        TyloTemperatureSetSensor(hub),
        TyloBathingTimeSensor(hub),
        TyloUptimeSensor(hub),
    ]
    async_add_entities(entities)


class TyloSensorBase(SensorEntity):
    """Base class for Tylö sensors."""

    _attr_has_entity_name = True
    _attr_should_poll = False

    def __init__(self, hub, entity_name: str) -> None:
        """Initialize the sensor."""
        self._hub = hub
        self._attr_unique_id = f"{hub.hub_id}_{entity_name}"
        self._attr_name = entity_name.replace("_", " ").title()

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

    async def async_added_to_hass(self) -> None:
        """Entity added to hass."""
        self._hub.register_callback(self.async_write_ha_state)

    async def async_will_remove_from_hass(self) -> None:
        """Entity removed from hass."""
        self._hub.remove_callback(self.async_write_ha_state)


class TyloTemperatureActualSensor(TyloSensorBase):
    """Actual temperature sensor."""

    _attr_device_class = SensorDeviceClass.TEMPERATURE
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_native_unit_of_measurement = UnitOfTemperature.CELSIUS

    def __init__(self, hub) -> None:
        """Initialize the sensor."""
        super().__init__(hub, ENTITY_TEMPERATURE_ACTUAL)

    @property
    def native_value(self) -> float | None:
        """Return the native value of the sensor."""
        return self._hub.temperature_actual


class TyloTemperatureSetSensor(TyloSensorBase):
    """Set temperature sensor."""

    _attr_device_class = SensorDeviceClass.TEMPERATURE
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_native_unit_of_measurement = UnitOfTemperature.CELSIUS

    def __init__(self, hub) -> None:
        """Initialize the sensor."""
        super().__init__(hub, ENTITY_TEMPERATURE_SET)

    @property
    def native_value(self) -> float | None:
        """Return the native value of the sensor."""
        return self._hub.temperature_set


class TyloBathingTimeSensor(TyloSensorBase):
    """Bathing time sensor."""

    _attr_device_class = SensorDeviceClass.DURATION
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_native_unit_of_measurement = UnitOfTime.MINUTES

    def __init__(self, hub) -> None:
        """Initialize the sensor."""
        super().__init__(hub, ENTITY_BATHING_TIME)

    @property
    def native_value(self) -> int | None:
        """Return the native value of the sensor."""
        return self._hub.bathing_time


class TyloUptimeSensor(TyloSensorBase):
    """Uptime sensor."""

    _attr_device_class = SensorDeviceClass.DURATION
    _attr_state_class = SensorStateClass.TOTAL_INCREASING
    _attr_native_unit_of_measurement = UnitOfTime.MINUTES

    def __init__(self, hub) -> None:
        """Initialize the sensor."""
        super().__init__(hub, ENTITY_UPTIME)

    @property
    def native_value(self) -> int | None:
        """Return the native value of the sensor."""
        return self._hub.uptime
