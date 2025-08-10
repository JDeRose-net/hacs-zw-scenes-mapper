from __future__ import annotations

import logging
from typing import Any, Dict, List

import voluptuous as vol
import yaml

from homeassistant.const import EVENT_HOMEASSISTANT_STARTED
from homeassistant.core import HomeAssistant, Event, ServiceCall, callback
import homeassistant.helpers.config_validation as cv
from homeassistant.helpers import discovery

from .const import (
    DOMAIN,
    CONF_FILE,
    CONF_DEBOUNCE_MS,
    DEFAULT_FILE,
    DEFAULT_DEBOUNCE_MS,
    EVENT_MAPPINGS_UPDATED,
    ATTR_DATA,
    EVENT_TYPE,
    SCENE_ACTIVATION_CC,
)

_LOGGER = logging.getLogger(__name__)

CONFIG_SCHEMA = vol.Schema(
    {
        DOMAIN: vol.Schema(
            {
                vol.Optional(CONF_FILE, default=DEFAULT_FILE): cv.string,
                vol.Optional(CONF_DEBOUNCE_MS, default=DEFAULT_DEBOUNCE_MS): vol.Coerce(int),
            }
        )
    },
    extra=vol.ALLOW_EXTRA,
)

# Simple in-memory state
class Zw2HaState:
    def __init__(self, file_path: str, debounce_ms: int) -> None:
        self.file_path = file_path
        self.debounce_ms = debounce_ms
        self.map_norm: Dict[str, List[str]] = {}   # key -> list of entity_ids (with domain)
        self.map_attr: Dict[str, str] = {}         # key -> comma string of bare slugs (for sensor attr compat)
        self._last_fire: Dict[str, float] = {}     # key -> monotonic ts

    def has(self, key: str) -> bool:
        return key in self.map_norm

    def get_targets(self, key: str) -> List[str]:
        return self.map_norm.get(key, [])

async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    conf = config.get(DOMAIN, {})
    file_path = conf.get(CONF_FILE, DEFAULT_FILE)
    debounce_ms = int(conf.get(CONF_DEBOUNCE_MS, DEFAULT_DEBOUNCE_MS))

    state = Zw2HaState(file_path, debounce_ms)
    hass.data[DOMAIN] = state

    async def _load_mappings() -> None:
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                raw = yaml.safe_load(f) or {}
        except FileNotFoundError:
            _LOGGER.warning("zw2ha: mappings file not found at %s; starting with empty map", file_path)
            raw = {}
        except Exception as e:
            _LOGGER.exception("zw2ha: failed to load mappings from %s: %s", file_path, e)
            raw = {}

        norm: Dict[str, List[str]] = {}
        attr: Dict[str, str] = {}

        def _normalize_value(v: Any) -> List[str]:
            if isinstance(v, list):
                items = [str(x).strip() for x in v]
            elif isinstance(v, str):
                items = [p.strip() for p in v.split(",") if p.strip()]
            else:
                items = []
            # Auto-prefix scene. if no domain given
            result = [i if "." in i else f"scene.{i}" for i in items]
            # Deduplicate preserving order
            seen = set()
            out: List[str] = []
            for i in result:
                if i not in seen:
                    out.append(i)
                    seen.add(i)
            return out

        for k, v in (raw or {}).items():
            key = str(k).strip()
            targets = _normalize_value(v)
            norm[key] = targets
            # Build compat attribute string of bare slugs (no domain)
            bare = []
            for ent in targets:
                bare.append(ent.split(".", 1)[1] if "." in ent else ent)
            attr[key] = ",".join(bare)

        state.map_norm = norm
        state.map_attr = attr
        _LOGGER.info("zw2ha: loaded %d mapping(s) from %s", len(norm), file_path)
        hass.bus.async_fire(EVENT_MAPPINGS_UPDATED, {"count": len(norm), "file": file_path})

    async def _handle_reload(call: ServiceCall) -> None:
        await _load_mappings()

    async def _handle_trigger(call: ServiceCall) -> None:
        zw_network = str(call.data.get("zw_network"))
        zw_scene = int(call.data.get("zw_scene"))
        await _maybe_fire(f"{zw_network}-{zw_scene}")

    @callback
    def _debounced(key: str) -> bool:
        # Return True if allowed (not debounced)
        import time
        now = time.monotonic()
        last = state._last_fire.get(key, 0.0)
        if (now - last) * 1000.0 < state.debounce_ms:
            return False
        state._last_fire[key] = now
        return True

    async def _maybe_fire(key: str) -> None:
        if not state.has(key):
            _LOGGER.warning("zw2ha: no scenes mapped for key '%s'", key)
            return
        if not _debounced(key):
            _LOGGER.debug("zw2ha: debounced key '%s'", key)
            return

        entity_ids = state.get_targets(key)
        if not entity_ids:
            _LOGGER.debug("zw2ha: key '%s' mapped to empty list", key)
            return

        _LOGGER.info("zw2ha: activating %s for key '%s'", entity_ids, key)
        await hass.services.async_call(
            "scene", "turn_on", {"entity_id": entity_ids}, blocking=False
        )

    @callback
    def _event_listener(event: Event) -> None:
        data = event.data or {}
        if data.get("command_class") != SCENE_ACTIVATION_CC:
            return
        home_id = data.get("home_id")
        value = data.get("value")
        if home_id is None or value is None:
            return
        try:
            key = f"{int(home_id)}-{int(value)}"
        except (ValueError, TypeError):
            return
        hass.async_create_task(_maybe_fire(key))

    # Register services
    hass.services.async_register(DOMAIN, "reload", _handle_reload)
    hass.services.async_register(
        DOMAIN,
        "trigger",
        _handle_trigger,
        schema=vol.Schema({"zw_network": cv.string, "zw_scene": vol.Coerce(int)}),
    )

    # Load platforms (sensor/button)
    hass.async_create_task(discovery.async_load_platform(hass, "sensor", DOMAIN, {}, config))
    hass.async_create_task(discovery.async_load_platform(hass, "button", DOMAIN, {}, config))

    # Load mappings now and also (re)on startup
    async def _startup_loader(_: Event) -> None:
        await _load_mappings()

    hass.bus.async_listen_once(EVENT_HOMEASSISTANT_STARTED, _startup_loader)
    await _load_mappings()

    # Subscribe to Z-Wave JS events
    hass.bus.async_listen(EVENT_TYPE, _event_listener)

    return True
