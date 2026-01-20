"""Model configuration manager for LED strips"""
import json
import logging
from pathlib import Path
from typing import Optional, Dict, List

LOGGER = logging.getLogger(__name__)

# Load models at module import time to avoid blocking I/O in event loop
_MODELS_CACHE: Dict[str, Dict] = {}

def _load_models_once() -> Dict[str, Dict]:
    """Load model configuration from JSON file (called once at module import)"""
    global _MODELS_CACHE
    if _MODELS_CACHE:
        return _MODELS_CACHE
    
    try:
        config_path = Path(__file__).parent / "models.json"
        with open(config_path, 'r') as f:
            _MODELS_CACHE = json.load(f)
        LOGGER.debug("Loaded %d models from configuration", len(_MODELS_CACHE))
    except Exception as e:
        LOGGER.error("Error loading models configuration: %s", e)
        _MODELS_CACHE = {}
    
    return _MODELS_CACHE

# Load models at module import time
_load_models_once()


class Model:
    """Model configuration manager for LED strips"""
    
    def __init__(self):
        self._models: Dict[str, Dict] = _MODELS_CACHE
    
    @staticmethod
    def get_models() -> List[str]:
        """Get list of all supported model names"""
        instance = Model()
        return list(instance._models.keys())
    
    def detect_model(self, device_name: str) -> Optional[str]:
        """Detect model from device name"""
        device_name_lower = device_name.lower()
        for model_name in self._models.keys():
            if device_name_lower.startswith(model_name.lower()):
                return model_name
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
