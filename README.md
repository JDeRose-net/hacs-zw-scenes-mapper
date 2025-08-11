# Z-Wave Scenes Mapper (zw2ha)

Maps **Z-Wave JS Scene Activation** events to **Home Assistant actions** using a simple YAML file.  
When a specific `<home_id>-<scene_value>` fires, zw2ha calls one or more entities with the correct service.

- Listens to `zwave_js_value_notification` (Command Class **43**)
- **Explicit entity IDs only** (`scene.*`, `script.*`, `automation.*`, `button.*`)
- Hot-reload your mappings without restarting HA
- Sensor shows mapping details + timestamps

## Install

1. Copy `custom_components/zw2ha` into your Home Assistant `config/custom_components/` directory  
   (or add the repo to HACS as a custom repository).
2. Add to `configuration.yaml`:

    zw2ha:
      # file: etc/zw2ha/mappings.yaml      # optional; this is the default
      # file: component:mappings.yaml      # use the packaged example file
      # file: zw2ha/mappings.yaml          # relative to /config
      # file: /absolute/path/to/file.yaml  # absolute path
      # debounce_ms: 300                   # optional (default 300ms)

3. Restart Home Assistant.

On first run, if the default file is missing, zw2ha will:
- create `/config/etc/zw2ha/` (if needed),
- copy the packaged `mappings.yaml` if present; otherwise create an empty `{}` stub.

## Default mapping file

Location: `/config/etc/zw2ha/mappings.yaml` (unless you override `file:`).

Keys are strings like `"4227869312-6"`:
- `4227869312` = Z-Wave JS `home_id`
- `6` = Scene value from the event’s `value` (0–255)

Always **quote** the key due to the hyphen and large integers.

### Allowed values (Tier 1)

Each value lists **fully-qualified entity IDs**. You can use a single string, a comma-string, or a YAML list.

- `scene.*` → `scene.turn_on`
- `script.*` → `script.turn_on`
- `automation.*` → `automation.trigger`
- `button.*` → `button.press`

Bare slugs (e.g., `kitchen_evening`) are ignored with a warning.  
Unknown domains fall back to `homeassistant.turn_on` (best-effort).

### Examples

Single target:

    "4227869312-1": "scene.ga_bd_s4"

Multiple (list):

    "4227869312-6":
      - scene.ga_bd_s4
      - scene.ga_kit_s4
      - scene.ga_lr_s4

Multiple (comma string):

    "4227869312-9": "scene.ga_bd_s0,scene.ga_kit_s0,scene.ga_lr_s0,scene.ga_ba_s0"

## Entities & Services

- Sensor: `sensor.zw2ha_map`  
  Attributes:
  - `data`: normalized mapping (`key: "entity1,entity2,..."`)
  - `count`: number of mappings loaded
  - `file`: resolved path to the active mappings file
  - `debounce_ms`: active debounce window (ms)
  - `last_loaded`: ISO-8601 UTC timestamp when the file was last read
  - `file_mtime`: ISO-8601 UTC timestamp of the file’s modification time

- Button: `button.zw2ha_reload`  
  Reloads the YAML file from disk.

- Services (Developer Tools → Actions):
  - `zw2ha.reload` — reload mappings
  - `zw2ha.trigger` — manually trigger a key:

        zw_network: "4227869312"
        zw_scene: 6

## How it works

- Subscribes to `zwave_js_value_notification` and filters for Command Class 43 (Scene Activation).
- Builds `"<home_id>-<value>"` and looks it up in your mapping.
- Applies a per-key debounce (default 300 ms).
- Calls each mapped entity with the appropriate service (in parallel).

## Troubleshooting

- No actions fire: ensure values are full entity IDs (e.g., `scene.kitchen_evening`).  
  Check Logs for: “ignoring unmapped/bare token …”.
- “Referenced entities … are missing”: the entity doesn’t exist or is unavailable. Verify in Developer Tools → States.
- Wrong file loaded: see `sensor.zw2ha_map` → `file`. Override with `file:` in `configuration.yaml` if needed.
- Mapping changes not applied: use `button.zw2ha_reload` or `zw2ha.reload`.

For verbose logs:

    logger:
      default: warning
      logs:
        custom_components.zw2ha: debug

## Uninstall / Updates

- Default mapping lives at `/config/etc/zw2ha/mappings.yaml`, so HACS updates/uninstall won’t touch it.
- Avoid storing live mappings inside `custom_components/zw2ha/` (HACS may overwrite on update).

## Example mapping (scenes only)

    "4227869312-1":  "scene.ga_bd_s4"
    "4227869312-2":  "scene.ga_bd_s3"
    "4227869312-3":  "scene.ga_bd_s2"
    "4227869312-4":  "scene.ga_bd_s0"
    "4227869312-5":  "scene.ga_bd_s2"

    "4227869312-6":
      - scene.ga_bd_s4
      - scene.ga_kit_s4
      - scene.ga_lr_s4
    "4227869312-7":
      - scene.ga_bd_s3
      - scene.ga_kit_s3
      - scene.ga_lr_s3
    "4227869312-8":
      - scene.ga_bd_s2
      - scene.ga_kit_s2
      - scene.ga_lr_s2
    "4227869312-9":
      - scene.ga_bd_s0
      - scene.ga_kit_s0
      - scene.ga_lr_s0
      - scene.ga_ba_s0

    "4227869312-10": "scene.ga_ba_s4"
    "4227869312-11": "scene.ga_ba_s3"
    "4227869312-12": "scene.ga_ba_s2"
    "4227869312-13": "scene.ga_ba_s0"

    "4227869312-14": "scene.ga_kit_s4"
    "4227869312-15": "scene.ga_kit_s3"
    "4227869312-16": "scene.ga_kit_s2"
    "4227869312-17": "scene.ga_kit_s0"

    "4227869312-18": "scene.ga_lr_s4"
    "4227869312-19": "scene.ga_lr_s3"
    "4227869312-20": "scene.ga_lr_s2"
    "4227869312-21": "scene.ga_lr_s0"

## Changelog

- 0.2.3
  - Default mapping file moved to `/config/etc/zw2ha/mappings.yaml`
  - First-run bootstrap creates default file (copy example or `{}`)
- 0.2.2
  - Async YAML loading (no event-loop blocking)
  - Sensor timestamps: `last_loaded`, `file_mtime`
- 0.2.1
  - Explicit entity IDs only (no auto-prefixing)
- 0.2.0
  - Tier 1 dispatch (`scene/script/automation/button`)
  - Sensor renamed to `sensor.zw2ha_map`

## License

MIT

