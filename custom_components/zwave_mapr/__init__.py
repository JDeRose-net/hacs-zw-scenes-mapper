from __future__ import annotations

import os
import asyncio
import logging
import shutil
from typing import Any, Dict, List

import voluptuous as vol
import yaml

from homeassistant.const import EVENT_HOMEASSISTANT_STARTED
from homeassistant.core import HomeAssistant, CoreState, Event, ServiceCall, callback
import homeassistant.helpers.config_validation as cv
from homeassistant.helpers import discovery
from homeassistant.util import dt as dt_util

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

DOMAIN_SERVICE_MAP: dict[str, tuple[str, str]] = {
    "scene": ("scene", "turn_on"),
    "script": ("script", "turn_on"),
    "automation": ("automation", "trigger"),
    "button": ("button", "press"),
}

CONFIG_SCHEMA = vol.Schema(
    {
        DOMAIN: vol.Schema(
            {
                vol.Optional(CONF_FILE): cv.string,
                vol.Optional(CONF_DEBOUNCE_MS, default=DEFAULT_DEBOUNCE_MS): vol.Coerce(int),
            }
        )
    },
    extra=vol.ALLOW_EXTRA,
)

class MaprState:
    def __init__(self, file_path: str, debounce_ms: int) -> None:
        self.file_path = file_path
        self.debounce_ms = debounce_ms
        self.map_norm: Dict[str, List[str]] = {}   # key -> list of entity_ids (domain-qualified)
        self.map_attr: Dict[str, str] = {}         # key -> comma string of full entity_ids
        self._last_fire: Dict[str, float] = {}     # key -> monotonic ts
        self.last_loaded: str | None = None        # ISO8601 UTC time the YAML was last loaded
        self.file_mtime: str | None = None         # ISO8601 UTC file modification time

    def has(self, key: str) -> bool:
        return key in self.map_norm

    def get_targets(self, key: str) -> List[str]:
        return self.map_norm.get(key, [])

# blocking helpers for executor
def _read_yaml_file(path: str) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}

def _mkdirs(path: str) -> None:
    os.makedirs(path, exist_ok=True)

def _copy_file(src: str, dst: str) -> None:
    shutil.copyfile(src, dst)

def _write_text(path: str, text: str) -> None:
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)

