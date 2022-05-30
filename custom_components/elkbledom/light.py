import logging
import voluptuous as vol
from typing import Any, Optional, Tuple

from .elkbledom import BLEDOMInstance
from .const import DOMAIN

from homeassistant.const import CONF_MAC
import homeassistant.helpers.config_validation as cv
from homeassistant.components.light import (COLOR_MODE_RGB, PLATFORM_SCHEMA,
                                            LightEntity, ATTR_RGB_COLOR, ATTR_BRIGHTNESS, COLOR_MODE_WHITE, ATTR_WHITE)
from homeassistant.util.color import (match_max_scale)
from homeassistant.helpers import device_registry

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend({
    vol.Required(CONF_MAC): cv.string
})

async def async_setup_entry(hass, config_entry, async_add_devices):
    instance = hass.data[DOMAIN][config_entry.entry_id]
    async_add_devices([BLEDOMLight(instance, config_entry.data["name"], config_entry.entry_id)])

class BLEDOMLight(LightEntity):
    def __init__(self, bledomInstance: BLEDOMInstance, name: str, entry_id: str) -> None:
        self._instance = bledomInstance
        self._entry_id = entry_id
        self._attr_supported_color_modes = {COLOR_MODE_RGB, COLOR_MODE_WHITE}
        self._color_mode = None
        self._attr_name = name
        self._attr_unique_id = self._instance.mac

    @property
    def available(self):
        return self._instance.is_on != None

    @property
    def brightness(self):
        if self._instance.white_brightness:
            return self._instance.white_brightness
        
        if self._instance._rgb_color:
            return max(self._instance.rgb_color)
        
        return None

    @property
    def is_on(self) -> Optional[bool]:
        return self._instance.is_on

    @property
    # RGB color/brightness based on https://github.com/home-assistant/core/issues/51175
    def rgb_color(self):
        if self._instance.rgb_color:
            return match_max_scale((255,), self._instance.rgb_color)
        return None

    @property
    def color_mode(self):
        if self._instance.rgb_color:
            if self._instance.rgb_color == (0, 0, 0):
                return COLOR_MODE_WHITE
            return COLOR_MODE_RGB
        return None

    @property
    def device_info(self):
        return {
            "identifiers": {
                (DOMAIN, self._instance.mac)
            },
            "name": self.name,
            "connections": {(device_registry.CONNECTION_NETWORK_MAC, self._instance.mac)},
            "config_entry_id": self._entry_id
        }

    def _transform_color_brightness(self, color: Tuple[int, int, int], set_brightness: int):
        rgb = match_max_scale((255,), color)
        res = tuple(color * set_brightness // 255 for color in rgb)
        return res

    async def async_turn_on(self, **kwargs: Any) -> None:
        if not self.is_on:
            await self._instance.turn_on()

        if ATTR_WHITE in kwargs:
            if kwargs[ATTR_WHITE] != self.brightness:
                await self._instance.set_white(kwargs[ATTR_WHITE])

        elif ATTR_RGB_COLOR in kwargs:
            if kwargs[ATTR_RGB_COLOR] != self.rgb_color:
                color = kwargs[ATTR_RGB_COLOR]
                if ATTR_BRIGHTNESS in kwargs:
                    color = self._transform_color_brightness(color, kwargs[ATTR_BRIGHTNESS])
                else:
                    color = self._transform_color_brightness(color, self.brightness)
                await self._instance.set_color(color)
        
        elif ATTR_BRIGHTNESS in kwargs and kwargs[ATTR_BRIGHTNESS] != self.brightness and self.rgb_color != None:
            await self._instance.set_color(self._transform_color_brightness(self.rgb_color, kwargs[ATTR_BRIGHTNESS]))


    async def async_turn_off(self, **kwargs: Any) -> None:
        await self._instance.turn_off()

    async def async_update(self) -> None:
        await self._instance.update()
