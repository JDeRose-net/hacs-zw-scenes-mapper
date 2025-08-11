# const.py

# sample configuration.yaml directives
#
# zw2ha:
#   file: /config/etc/zw2ha/mappings.yaml
#   debounce_ms: 100

DOMAIN = "zw2ha"
CONF_FILE = "file"
CONF_DEBOUNCE_MS = "debounce_ms"

# default mapping lives under /config/etc/zw2ha/
DEFAULT_FILE = "etc/zw2ha/mappings.yaml"
DEFAULT_DEBOUNCE_MS = 300

EVENT_MAPPINGS_UPDATED = f"{DOMAIN}_mappings_updated"
ATTR_DATA = "data"

EVENT_TYPE = "zwave_js_value_notification"
SCENE_ACTIVATION_CC = 43  # COMMAND_CLASS_SCENE_ACTIVATION
