DOMAIN = "zwave_mapr"

# sample configuration.yaml directives
#
# zwave_mapr:
#   file: /config/etc/zw2ha/mappings.yaml
#   debounce_ms: 100

CONF_FILE = "file"
CONF_DEBOUNCE_MS = "debounce_ms"

# Default mapping lives under /config/etc/zwave_mapr/
DEFAULT_FILE = "etc/zwave_mapr/mappings.yaml"
DEFAULT_DEBOUNCE_MS = 300

EVENT_MAPPINGS_UPDATED = f"{DOMAIN}_mappings_updated"
ATTR_DATA = "data"

EVENT_TYPE = "zwave_js_value_notification"
SCENE_ACTIVATION_CC = 43  # COMMAND_CLASS_SCENE_ACTIVATION
