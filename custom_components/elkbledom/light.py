from __future__ import annotations

import logging
import voluptuous as vol
from typing import Any, Optional, Tuple

from .elkbledom import BLEDOMInstance
from .const import DOMAIN, EFFECTS, EFFECTS_list, EFFECTS_MAP, EFFECTS_LIST_MAP, CONF_EFFECTS_CLASS

from homeassistant.const import CONF_MAC
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.restore_state import RestoreEntity
from homeassistant.components.light import (
    PLATFORM_SCHEMA,
    ATTR_BRIGHTNESS,
    ATTR_COLOR_TEMP_KELVIN,
    ATTR_EFFECT,
    ATTR_RGB_COLOR,
    ATTR_WHITE,
    ColorMode,
    LightEntity,
    LightEntityFeature,
)
from homeassistant.util.color import (match_max_scale)
from homeassistant.helpers import device_registry

PARALLEL_UPDATES = 0  # fix entity_platform parallel_updates Semaphore

LOGGER = logging.getLogger(__name__)
PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend({
    vol.Required(CONF_MAC): cv.string
})

async def async_setup_entry(hass, config_entry, async_add_devices):
    instance = hass.data[DOMAIN][config_entry.entry_id]
    await instance.update()
    async_add_devices([BLEDOMLight(instance, config_entry.data["name"], config_entry.entry_id)])

