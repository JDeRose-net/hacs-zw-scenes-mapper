from __future__ import annotations
from typing import Any

from homeassistant.components.sensor import SensorEntity
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.typing import ConfigType, DiscoveryInfoType
from homeassistant.helpers.entity import DeviceInfo

from .const import DOMAIN, EVENT_MAPPINGS_UPDATED, ATTR_DATA

async def async_setup_platform(
    hass: HomeAssistant,
    config: ConfigType,
    async_add_entities,
    discovery_info: DiscoveryInfoType | None = None,
) -> None:
    state = hass.data[DOMAIN]
    async_add_entities([Zw2HaMapSensor(hass, state)], update_before_add=False)

class Zw2HaMapSensor(SensorEntity):
    _attr_has_entity_name = True
    _attr_name = "Z-Wave to HA Scene Map"
    _attr_icon = "mdi:link-variant"
    _attr_should_poll = False
    _attr_native_value = "loaded"

    def __init__(self, hass: HomeAssistant, state) -> None:
        self.hass = hass
        self._state = state
        self._attr_unique_id = "zw2ha_map_sensor"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, "zw2ha")},
            name="ZW2HA",
            manufacturer="zw2ha",
            model="Scene Mapper",
        )

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        # Keep a 'data' attribute compatible with the example script
        return {
            ATTR_DATA: self._state.map_attr,
            "count": len(self._state.map_attr),
            "file": self._state.file_path,
            "debounce_ms": self._state.debounce_ms,
        }

    async def async_added_to_hass(self) -> None:
        @callback
        def _updated(_event):
            self.async_write_ha_state()
        self.hass.bus.async_listen(EVENT_MAPPINGS_UPDATED, _updated)
