import asyncio
from .elkbledom import discover, BLEDOMInstance
from typing import Any

from homeassistant import config_entries
from homeassistant.const import CONF_MAC
import voluptuous as vol
from homeassistant.helpers.device_registry import format_mac
from .const import DOMAIN
import logging

LOGGER = logging.getLogger(__name__)
DATA_SCHEMA = vol.Schema({("host"): str})

MANUAL_MAC = "manual"

class BLEDOMFlowHandler(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1
    CONNECTION_CLASS = config_entries.CONN_CLASS_LOCAL_POLL

    def __init__(self) -> None:
        self.mac = None
        self._instance = None
        self.name = None

    async def async_step_user(self, user_input=None):
        """Handle the initial step."""
        if user_input is not None:
            if user_input["mac"] == MANUAL_MAC:
                return await self.async_step_manual()
            
            self.mac = user_input["mac"]
            self.name = user_input["name"]
            await self.async_set_unique_id(format_mac(self.mac))
            return await self.async_step_validate()

        already_configured = self._async_current_ids(False)
        devices = await discover()
        devices = [device for device in devices if format_mac(device.address) not in already_configured]

        if not devices:
            return await self.async_step_manual()
        
        return self.async_show_form(
            step_id="user", data_schema=vol.Schema(
                {
                    vol.Required("mac"): vol.In(
                        {
                            **{device.address: device.name for device in devices},
                            MANUAL_MAC: "Manually add a MAC address",
                        }
                    ),
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
            self.mac = user_input["mac"]
            self.name = user_input["name"]
            await self.async_set_unique_id(format_mac(self.mac))
            return await self.async_step_validate()

        return self.async_show_form(
            step_id="manual", data_schema=vol.Schema(
                {
                    vol.Required("mac"): str,
                    vol.Required("name"): str
                }
            ), errors={})

    async def toggle_light(self):
        if not self._instance:
            self._instance = BLEDOMInstance(self.mac)
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
            await self._instance.disconnect()
