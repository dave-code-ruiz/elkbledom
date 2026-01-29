from enum import Enum
import json
from pathlib import Path

DOMAIN = "elkbledom"
CONF_RESET = "reset"
CONF_DELAY = "delay"
CONF_MODEL = "model"
CONF_EFFECTS_CLASS = "effects_class"

# Brightness mode configuration
CONF_BRIGHTNESS_MODE = "brightness_mode"
BRIGHTNESS_MODES = ["auto", "rgb", "native"]
DEFAULT_BRIGHTNESS_MODE = "auto"
class MIC_EFFECTS (Enum):
    # Microphone Effects (0x80-0x87)
    mic_energic = 0x80
    mic_rhythm = 0x81
    mic_spectrum = 0x82
    mic_rolling = 0x83
    mic_effect_4 = 0x84
    mic_effect_5 = 0x85
    mic_effect_6 = 0x86
    mic_effect_7 = 0x87

MIC_EFFECTS_list = [
    'mic_energic',
    'mic_rhythm',
    'mic_spectrum',
    'mic_rolling',
    'mic_effect_4',
    'mic_effect_5',
    'mic_effect_6',
    'mic_effect_7'
    ]

class WEEK_DAYS (Enum):
    monday = 0x01
    tuesday = 0x02
    wednesday = 0x04
    thursday = 0x08
    friday = 0x10
    saturday = 0x20
    sunday = 0x40
    all = (0x01 + 0x02 + 0x04 + 0x08 + 0x10 + 0x20 + 0x40)
    week_days = (0x01 + 0x02 + 0x04 + 0x08 + 0x10)
    weekend_days = (0x20 + 0x40)
    none = 0x00

#print(EFFECTS.blink_red.value)

# Load effects definitions from definitions.json
def _load_effects_from_json():
    """Load effects definitions and lists from definitions.json"""
    definitions_file = Path(__file__).parent / "definitions.json"
    try:
        with open(definitions_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
            effects_defs = data.get("effects_definitions", {})
            effects_lists = data.get("effects_lists", {})
            
            # Create Enum classes dynamically for all effects definitions
            effects_enums = {}
            for effect_class_name, effect_values in effects_defs.items():
                effects_enums[effect_class_name] = Enum(effect_class_name, effect_values)
            
            return effects_enums, effects_lists
    except Exception as e:
        # Fallback to empty dicts if file doesn't exist or can't be loaded
        return {}, {}

_effects_enums, _effects_lists_data = _load_effects_from_json()

# Export all effect classes and lists dynamically
# This allows adding new effects in models.json without changing this file
globals().update(_effects_enums)  # EFFECTS, EFFECTS_MELK, EFFECTS_MELK_OF10, etc.
globals().update(_effects_lists_data)  # EFFECTS_list, EFFECTS_list_MELK, etc.

# Create EFFECTS_MAP with all dynamically loaded effect classes
EFFECTS_MAP = _effects_enums.copy()

# Create EFFECTS_LIST_MAP with all dynamically loaded effect lists
EFFECTS_LIST_MAP = _effects_lists_data.copy()