async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    conf = config.get(DOMAIN, {})
    raw_path = conf.get(CONF_FILE)  # may be None

    component_dir = os.path.dirname(__file__)

    # resolve configured path
    if raw_path:
        if isinstance(raw_path, str) and raw_path.startswith("component:"):
            rel = raw_path.split("component:", 1)[1].lstrip("/\\")
            file_path = os.path.join(component_dir, rel)
        elif os.path.isabs(raw_path):
            file_path = raw_path
        else:
            file_path = hass.config.path(raw_path)
    else:
        # default is under /config/etc/zwave_mapr/mappings.yaml
        file_path = hass.config.path(DEFAULT_FILE)

    # bootstrap: if using the default path and file is missing, pre-create it
    default_cfg_path = hass.config.path(DEFAULT_FILE)
    if not os.path.exists(file_path) and os.path.normpath(file_path) == os.path.normpath(default_cfg_path):
        try:
            await hass.async_add_executor_job(_mkdirs, os.path.dirname(file_path))
            component_example = os.path.join(component_dir, "mappings.yaml")
            if os.path.exists(component_example):
                await hass.async_add_executor_job(_copy_file, component_example, file_path)
                _LOGGER.info("%s: created default mapping at %s from component example", DOMAIN, file_path)
            else:
                await hass.async_add_executor_job(_write_text, file_path, "{}\n")
                _LOGGER.info("%s: created empty mapping at %s", DOMAIN, file_path)
        except Exception as e:
            _LOGGER.warning("%s: unable to create default mapping at %s: %s", DOMAIN, file_path, e)

    debounce_ms = int(conf.get(CONF_DEBOUNCE_MS, DEFAULT_DEBOUNCE_MS))

    state = MaprState(file_path, debounce_ms)
    hass.data[DOMAIN] = state

    async def _load_mappings() -> None:
        try:
            raw = await hass.async_add_executor_job(_read_yaml_file, state.file_path)
        except FileNotFoundError:
            _LOGGER.warning("%s: mappings file not found at %s; starting with empty map", DOMAIN, state.file_path)
            raw = {}
        except Exception as e:
            _LOGGER.exception("%s: failed to load mappings from %s: %s", DOMAIN, state.file_path, e)
            raw = {}

        norm: Dict[str, List[str]] = {}
        attr: Dict[str, str] = {}

        def _normalize_list(v: Any) -> List[str]:
            # accept list or comma-separated string; require domain-qualified entity_ids
            if isinstance(v, list):
                items = [str(x).strip() for x in v]
            elif isinstance(v, str):
                items = [p.strip() for p in v.split(",") if p.strip()]
            else:
                items = []

            out: List[str] = []
            seen: set[str] = set()
            for token in items:
                if "." not in token:
                    _LOGGER.warning("%s: ignoring unmapped/bare token '%s' (must be domain.entity_id)", DOMAIN, token)
                    continue
                if token in seen:
                    continue
                out.append(token)
                seen.add(token)
            return out

        for k, v in (raw or {}).items():
            key = str(k).strip()
            targets = _normalize_list(v)
            if targets:
                norm[key] = targets
                attr[key] = ",".join(targets)

        state.map_norm = norm
        state.map_attr = attr

        # timestamp attributes
        loaded_at = dt_util.utcnow().isoformat().replace("+00:00", "Z")
        state.last_loaded = loaded_at
        try:
            mtime = os.path.getmtime(state.file_path)
            state.file_mtime = dt_util.utc_from_timestamp(mtime).isoformat().replace("+00:00", "Z")
        except OSError:
            state.file_mtime = None

        _LOGGER.info("%s: loaded %d mapping(s) from %s at %s", DOMAIN, len(norm), state.file_path, loaded_at)
        hass.bus.async_fire(
            EVENT_MAPPINGS_UPDATED,
            {"count": len(norm), "file": state.file_path, "loaded_at": loaded_at},
        )

    async def _handle_reload(call: ServiceCall) -> None:
        await _load_mappings()

    async def _handle_trigger(call: ServiceCall) -> None:
        zw_network = str(call.data.get("zw_network"))
        zw_scene = int(call.data.get("zw_scene"))
        await _maybe_fire(f"{zw_network}-{zw_scene}")

    @callback
    def _debounced(key: str) -> bool:
        import time
        now = time.monotonic()
        last = state._last_fire.get(key, 0.0)
        if (now - last) * 1000.0 < state.debounce_ms:
            return False
        state._last_fire[key] = now
        return True

    async def _call_entity(entity_id: str) -> None:
        dom = entity_id.split(".", 1)[0]
        domain, service = DOMAIN_SERVICE_MAP.get(dom, ("homeassistant", "turn_on"))
        await hass.services.async_call(domain, service, {"entity_id": entity_id}, blocking=False)

    async def _maybe_fire(key: str) -> None:
        if not state.has(key):
            _LOGGER.warning("%s: no targets mapped for key '%s'", DOMAIN, key)
            return
        if not _debounced(key):
            _LOGGER.debug("%s: debounced key '%s'", DOMAIN, key)
            return

        entity_ids = state.get_targets(key)
        if not entity_ids:
            _LOGGER.debug("%s: key '%s' mapped to empty list", DOMAIN, key)
            return

        _LOGGER.info("%s: activating %s for key '%s'", DOMAIN, entity_ids, key)
        await asyncio.gather(*[_call_entity(e) for e in entity_ids], return_exceptions=True)

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

    # register services
    hass.services.async_register(DOMAIN, "reload", _handle_reload)
    hass.services.async_register(
        DOMAIN,
        "trigger",
        _handle_trigger,
        schema=vol.Schema({"zw_network": cv.string, "zw_scene": vol.Coerce(int)}),
    )

    # load platforms (sensor/button)
    hass.async_create_task(discovery.async_load_platform(hass, "sensor", DOMAIN, {}, config))
    hass.async_create_task(discovery.async_load_platform(hass, "button", DOMAIN, {}, config))

    # subscribe to Z-Wave JS events
    hass.bus.async_listen(EVENT_TYPE, _event_listener)

    # load mappings once, depending on HA core state
    if hass.state == CoreState.running:
        # integration set up while HA is already running (e.g., reloaded/installed)
        await _load_mappings()
    else:
        # normal boot: load once when HA is fully started
        async def _startup_loader(_: Event) -> None:
            await _load_mappings()
        hass.bus.async_listen_once(EVENT_HOMEASSISTANT_STARTED, _startup_loader)

    return True

