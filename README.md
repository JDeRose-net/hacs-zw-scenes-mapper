# Z-Wave to Home Assistant Scenes (zw2ha)

A tiny, event-driven custom integration that listens for **Z-Wave JS Scene Activation** events
(`zwave_js_value_notification` with `command_class: 43`) and activates one or more Home Assistant
scenes based on a simple YAML mapping.

## Features
- Listens to Z-Wave JS Scene Activation (CC 43) events
- Maps `<home_id>-<scene_value>` to one or more scenes
- Supports comma-separated strings **or** YAML lists
- Auto-prefixes `scene.` when the domain is omitted
- Reload mappings via **button** (`button.zw2ha_reload`) or **service** (`zw2ha.reload`)
- Exposes a sensor with the normalized mapping for visibility (`sensor.z_wave_to_ha_scene_map`)
- Basic debounce (default 300 ms) to avoid duplicate activations

## Installation
1. Copy `custom_components/zw2ha` into your Home Assistant `config/custom_components/`.
2. Create `config/zw2ha/mappings.yaml` using the example below.
3. (Optional) Add configuration to `configuration.yaml` if you want to override defaults:
   ```yaml
   zw2ha:
     file: zw2ha/mappings.yaml
     debounce_ms: 300
   ```
4. Restart Home Assistant.

## Example `mappings.yaml`
```yaml
# key: "<home_id>-<scene_value>"
"4227869312-1":  "ga_bd_s4"
"4227869312-2":  "ga_bd_s3"
"4227869312-3":  "ga_bd_s2"
"4227869312-4":  "ga_bd_s0"
"4227869312-5":  "ga_bd_s2"
"4227869312-6":  ["ga_bd_s4", "ga_kit_s4", "ga_lr_s4"]
"4227869312-7":  ["ga_bd_s3", "ga_kit_s3", "ga_lr_s3"]
"4227869312-8":  ["ga_bd_s2", "ga_kit_s2", "ga_lr_s2"]
"4227869312-9":  "ga_bd_s0,ga_kit_s0,ga_lr_s0,ga_ba_s0"
```

> Both comma strings and lists are accepted. Whitespace is trimmed. If you omit a domain, it is
> treated as `scene.<value>`.

## Entities & Services
- `sensor.z_wave_to_ha_scene_map` — attributes include:
  - `data`: normalized mapping (values as **comma strings** of bare slugs, for compatibility)
  - `count`, `file`, `debounce_ms`
- `button.zw2ha_reload` — reloads the YAML file
- Services:
  - `zw2ha.reload` — reload mappings from disk
  - `zw2ha.trigger` — manually trigger a mapping:
    ```yaml
    service: zw2ha.trigger
    data:
      zw_network: "4227869312"
      zw_scene: 6
    ```

## How it works
- Listens for `zwave_js_value_notification` events where `command_class` is `43` (Scene Activation).
- Builds a key string `"{home_id}-{int(value)}"` and looks it up in the map.
- If found (and not recently fired for the same key), calls `scene.turn_on` with all targets at once.

## Logging
Configure the logger if you want more detail:
```yaml
logger:
  default: warning
  logs:
    custom_components.zw2ha: debug
```

## Notes
- This initial version targets **Scene Activation (CC 43)** only. Central Scene (CC 91) could be added later.
- When multiple scenes touch the same entities, consider consolidating into a single scene to avoid races.

## License
MIT
