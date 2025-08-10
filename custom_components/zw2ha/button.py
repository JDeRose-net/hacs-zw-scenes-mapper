from __future__ import annotations

from homeassistant.components.button import ButtonEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.typing import ConfigType, DiscoveryInfoType
from homeassistant.helpers.entity import DeviceInfo

from .const import DOMAIN

async def async_setup_platform(
    hass: HomeAssistant,
    config: ConfigType,
    async_add_entities,
    discovery_info: DiscoveryInfoType | None = None,
) -> None:
    async_add_entities([Zw2HaReloadButton(hass)], update_before_add=False)

class Zw2HaReloadButton(ButtonEntity):
    _attr_has_entity_name = True
    _attr_name = "ZW2HA Reload"
    _attr_icon = "mdi:reload"

    def __init__(self, hass: HomeAssistant) -> None:
        self._hass = hass
        self._attr_unique_id = "zw2ha_reload_button"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, "zw2ha")},
            name="ZW2HA",
            manufacturer="zw2ha",
            model="Scene Mapper",
        )

    async def async_press(self) -> None:
        await self._hass.services.async_call("zw2ha", "reload", blocking=True)
