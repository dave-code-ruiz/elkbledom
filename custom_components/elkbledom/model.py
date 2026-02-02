"""Model configuration manager for LED strips"""
import json
import logging
from pathlib import Path
from typing import Optional, Dict, List
from enum import Enum
from homeassistant.core import HomeAssistant

LOGGER = logging.getLogger(__name__)

# Models data key - must match __init__.py
MODELS_DATA_KEY = "elkbledom_models"

# Cache for dynamically created effect enums
_EFFECTS_CACHE = {}

async def ensure_models_loaded(hass: HomeAssistant) -> Dict[str, Dict]:
    """Ensure models are loaded in hass.data, loading them if necessary."""
    if MODELS_DATA_KEY in hass.data:
        return hass.data[MODELS_DATA_KEY]
    
    # Need to load models
    models_file = Path(__file__).parent / "models.json"
    
    def _load_json():
        try:
            if not models_file.exists():
                LOGGER.error("models.json file not found at: %s", models_file)
                return {}
            
            content = models_file.read_text(encoding="utf-8")
            models = json.loads(content)
            LOGGER.debug("Loaded %d models from models.json", len(models))
            return models
        except json.JSONDecodeError as e:
            LOGGER.error("Error decoding models.json: %s", e)
            return {}
        except Exception as e:
            LOGGER.error("Error loading models.json from %s: %s", models_file, e)
            return {}
    
    hass.data[MODELS_DATA_KEY] = await hass.async_add_executor_job(_load_json)
    return hass.data[MODELS_DATA_KEY]

def get_models_data(hass: HomeAssistant) -> Dict[str, Dict]:
    """Get models data from hass.data (loaded asynchronously in __init__.py)."""
    return hass.data.get(MODELS_DATA_KEY, {})


