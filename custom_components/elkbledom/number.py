from __future__ import annotations

from homeassistant.components.number import (
    NumberEntity,
    NumberEntityDescription,
)

from .elkbledom import BLEDOMInstance
from .const import DOMAIN

from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers import device_registry
from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry


import logging

LOG = logging.getLogger(__name__)

async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    instance = hass.data[DOMAIN][config_entry.entry_id]
    await instance.update()
    async_add_entities(
        [BLEDOMSlider(instance, "Effect Speed " + config_entry.data["name"], config_entry.entry_id)])

class BLEDOMSlider(NumberEntity):
    """Blauberg Fan entity"""

    def __init__(self, bledomInstance: BLEDOMInstance, attr_name: str, entry_id: str) -> None:
        self._instance = bledomInstance
        self._attr_name = attr_name
        self._attr_unique_id = self._instance.address
        self._effect_speed = 0

    @property
    def available(self):
        return self._instance.is_on != None

    @property
    def name(self) -> str:
        return self._attr_name

    @property
    def unique_id(self) -> str:
        """Return the unique id."""
        return self._attr_unique_id

    @property
    def native_value(self) -> int | None:
        return self._effect_speed

    @property
    def device_info(self):
        """Return device info."""
        return DeviceInfo(
            identifiers={
                # Serial numbers are unique identifiers within a specific domain
                (DOMAIN, self._instance.address)
            },
            name=self.name,
            connections={(device_registry.CONNECTION_NETWORK_MAC,
                          self._instance.address)},
        )

    @property
    def entity_info(self):
        NumberEntityDescription(
            key=self.name,
            native_max_value=255,
            native_min_value=0,
        )

    async def async_set_native_value(self, value: float) -> None:
        """Update the current value."""
        await self._instance.set_effect_speed(int(value))
        self._effect_speed = value