class BLEDOMLight(RestoreEntity, LightEntity):
    def __init__(self, bledomInstance: BLEDOMInstance, name: str, entry_id: str) -> None:
        self._instance = bledomInstance
        self._entry_id = entry_id
        self._attr_supported_color_modes = {ColorMode.RGB, ColorMode.COLOR_TEMP, ColorMode.WHITE}
        self._attr_supported_features = LightEntityFeature.EFFECT
        self._attr_color_mode = ColorMode.WHITE
        self._attr_name = name
        self._attr_effect = None
        self._attr_unique_id = self._instance.address
        self._hass = None

    @property
    def available(self):
        return self._instance.is_on != None

    @property
    def brightness(self):
        return self._instance.brightness

    @property
    def is_on(self) -> Optional[bool]:
        return self._instance.is_on

    @property
    def color_temp_kelvin(self):
        return self._instance.color_temp_kelvin
    
    @property
    def max_color_temp_kelvin(self):
        return self._instance.max_color_temp_kelvin

    @property
    def min_color_temp_kelvin(self):
        return self._instance.min_color_temp_kelvin

    @property
    def effect_list(self):
        """Return list of available effects for this model."""
        # First check if user has manually configured effects class
        effects_class_name = self._get_configured_effects_class()
        if effects_class_name:
            # Get the corresponding list using the same position in both maps
            effects_to_list_map = dict(zip(EFFECTS_MAP.keys(), EFFECTS_LIST_MAP.keys()))
            effects_list_name = effects_to_list_map.get(effects_class_name)
            if effects_list_name:
                return EFFECTS_LIST_MAP.get(effects_list_name, EFFECTS_list)
        
        # Otherwise use model default
        effects_list_name = self._instance.model.get_effects_list(self._instance.model_name)
        return EFFECTS_LIST_MAP.get(effects_list_name, EFFECTS_list)

    @property
    def effect(self):
        """Return current effect."""
        return self._attr_effect

    @property
    def extra_state_attributes(self):
        """Return entity specific state attributes."""
        return {
            "effect_speed": self._instance.effect_speed,
        }

    @property
    def rgb_color(self):
        if self._instance.rgb_color:
            return match_max_scale((255,), self._instance.rgb_color)
        return None

    @property
    def device_info(self):
        """Return device info."""
        return DeviceInfo(
            identifiers={
                # Serial numbers are unique identifiers within a specific domain
                (DOMAIN, self._instance.address)
            },
            name=self.name,
            connections={(device_registry.CONNECTION_NETWORK_MAC, self._instance.address)},
        )

    @property
    def should_poll(self):
        """No polling needed for a demo light."""
        return False

    def _get_configured_effects_class(self) -> Optional[str]:
        """Get the configured effects class from config entry options."""
        if not self._hass:
            return None
        
        # Get config entry for this entity
        from homeassistant.helpers import entity_registry
        ent_reg = entity_registry.async_get(self._hass)
        entity_entry = ent_reg.async_get(self.entity_id)
        
        if entity_entry and entity_entry.config_entry_id:
            config_entry = self._hass.config_entries.async_get_entry(entity_entry.config_entry_id)
            if config_entry:
                return config_entry.options.get(CONF_EFFECTS_CLASS)
        
        return None
    
    async def async_added_to_hass(self) -> None:
        """Restore previous state when entity is added to hass."""
        await super().async_added_to_hass()
        
        # Store hass reference for config access
        self._hass = self.hass
        
        # Restore the last known state
        if (last_state := await self.async_get_last_state()) is not None:
            LOGGER.debug(f"Restoring previous state for {self.name}: {last_state.state}")
            
            # Restore on/off state
            if last_state.state == "on":
                self._instance._is_on = True
                LOGGER.debug(f"Restored state: ON")
            elif last_state.state == "off":
                self._instance._is_on = False
                LOGGER.debug(f"Restored state: OFF")
            elif last_state.state == "unavailable":
                # If previous state was unavailable, assume device is off but available
                # This prevents the entity from staying unavailable after restart
                self._instance._is_on = False
                LOGGER.debug(f"Previous state was unavailable, setting to OFF")
            
            # Restore brightness
            if ATTR_BRIGHTNESS in last_state.attributes:
                self._instance._brightness = last_state.attributes[ATTR_BRIGHTNESS]
                LOGGER.debug(f"Restored brightness: {self._instance._brightness}")
            
            # Restore RGB color
            if ATTR_RGB_COLOR in last_state.attributes and last_state.attributes[ATTR_RGB_COLOR] is not None:
                try:
                    self._instance._rgb_color = tuple(last_state.attributes[ATTR_RGB_COLOR])
                    self._attr_color_mode = ColorMode.RGB
                    LOGGER.debug(f"Restored RGB color: {self._instance._rgb_color}")
                except (TypeError, ValueError) as e:
                    LOGGER.warning(f"Invalid RGB color data, skipping: {e}")
            
            # Restore color temperature
            elif ATTR_COLOR_TEMP_KELVIN in last_state.attributes and last_state.attributes[ATTR_COLOR_TEMP_KELVIN] is not None:
                try:
                    self._instance._color_temp_kelvin = last_state.attributes[ATTR_COLOR_TEMP_KELVIN]
                    self._attr_color_mode = ColorMode.COLOR_TEMP
                    LOGGER.debug(f"Restored color temp: {self._instance._color_temp_kelvin}K")
                except (TypeError, ValueError) as e:
                    LOGGER.warning(f"Invalid color temperature data, skipping: {e}")
            
            # Restore white mode
            elif last_state.attributes.get("color_mode") == ColorMode.WHITE:
                self._attr_color_mode = ColorMode.WHITE
                LOGGER.debug("Restored color mode: WHITE")
            
            # Restore effect
            if ATTR_EFFECT in last_state.attributes:
                self._attr_effect = last_state.attributes[ATTR_EFFECT]
                # Get the correct effects class (user configured or model default)
                effects_class_name = self._get_configured_effects_class()
                if not effects_class_name:
                    effects_class_name = self._instance.model.get_effects_class(self._instance.model_name)
                effects_class = EFFECTS_MAP.get(effects_class_name, EFFECTS)
                if self._attr_effect in effects_class.__members__:
                    self._instance._effect = effects_class[self._attr_effect].value
                LOGGER.debug(f"Restored effect: {self._attr_effect}")
            
            # Restore effect speed from extra attributes
            if "effect_speed" in last_state.attributes:
                try:
                    self._instance._effect_speed = int(last_state.attributes["effect_speed"])
                    LOGGER.debug(f"Restored effect speed: {self._instance._effect_speed}")
                except (TypeError, ValueError) as e:
                    LOGGER.warning(f"Invalid effect speed data, using default: {e}")
        else:
            # No previous state found, set default values
            LOGGER.debug(f"No previous state found for {self.name}, setting defaults")
            self._instance._is_on = False
            self._instance._brightness = 255
            self._attr_color_mode = ColorMode.WHITE

    def _transform_color_brightness(self, color: Tuple[int, int, int], set_brightness: int):
        rgb = match_max_scale((255,), color)
        res = tuple(color * set_brightness // 255 for color in rgb)
        return res

    async def async_turn_on(self, **kwargs: Any) -> None:
        LOGGER.debug(f"Params turn on: {kwargs} color mode: {self._attr_color_mode}")
        if not self.is_on:
            await self._instance.turn_on()
            if self._instance.reset:
                LOGGER.debug("Change color to white to reset led strip when other infrared control interact")
                self._attr_color_mode = ColorMode.WHITE
                self._attr_effect = None
                await self._instance.set_color(self._transform_color_brightness((255, 255, 255), 250), is_base_color=False)
                if ATTR_WHITE in kwargs:
                    await self._instance.set_white(kwargs[ATTR_WHITE])

        
        if ATTR_BRIGHTNESS in kwargs and kwargs[ATTR_BRIGHTNESS] != self.brightness and self.rgb_color != None:
            await self._instance.set_brightness(kwargs[ATTR_BRIGHTNESS])

        if ATTR_COLOR_TEMP_KELVIN in kwargs:
            self._attr_color_mode = ColorMode.COLOR_TEMP
            if kwargs[ATTR_COLOR_TEMP_KELVIN] != self.color_temp:
                self._attr_effect = None
                brightness = kwargs.get(ATTR_BRIGHTNESS, self.brightness)
                await self._instance.set_color_temp_kelvin(kwargs[ATTR_COLOR_TEMP_KELVIN], brightness)

        if ATTR_WHITE in kwargs:
            self._attr_color_mode = ColorMode.WHITE
            self._attr_effect = None
            await self._instance.set_color(self._transform_color_brightness((255, 255, 255), kwargs[ATTR_WHITE]), is_base_color=False)
            await self._instance.set_white(kwargs[ATTR_WHITE])

        if ATTR_RGB_COLOR in kwargs:
            self._attr_color_mode = ColorMode.RGB
            if kwargs[ATTR_RGB_COLOR] != self.rgb_color:
                color = kwargs[ATTR_RGB_COLOR]
                self._attr_effect = None
                # Save as base color and apply current brightness
                await self._instance.set_color(color, is_base_color=True)
                # Apply current brightness to the new color
                current_brightness = kwargs.get(ATTR_BRIGHTNESS, self.brightness)
                if current_brightness and current_brightness != 255:
                    await self._instance.set_brightness(current_brightness)

        if ATTR_EFFECT in kwargs and kwargs[ATTR_EFFECT] != self.effect:
            self._attr_effect = kwargs[ATTR_EFFECT]
            # Get the correct effects class (user configured or model default)
            effects_class_name = self._get_configured_effects_class()
            if not effects_class_name:
                effects_class_name = self._instance.model.get_effects_class(self._instance.model_name)
            effects_class = EFFECTS_MAP.get(effects_class_name, EFFECTS)
            effect_value = effects_class[kwargs[ATTR_EFFECT]].value
            await self._instance.set_effect(effect_value)
            # Also send effect speed to ensure it's applied
            if self._instance.effect_speed is not None:
                await self._instance.set_effect_speed(self._instance.effect_speed)

        self.async_write_ha_state()

    async def async_turn_off(self, **kwargs: Any) -> None:
        LOGGER.debug(f"Params turn off: {kwargs} color mode: {self._attr_color_mode}")
        await self._instance.turn_off()
        self.async_write_ha_state()

    async def async_update(self) -> None:
        await self._instance.update()
        self.async_write_ha_state()
