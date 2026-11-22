from __future__ import annotations

import random
import voluptuous as vol

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, Event, ServiceCall
from homeassistant.exceptions import ServiceValidationError
from homeassistant.const import CONF_MAC, EVENT_HOMEASSISTANT_STOP, ATTR_ENTITY_ID
from homeassistant.const import Platform
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers import entity_registry as er

from .const import DOMAIN, CONF_RESET, CONF_DELAY, CONF_MODEL
from .elkbledom import BLEDOMInstance
from .model import ensure_models_loaded
import logging

LOGGER = logging.getLogger(__name__)
PLATFORMS: list[Platform] = [
    Platform.LIGHT,
    Platform.NUMBER,
    Platform.SELECT,
    Platform.SWITCH,
]

# Service names
SERVICE_SET_RANDOM_COLOR = "set_random_color"
SERVICE_SET_RGB_COLOR = "set_rgb_color"
SERVICE_SEND_RAW = "send_raw"

# Largest single write accepted by send_raw. BLE writes are limited by the
# negotiated MTU; most controllers in this family use 9-byte commands.
MAX_RAW_COMMAND_BYTES = 244

# Service schemas
SERVICE_SET_RANDOM_COLOR_SCHEMA = vol.Schema({
    vol.Required(ATTR_ENTITY_ID): cv.entity_ids,
    vol.Optional("brightness", default=255): vol.All(vol.Coerce(int), vol.Range(min=0, max=255)),
})

SERVICE_SET_RGB_COLOR_SCHEMA = vol.Schema({
    vol.Required(ATTR_ENTITY_ID): cv.entity_ids,
    vol.Required("r"): vol.All(vol.Coerce(int), vol.Range(min=0, max=255)),
    vol.Required("g"): vol.All(vol.Coerce(int), vol.Range(min=0, max=255)),
    vol.Required("b"): vol.All(vol.Coerce(int), vol.Range(min=0, max=255)),
    vol.Optional("brightness", default=255): vol.All(vol.Coerce(int), vol.Range(min=0, max=255)),
})

def _raw_command(value) -> list[int]:
    """Validate one raw command given as a hex string, e.g. "7e 07 31 04 07 ff ff 00 ef"."""
    text = str(value).replace(" ", "").replace(":", "").replace("-", "")
    try:
        data = bytes.fromhex(text)
    except ValueError as err:
        raise vol.Invalid(f"'{value}' is not a valid hex string") from err
    if not 1 <= len(data) <= MAX_RAW_COMMAND_BYTES:
        raise vol.Invalid(
            f"each command must be 1-{MAX_RAW_COMMAND_BYTES} bytes, got {len(data)}"
        )
    return list(data)