class Model:
    """Model configuration manager for LED strips"""
    
    def __init__(self, hass: Optional[HomeAssistant] = None):
        """Initialize Model with optional hass instance for data access."""
        self._hass = hass
        self._models: Dict[str, Dict] = {}
        if hass is not None:
            self._models = get_models_data(hass)
    
    def get_models(self) -> List[str]:
        """Get list of all supported model names"""
        return list(self._models.keys())
    
    def detect_model(self, device_name: str) -> Optional[str]:
        """Detect model from device name"""
        device_name_lower = device_name.lower()
        # Sort model names by length (longest first) to match most specific models first
        sorted_models = sorted(self._models.keys(), key=len, reverse=True)
        for model_name in sorted_models:
            if device_name_lower.startswith(model_name.lower()):
                return model_name
        return None
    
    def detect_model_by_handle(self, device_name: str, char_handle: int) -> Optional[str]:
        """Detect model from device name and characteristic handle.
        
        When multiple models have the same name but different handles,
        the handle is used to select the correct one.
        """
        device_name_lower = device_name.lower()
        
        # Collect all matching models by name
        matching_models = []
        for model_name, model_data in self._models.items():
            if device_name_lower.startswith(model_name.lower()):
                matching_models.append((model_name, model_data))
        
        if not matching_models:
            return None
        
        # If only one match, return it
        if len(matching_models) == 1:
            return matching_models[0][0]
        
        # Multiple matches: prefer the one with matching handle
        for model_name, model_data in matching_models:
            model_handle = model_data.get("handle")
            if model_handle is not None and char_handle == model_handle:
                LOGGER.debug("Model detected by handle: %s (handle: 0x%04x)", model_name, char_handle)
                return model_name
        
        # No handle match: return the one without handle (generic version)
        for model_name, model_data in matching_models:
            if model_data.get("handle") is None:
                LOGGER.debug("Model detected by name (no handle match): %s", model_name)
                return model_name
        
        # Fallback: return first match
        return matching_models[0][0]
    
    def get_handle(self, model_name: str) -> Optional[int]:
        """Get handle for model"""
        if model_name in self._models:
            return self._models[model_name].get("handle")
        return None
    
    def get_write_uuid(self, model_name: str) -> Optional[str]:
        """Get write characteristic UUID for model"""
        if model_name in self._models:
            return self._models[model_name].get("write_uuid")
        return None
    
    def get_read_uuid(self, model_name: str) -> Optional[str]:
        """Get read characteristic UUID for model"""
        if model_name in self._models:
            return self._models[model_name].get("read_uuid")
        return None
    
    def get_turn_on_cmd(self, model_name: str) -> Optional[List[int]]:
        """Get turn on command for model"""
        if model_name in self._models:
            return self._models[model_name].get("commands", {}).get("turn_on")
        return None
    
    def get_turn_off_cmd(self, model_name: str) -> Optional[List[int]]:
        """Get turn off command for model"""
        if model_name in self._models:
            return self._models[model_name].get("commands", {}).get("turn_off")
        return None
    
    def get_white_cmd(self, model_name: str, intensity: int) -> Optional[List[int]]:
        """Get white command for model with intensity"""
        if model_name in self._models:
            cmd = self._models[model_name].get("commands", {}).get("white", []).copy()
            # Replace 'i' placeholder with intensity value
            cmd = [int(intensity * 100 / 255) if x == "i" else x for x in cmd]
            return cmd
        return None
    
    def get_effect_speed_cmd(self, model_name: str, value: int) -> Optional[List[int]]:
        """Get effect speed command for model"""
        if model_name in self._models:
            cmd = self._models[model_name].get("commands", {}).get("effect_speed", []).copy()
            # Replace 'v' placeholder with value
            cmd = [int(value) if x == "v" else x for x in cmd]
            return cmd
        return None
    
    def get_effect_cmd(self, model_name: str, value: int) -> Optional[List[int]]:
        """Get effect command for model"""
        if model_name in self._models:
            cmd = self._models[model_name].get("commands", {}).get("effect", []).copy()
            # Replace 'v' placeholder with value
            cmd = [int(value) if x == "v" else x for x in cmd]
            return cmd
        return None
    
    def get_color_temp_cmd(self, model_name: str, warm: int, cold: int) -> Optional[List[int]]:
        """Get color temperature command for model"""
        if model_name in self._models:
            cmd = self._models[model_name].get("commands", {}).get("color_temp", []).copy()
            # Replace 'w' and 'c' placeholders with warm and cold values
            result = []
            for x in cmd:
                if x == "w":
                    result.append(int(warm))
                elif x == "c":
                    result.append(int(cold))
                else:
                    result.append(x)
            return result
        return None
    
    def get_color_cmd(self, model_name: str, r: int, g: int, b: int) -> Optional[List[int]]:
        """Get color command for model"""
        if model_name in self._models:
            cmd = self._models[model_name].get("commands", {}).get("color", []).copy()
            # Replace 'r', 'g', 'b' placeholders with RGB values
            result = []
            for x in cmd:
                if x == "r":
                    result.append(r)
                elif x == "g":
                    result.append(g)
                elif x == "b":
                    result.append(b)
                else:
                    result.append(x)
            return result
        return None
    
    def get_brightness_cmd(self, model_name: str, intensity: int) -> Optional[List[int]]:
        """Get brightness command for model"""
        if model_name in self._models:
            cmd = self._models[model_name].get("commands", {}).get("brightness", []).copy()
            # Replace 'i' placeholder with intensity value
            cmd = [int(intensity * 100 / 255) if x == "i" else x for x in cmd]
            return cmd
        return None
    
    def get_query_cmd(self, model_name: str) -> Optional[List[int]]:
        """Get query command for model"""
        if model_name in self._models:
            return self._models[model_name].get("commands", {}).get("query")
        return None
    
    def get_sync_time_cmd(self, model_name: str, hour: int, minute: int, second: int, day_of_week: int) -> List[int]:
        """Get sync time command (same for all models)"""
        return [0x7e, 0x00, 0x83, hour, minute, second, day_of_week, 0x00, 0xef]
    
    def get_custom_time_cmd(self, model_name: str, hour: int, minute: int, second: int, day_of_week: int) -> List[int]:
        """Get custom time command (same for all models)"""
        return [0x7e, 0x00, 0x83, hour, minute, second, day_of_week, 0x00, 0xef]
    
    def get_min_color_temp_kelvin(self, model_name: str) -> int:
        """Get minimum color temperature in Kelvin for model"""
        if model_name in self._models:
            return self._models[model_name].get("color_temp_range", {}).get("min_kelvin", 1800)
        return 1800
    
    def get_max_color_temp_kelvin(self, model_name: str) -> int:
        """Get maximum color temperature in Kelvin for model"""
        if model_name in self._models:
            return self._models[model_name].get("color_temp_range", {}).get("max_kelvin", 7000)
        return 7000
    
    def get_effects_class(self, model_name: str) -> str:
        """Get effects class name for model"""
        if model_name in self._models:
            return self._models[model_name].get("effects_class", "EFFECTS")
        return "EFFECTS"
    
    def get_effects_list(self, model_name: str) -> str:
        """Get effects list name for model"""
        if model_name in self._models:
            return self._models[model_name].get("effects_list", "EFFECTS_list")
        return "EFFECTS_list"    
    def get_effect_value(self, effects_class_name: str, effect_name: str) -> Optional[int]:
        """Get effect value from effects definitions"""
        definitions = self._load_definitions()
        effects_defs = definitions.get("effects_definitions", {})
        effects_class = effects_defs.get(effects_class_name, {})
        return effects_class.get(effect_name)
    
    def get_effects_enum(self, effects_class_name: str) -> Optional[type]:
        """Get or create an Enum class for the specified effects class"""
        # Check cache first
        if effects_class_name in _EFFECTS_CACHE:
            return _EFFECTS_CACHE[effects_class_name]
        
        definitions = self._load_definitions()
        effects_defs = definitions.get("effects_definitions", {})
        if effects_class_name not in effects_defs:
            return None
        
        # Create enum dynamically
        effects_dict = effects_defs[effects_class_name]
        effects_enum = Enum(effects_class_name, effects_dict)
        
        # Cache it
        _EFFECTS_CACHE[effects_class_name] = effects_enum
        return effects_enum
    
    def get_effects_list_values(self, effects_list_name: str) -> List[str]:
        """Get list of effect names for a specific effects list"""
        definitions = self._load_definitions()
        effects_lists = definitions.get("effects_lists", {})
        return effects_lists.get(effects_list_name, [])
    
    def get_all_effects_definitions(self) -> Dict[str, Dict[str, int]]:
        """Get all effects definitions"""
        definitions = self._load_definitions()
        return definitions.get("effects_definitions", {})
    
    def get_all_effects_lists(self) -> Dict[str, List[str]]:
        """Get all effects lists"""
        definitions = self._load_definitions()
        return definitions.get("effects_lists", {})
    
    def _load_definitions(self) -> Dict:
        """Load definitions from definitions.json"""
        definitions_file = Path(__file__).parent / "definitions.json"
        try:
            if not definitions_file.exists():
                return {}
            content = definitions_file.read_text(encoding="utf-8")
            return json.loads(content)
        except Exception as e:
            LOGGER.error("Error loading definitions.json: %s", e)
            return {}