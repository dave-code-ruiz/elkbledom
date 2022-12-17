import asyncio
from .elkbledom import BLEDOMInstance
from typing import Any

from homeassistant import config_entries
from homeassistant.const import CONF_MAC
import voluptuous as vol
from homeassistant.helpers.device_registry import format_mac
from homeassistant.data_entry_flow import FlowResult
from homeassistant.components.bluetooth import (
    BluetoothServiceInfoBleak,
    async_discovered_service_info,
)
from bluetooth_sensor_state_data import BluetoothData
from home_assistant_bluetooth import BluetoothServiceInfo

from .const import DOMAIN
import logging

LOGGER = logging.getLogger(__name__)
DATA_SCHEMA = vol.Schema({("host"): str})

MANUAL_MAC = "manual"

class DeviceData(BluetoothData):
    def __init__(self, discovery_info) -> None:
        self._discovery = discovery_info

    def supported(self):
        return self._discovery.name.lower().startswith("elk-bledom") or self._discovery.name.lower().startswith("ledble")

    def address(self):
        return self._discovery.address

    def get_device_name(self):
        return self._discovery.name

    def name(self):
        return self._discovery.name

    def rssi(self):
        return self._discovery.rssi

    def _start_update(self, service_info: BluetoothServiceInfo) -> None:
        """Update from BLE advertisement data."""
        LOGGER.debug("Parsing Govee BLE advertisement data: %s", service_info)
        
class BLEDOMFlowHandler(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1
    CONNECTION_CLASS = config_entries.CONN_CLASS_LOCAL_POLL

    def __init__(self) -> None:
        self.mac = None
        self._device = None
        self._instance = None
        self.name = None
        self._discovery_info: BluetoothServiceInfoBleak | None = None
        self._discovered_device: DeviceData | None = None
        self._discovered_devices = []

    async def async_step_bluetooth(
        self, discovery_info: BluetoothServiceInfoBleak
    ) -> FlowResult:
        """Handle the bluetooth discovery step."""
        LOGGER.debug("Discovered bluetooth devices, step bluetooth, : %s", discovery_info)
        await self.async_set_unique_id(discovery_info.address)
        self._abort_if_unique_id_configured()
        device = DeviceData(discovery_info)
        if not device.supported():
            return self.async_abort(reason="not_supported")
        self._discovery_info = discovery_info
        self._discovered_device = device
        return await self.async_step_bluetooth_confirm()

    async def async_step_bluetooth_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Confirm discovery."""
        LOGGER.debug("Discovered bluetooth devices, step bluetooth confirm, : %s", user_input)
        assert self._discovered_device is not None
        device = self._discovered_device
        assert self._discovery_info is not None
        discovery_info = self._discovery_info
        title = device.title or device.get_device_name() or discovery_info.name
        if user_input is not None:
            return self.async_create_entry(title=self.name, data={CONF_MAC: self.mac, "name": self.name})

        self._set_confirm_only()
        placeholders = {"name": title}
        self.context["title_placeholders"] = placeholders
        return await self.async_step_user()
    
    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the user step to pick discovered device."""
        if user_input is not None:
            if user_input[CONF_MAC] == MANUAL_MAC:
                return await self.async_step_manual()
            self.mac = user_input[CONF_MAC]
            self.name = user_input["name"]
            await self.async_set_unique_id(self.mac, raise_on_progress=False)
            self._abort_if_unique_id_configured()
            return await self.async_step_validate()

        current_addresses = self._async_current_ids()
        for discovery_info in async_discovered_service_info(self.hass):
            self.mac = discovery_info.address
            if self.mac in current_addresses:
                LOGGER.debug("Device %s in current_addresses", (self.mac))
                continue
            if (device for device in self._discovered_devices if device.address == self.mac) == ([]):
                LOGGER.debug("Device %s in discovered_devices", (device))
                continue
            device = DeviceData(discovery_info)
            if device.supported():
                self._discovered_devices.append(device)
        
        if not self._discovered_devices:
            return await self.async_step_manual()

        LOGGER.debug("Discovered supported devices: %s - %s", self._discovered_devices[0].name(), self._discovered_devices[0].address())

        mac_dict = { dev.address(): dev.name() for dev in self._discovered_devices }
        mac_dict[MANUAL_MAC] = "Manually add a MAC address"
        return self.async_show_form(
            step_id="user", data_schema=vol.Schema(
                {
                    vol.Required(CONF_MAC): vol.In(mac_dict),
                    vol.Required("name"): str
                }
            ),
            errors={})

    async def async_step_validate(self, user_input: "dict[str, Any] | None" = None):
        if user_input is not None:
            if "flicker" in user_input:
                if user_input["flicker"]:
                    return self.async_create_entry(title=self.name, data={CONF_MAC: self.mac, "name": self.name})
                return self.async_abort(reason="cannot_validate")
            
            if "retry" in user_input and not user_input["retry"]:
                return self.async_abort(reason="cannot_connect")

        error = await self.toggle_light()

        if error:
            return self.async_show_form(
                step_id="validate", data_schema=vol.Schema(
                    {
                        vol.Required("retry"): bool
                    }
                ), errors={"base": "connect"})
        
        return self.async_show_form(
            step_id="validate", data_schema=vol.Schema(
                {
                    vol.Required("flicker"): bool
                }
            ), errors={})

    async def async_step_manual(self, user_input: "dict[str, Any] | None" = None):
        if user_input is not None:            
            self.mac = user_input[CONF_MAC]
            self.name = user_input["name"]
            await self.async_set_unique_id(format_mac(self.mac))
            return await self.async_step_validate()

        return self.async_show_form(
            step_id="manual", data_schema=vol.Schema(
                {
                    vol.Required(CONF_MAC): str,
                    vol.Required("name"): str
                }
            ), errors={})

    async def toggle_light(self):
        if not self._instance:
            self._instance = BLEDOMInstance(self.mac, self.hass)
        try:
            await self._instance.update()
            if self._instance.is_on:
                await self._instance.turn_off()
                await asyncio.sleep(2)
                await self._instance.turn_on()
                await asyncio.sleep(2)
                await self._instance.turn_off()
            else:
                await self._instance.turn_on()
                await asyncio.sleep(2)
                await self._instance.turn_off()
        except (Exception) as error:
            return error
        finally:
            await self._instance.stop()
