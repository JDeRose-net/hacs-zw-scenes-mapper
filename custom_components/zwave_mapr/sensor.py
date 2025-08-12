from __future__ import annotations
from typing import Any, Optional

from homeassistant.components.sensor import SensorEntity
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.typing import ConfigType, DiscoveryInfoType
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.loader import async_get_integration

from .const import DOMAIN, EVENT_MAPPINGS_UPDATED, ATTR_DATA


async def async_setup_platform(
    hass: HomeAssistant,
    config: ConfigType,
    async_add_entities,
    discovery_info: DiscoveryInfoType | None = None,
) -> None:
    state = hass.data[DOMAIN]

    # pull integration version for display on the Device card (nice touch)
    try:
        integration = await async_get_integration(hass, DOMAIN)
        sw_version: Optional[str] = getattr(integration, "version", None)
    except Exception:
        sw_version = None

    async_add_entities([MapSensor(hass, state, sw_version)], update_before_add=False)


class MapSensor(SensorEntity):
    _attr_has_entity_name = True
    _attr_name = "Z-Wave Mapr Map"
    _attr_icon = "mdi:link-variant"
    _attr_should_poll = False
    _attr_native_value = "loaded"

    def __init__(self, hass: HomeAssistant, state, sw_version: Optional[str]) -> None:
        self.hass = hass
        self._state = state

        # Stable identifiers
        self._attr_unique_id = "zwave_mapr_map"
        self.entity_id = "sensor.zwave_mapr_map"  # ← force exact entity_id

        # Device card metadata
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, DOMAIN)},
            name="Z-Wave Scenes Mapr",
            manufacturer="JDeRose.net",
            model="hacs-zwave-mapr",
            configuration_url="https://github.com/jderose-net/hacs-zwave-mapr",
            sw_version=sw_version,
        )

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        return {
            ATTR_DATA: self._state.map_attr,
            "count": len(self._state.map_attr),
            "file": self._state.file_path,
            "debounce_ms": self._state.debounce_ms,
            "last_loaded": getattr(self._state, "last_loaded", None),
            "file_mtime": getattr(self._state, "file_mtime", None),
        }

    async def async_added_to_hass(self) -> None:
        @callback
        def _updated(_event):
            self.async_write_ha_state()
        self.hass.bus.async_listen(EVENT_MAPPINGS_UPDATED, _updated)

