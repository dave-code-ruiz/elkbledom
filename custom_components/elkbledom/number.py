from __future__ import annotations

from homeassistant.components.number import (
    NumberEntity,
    NumberEntityDescription,
)

from .elkbledom import BLEDOMInstance
from .const import DOMAIN

from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.restore_state import RestoreEntity
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
    async_add_entities([
        BLEDOMEffectSpeed(instance, "Effect Speed " + config_entry.data["name"], config_entry.entry_id),
        BLEDOMMicSensitivity(instance, "Mic Sensitivity " + config_entry.data["name"], config_entry.entry_id)
    ])

class BLEDOMEffectSpeed(RestoreEntity, NumberEntity):
    """Effect Speed entity"""

    def __init__(self, bledomInstance: BLEDOMInstance, attr_name: str, entry_id: str) -> None:
        self._instance = bledomInstance
        self._attr_name = attr_name
        self._attr_unique_id = self._instance.address + "_effect_speed"
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
        # Sync with instance value
        if self._instance.effect_speed is not None:
            return self._instance.effect_speed
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
        self._effect_speed = int(value)
        self.async_write_ha_state()

    async def async_added_to_hass(self) -> None:
        """Restore previous state when entity is added to hass."""
        await super().async_added_to_hass()
        
        # Restore the last known effect speed
        if (last_state := await self.async_get_last_state()) is not None:
            try:
                self._effect_speed = int(float(last_state.state))
                LOG.debug(f"Restored effect speed for {self.name}: {self._effect_speed}")
            except (ValueError, TypeError):
                LOG.debug(f"Could not restore effect speed for {self.name}, using default")

class BLEDOMMicSensitivity(RestoreEntity, NumberEntity):
    """Microphone Sensitivity entity"""

    def __init__(self, bledomInstance: BLEDOMInstance, attr_name: str, entry_id: str) -> None:
        self._instance = bledomInstance
        self._attr_name = attr_name
        self._attr_unique_id = self._instance.address + "_mic_sensitivity"
        self._mic_sensitivity = 50

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
        return self._mic_sensitivity

    @property
    def native_min_value(self) -> int:
        return 0

    @property
    def native_max_value(self) -> int:
        return 100

    @property
    def native_step(self) -> int:
        return 1

    @property
    def device_info(self):
        """Return device info."""
        return DeviceInfo(
            identifiers={
                (DOMAIN, self._instance.address)
            },
            name=self.name,
            connections={(device_registry.CONNECTION_NETWORK_MAC,
                          self._instance.address)},
        )

    async def async_set_native_value(self, value: float) -> None:
        """Update the current value."""
        await self._instance.set_mic_sensitivity(int(value))
        self._mic_sensitivity = int(value)

    async def async_added_to_hass(self) -> None:
        """Restore previous state when entity is added to hass."""
        await super().async_added_to_hass()
        
        # Restore the last known mic sensitivity
        if (last_state := await self.async_get_last_state()) is not None:
            try:
                self._mic_sensitivity = int(float(last_state.state))
                LOG.debug(f"Restored mic sensitivity for {self.name}: {self._mic_sensitivity}")
            except (ValueError, TypeError):
                LOG.debug(f"Could not restore mic sensitivity for {self.name}, using default (50)")
        else:
            LOG.debug(f"No previous state found for {self.name}")