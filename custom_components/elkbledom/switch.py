from __future__ import annotations

from typing import Any

from homeassistant.components.switch import SwitchEntity
from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.restore_state import RestoreEntity
from homeassistant.helpers import device_registry

from .elkbledom import BLEDOMInstance
from .const import DOMAIN

import logging

LOG = logging.getLogger(__name__)

async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    instance = hass.data[DOMAIN][config_entry.entry_id]
    entities = [
        BLEDOMMicSwitch(instance, "Mic Enable " + config_entry.data["name"], config_entry.entry_id)
    ]
    if instance.model.get_motor_power_cmd(instance.model_name, True):
        entities.append(
            BLEDOMMotorSwitch(instance, "Flicker " + config_entry.data["name"], config_entry.entry_id)
        )
    async_add_entities(entities)

class BLEDOMMicSwitch(RestoreEntity, SwitchEntity):
    """Microphone Enable/Disable switch entity"""

    def __init__(self, bledomInstance: BLEDOMInstance, attr_name: str, entry_id: str) -> None:
        self._instance = bledomInstance
        self._attr_name = attr_name
        self._attr_unique_id = self._instance.address + "_mic_enable"
        self._is_on = False

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
    def is_on(self) -> bool:
        return self._is_on

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

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn the microphone on."""
        await self._instance.enable_mic()
        self._is_on = True
        LOG.debug(f"Microphone enabled for {self.name}")

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn the microphone off."""
        await self._instance.disable_mic()
        self._is_on = False
        LOG.debug(f"Microphone disabled for {self.name}")

    async def async_added_to_hass(self) -> None:
        """Restore previous state when entity is added to hass."""
        await super().async_added_to_hass()
        
        # Restore the last known mic state
        if (last_state := await self.async_get_last_state()) is not None:
            if last_state.state == "on":
                self._is_on = True
                LOG.debug(f"Restored mic state for {self.name}: ON")
            elif last_state.state == "off":
                self._is_on = False
                LOG.debug(f"Restored mic state for {self.name}: OFF")
        else:
            LOG.debug(f"No previous mic state found for {self.name}, defaulting to OFF")


class BLEDOMMotorSwitch(RestoreEntity, SwitchEntity):
    """Motor on/off switch for star projectors (moves the gobo in front of the light)."""

    _attr_icon = "mdi:rotate-3d-variant"

    def __init__(self, bledomInstance: BLEDOMInstance, attr_name: str, entry_id: str) -> None:
        self._instance = bledomInstance
        self._attr_name = attr_name
        self._attr_unique_id = self._instance.address + "_motor"

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
    def is_on(self) -> bool:
        return self._instance._motor_on

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

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Start the motor."""
        await self._instance.set_motor_power(True)
        self.async_write_ha_state()

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Stop the motor."""
        await self._instance.set_motor_power(False)
        self.async_write_ha_state()

    async def async_added_to_hass(self) -> None:
        """Restore the last known motor state (the lamp can't be queried for it)."""
        await super().async_added_to_hass()
        if (last_state := await self.async_get_last_state()) is not None:
            self._instance._motor_on = last_state.state == "on"
