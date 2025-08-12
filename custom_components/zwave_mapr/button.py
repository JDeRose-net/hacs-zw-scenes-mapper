from __future__ import annotations
from typing import Optional

from homeassistant.components.button import ButtonEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.typing import ConfigType, DiscoveryInfoType
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.loader import async_get_integration

from .const import DOMAIN


async def async_setup_platform(
    hass: HomeAssistant,
    config: ConfigType,
    async_add_entities,
    discovery_info: DiscoveryInfoType | None = None,
) -> None:
    # pull integration version for display on the Device card (nice touch)
    try:
        integration = await async_get_integration(hass, DOMAIN)
        sw_version: Optional[str] = getattr(integration, "version", None)
    except Exception:
        sw_version = None

    async_add_entities([ReloadButton(hass, sw_version)], update_before_add=False)


class ReloadButton(ButtonEntity):
    _attr_has_entity_name = True
    _attr_name = "Z-Wave Mapr Reload"
    _attr_icon = "mdi:reload"

    def __init__(self, hass: HomeAssistant, sw_version: Optional[str]) -> None:
        self._hass = hass
        self._attr_unique_id = "zwave_mapr_reload"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, DOMAIN)},
            name="ZWave Mapr",
            manufacturer="JDeRose.net",
            model="hacs-zwave-mapr",
            configuration_url="https://github.com/jderose-net/hacs-zwave-mapr",
            sw_version=sw_version,
        )

    async def async_press(self) -> None:
        await self._hass.services.async_call(DOMAIN, "reload", blocking=True)