SERVICE_SEND_RAW_SCHEMA = vol.Schema({
    vol.Required(ATTR_ENTITY_ID): cv.entity_ids,
    vol.Required("commands"): vol.All(cv.ensure_list, vol.Length(min=1), [_raw_command]),
    vol.Optional("delay_ms", default=80): vol.All(vol.Coerce(int), vol.Range(min=0, max=5000)),
})

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up ElkBLEDOM from a config entry."""
    reset = entry.options.get(CONF_RESET, None) or entry.data.get(CONF_RESET, None)
    delay = entry.options.get(CONF_DELAY, None) or entry.data.get(CONF_DELAY, None)
    mac = entry.options.get(CONF_MAC, None) or entry.data.get(CONF_MAC, None)
    forced_model = entry.options.get(CONF_MODEL, None) or entry.data.get(CONF_MODEL, None)
    LOGGER.debug("Config: Reset: %s, Delay: %s, Mac: %s, Forced Model: %s", reset, delay, mac, forced_model)

    # Ensure models are loaded (will reuse if already in hass.data)
    await ensure_models_loaded(hass)
    
    instance = BLEDOMInstance(entry.data[CONF_MAC], reset, delay, hass, forced_model)
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = instance
   
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    entry.async_on_unload(entry.add_update_listener(_async_update_listener))

    async def _async_stop(event: Event) -> None:
        """Close the connection."""
        await instance.stop()

    entry.async_on_unload(
        hass.bus.async_listen_once(EVENT_HOMEASSISTANT_STOP, _async_stop)
    )
    
    # Register services (only once for all entries)
    if not hass.services.has_service(DOMAIN, SERVICE_SET_RANDOM_COLOR):
        async def handle_set_random_color(call: ServiceCall) -> None:
            """Handle the set_random_color service call."""
            entity_ids = call.data[ATTR_ENTITY_ID]
            brightness = call.data.get("brightness", 255)
            
            # Generate random RGB values
            r = random.randint(0, 255)
            g = random.randint(0, 255)
            b = random.randint(0, 255)
            
            # Call light.turn_on with random color for each entity
            await hass.services.async_call(
                "light",
                "turn_on",
                {
                    ATTR_ENTITY_ID: entity_ids,
                    "rgb_color": [r, g, b],
                    "brightness": brightness,
                },
                blocking=True,
            )
            LOGGER.debug(
                "Random color set to RGB(%d, %d, %d) with brightness %d for entities: %s",
                r, g, b, brightness, entity_ids
            )
        
        hass.services.async_register(
            DOMAIN,
            SERVICE_SET_RANDOM_COLOR,
            handle_set_random_color,
            schema=SERVICE_SET_RANDOM_COLOR_SCHEMA,
        )
    
    if not hass.services.has_service(DOMAIN, SERVICE_SET_RGB_COLOR):
        async def handle_set_rgb_color(call: ServiceCall) -> None:
            """Handle the set_rgb_color service call."""
            entity_ids = call.data[ATTR_ENTITY_ID]
            r = call.data["r"]
            g = call.data["g"]
            b = call.data["b"]
            brightness = call.data.get("brightness", 255)
            
            # Call light.turn_on with specified RGB color
            await hass.services.async_call(
                "light",
                "turn_on",
                {
                    ATTR_ENTITY_ID: entity_ids,
                    "rgb_color": [r, g, b],
                    "brightness": brightness,
                },
                blocking=True,
            )
            LOGGER.debug(
                "RGB color set to (%d, %d, %d) with brightness %d for entities: %s",
                r, g, b, brightness, entity_ids
            )
        
        hass.services.async_register(
            DOMAIN,
            SERVICE_SET_RGB_COLOR,
            handle_set_rgb_color,
            schema=SERVICE_SET_RGB_COLOR_SCHEMA,
        )
    
    if not hass.services.has_service(DOMAIN, SERVICE_SEND_RAW):
        async def handle_send_raw(call: ServiceCall) -> None:
            """Handle the send_raw service call."""
            ent_reg = er.async_get(hass)
            targets = []
            for entity_id in call.data[ATTR_ENTITY_ID]:
                entity_entry = ent_reg.async_get(entity_id)
                instance = (
                    hass.data.get(DOMAIN, {}).get(entity_entry.config_entry_id)
                    if entity_entry
                    else None
                )
                if instance is None:
                    raise ServiceValidationError(
                        f"{entity_id} is not an ElkBLEDOM entity"
                    )
                targets.append((entity_id, instance))

            for entity_id, instance in targets:
                await instance.send_raw(
                    call.data["commands"], call.data["delay_ms"] / 1000
                )
                LOGGER.debug(
                    "Sent %d raw command(s) to %s", len(call.data["commands"]), entity_id
                )

        hass.services.async_register(
            DOMAIN,
            SERVICE_SEND_RAW,
            handle_send_raw,
            schema=SERVICE_SEND_RAW_SCHEMA,
        )

    return True
   
async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        instance = hass.data[DOMAIN][entry.entry_id]
        await instance.stop()
    return unload_ok

async def _async_update_listener(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Handle options update."""
    instance = hass.data[DOMAIN][entry.entry_id]
    if entry.title != instance.name:
        await hass.config_entries.async_reload(entry.entry_id)
