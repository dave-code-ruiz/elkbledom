import logging
import voluptuous as vol
from typing import Any, Optional, Tuple

from .elkbledom import BLEDOMInstance
from .const import DOMAIN, EFFECTS, EFFECTS_list

from homeassistant.const import CONF_MAC
import homeassistant.helpers.config_validation as cv
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.components.light import (
    PLATFORM_SCHEMA,
    ATTR_BRIGHTNESS,
    ATTR_COLOR_TEMP,
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
    # config_entry.async_on_unload(
    #     await instance.stop()
    # )

class BLEDOMLight(LightEntity):
    def __init__(self, bledomInstance: BLEDOMInstance, name: str, entry_id: str) -> None:
        self._instance = bledomInstance
        self._entry_id = entry_id
        self._attr_supported_color_modes = {ColorMode.RGB, ColorMode.COLOR_TEMP, ColorMode.WHITE}
        self._attr_supported_features = LightEntityFeature.EFFECT
        self._color_mode = ColorMode.WHITE
        self._attr_name = name
        self._effect = None
        self._attr_unique_id = self._instance.mac

    @property
    def available(self):
        return self._instance.is_on != None

    @property
    def brightness(self):
        if self._instance.white_brightness:
            return self._instance.white_brightness
        
        return None

    @property
    def is_on(self) -> Optional[bool]:
        return self._instance.is_on

    @property
    def max_mireds(self):
        return 100

    @property
    def min_mireds(self):
        return 1

    @property
    def color_temp(self):
        return self._instance.color_temp

    @property
    def effect_list(self):
        return EFFECTS_list

    @property
    def effect(self):
        return self._effect

    @property
    def supported_features(self) -> int:
        """Flag supported features."""
        return self._attr_supported_features

    @property
    def supported_color_modes(self) -> int:
        """Flag supported color modes."""
        return self._attr_supported_color_modes

    @property
    def rgb_color(self):
        if self._instance.rgb_color:
            return self._instance.rgb_color
        return None

    @property
    def color_mode(self):
        """Return the color mode of the light."""
        return self._color_mode
        
    @property
    def device_info(self):
        """Return device info."""
        return DeviceInfo(
            identifiers={
                # Serial numbers are unique identifiers within a specific domain
                (DOMAIN, self._instance.mac)
            },
            name=self.name,
            connections={(device_registry.CONNECTION_NETWORK_MAC, self._instance.mac)},
            config_entry_id=self._entry_id,
        )

    @property
    def should_poll(self):
        """No polling needed for a demo light."""
        return False

    async def async_turn_on(self, **kwargs: Any) -> None:
        LOGGER.debug(f"Params turn on: {kwargs}")
        if not self.is_on:
            await self._instance.turn_on()
            LOGGER.debug("Change color to white, some error with other infrared control interact")
            await self._instance.set_color((255, 255, 255))
            await self._instance.set_white(255)

        if ATTR_BRIGHTNESS in kwargs and kwargs[ATTR_BRIGHTNESS] != self.brightness and self.rgb_color != None:
            await self._instance.set_white(kwargs[ATTR_BRIGHTNESS])

        if ATTR_COLOR_TEMP in kwargs:
            self._color_mode = ColorMode.COLOR_TEMP
            if kwargs[ATTR_COLOR_TEMP] != self.color_temp:
                self._effect = None
                await self._instance.set_color_temp(kwargs[ATTR_COLOR_TEMP])

        if ATTR_WHITE in kwargs:
            self._color_mode = ColorMode.WHITE
            if self.rgb_color != (255, 255, 255):
                await self._instance.set_color((255, 255, 255))
            if kwargs[ATTR_WHITE] != self.brightness:
                self._effect = None
                await self._instance.set_white(kwargs[ATTR_WHITE])

        if ATTR_RGB_COLOR in kwargs:
            self._color_mode = ColorMode.RGB
            if kwargs[ATTR_RGB_COLOR] != self.rgb_color:
                color = kwargs[ATTR_RGB_COLOR]
                self._effect = None
                await self._instance.set_color(color)

        if ATTR_EFFECT in kwargs and kwargs[ATTR_EFFECT] != self.effect:
            self._effect = kwargs[ATTR_EFFECT]
            await self._instance.set_effect(EFFECTS[kwargs[ATTR_EFFECT]].value)

        self.async_write_ha_state()

    async def async_turn_off(self, **kwargs: Any) -> None:
        await self._instance.turn_off()
        self.async_write_ha_state()

    async def async_update(self) -> None:
        await self._instance.update()
        self.async_write_ha_state()
