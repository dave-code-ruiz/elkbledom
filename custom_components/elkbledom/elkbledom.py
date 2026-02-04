import asyncio
import datetime
import traceback
import logging
from typing import Any, TypeVar, cast, Tuple, Optional, Dict, List
from collections.abc import Callable
from homeassistant.exceptions import ConfigEntryNotReady

from bleak.backends.device import BLEDevice
from bleak.backends.service import BleakGATTServiceCollection
from bleak.exc import BleakDBusError
from bleak_retry_connector import BLEAK_RETRY_EXCEPTIONS as BLEAK_EXCEPTIONS
from bleak_retry_connector import (
    BleakClientWithServiceCache,
    BleakNotFoundError,
    establish_connection,
)
from homeassistant.components.bluetooth import async_discovered_service_info, async_ble_device_from_address
from home_assistant_bluetooth import BluetoothServiceInfo

from .model import Model

LOGGER = logging.getLogger(__name__)

#gatttool -i hci0 -b be:59:7a:00:08:d5 --char-write-req -a 0x0009 -n 7e00040100000000ef POWERON
# sudo gatttool -b be:59:7a:00:08:d5 --char-write-req -a 0x0009 -n 7e0004f00001ff00ef # POWER ON
# sudo gatttool -b be:59:7a:00:08:d5 --char-write-req -a 0x0009 -n 7e000503ff000000ef # RED
# sudo gatttool -b be:59:7a:00:08:d5 --char-write-req -a 0x0009 -n 7e0005030000ff00ef # BLUE
# sudo gatttool -b be:59:7a:00:08:d5 --char-write-req -a 0x0009 -n 7e00050300ff0000ef # GREEN
# sudo gatttool -b be:59:7a:00:08:d5 --char-write-req -a 0x0009 -n 7e0004000000ff00ef # POWER OFF


DEFAULT_ATTEMPTS = 3
#DISCONNECT_DELAY = 120
BLEAK_BACKOFF_TIME = 0.25
RETRY_BACKOFF_EXCEPTIONS = (BleakDBusError,)
WrapFuncType = TypeVar("WrapFuncType", bound=Callable[..., Any])

def retry_bluetooth_connection_error(func: WrapFuncType) -> WrapFuncType:
    """Define a wrapper to retry on bleak error.

    The accessory is allowed to disconnect us any time so
    we need to retry the operation.
    """

    async def _async_wrap_retry_bluetooth_connection_error(
        self: "BLEDOMInstance", *args: Any, **kwargs: Any
    ) -> Any:
        # LOGGER.debug("%s: Starting retry loop", self.name)
        attempts = DEFAULT_ATTEMPTS
        max_attempts = attempts - 1

        for attempt in range(attempts):
            try:
                return await func(self, *args, **kwargs)
            except BleakNotFoundError:
                # The lock cannot be found so there is no
                # point in retrying.
                raise
            except RETRY_BACKOFF_EXCEPTIONS as err:
                if attempt >= max_attempts:
                    LOGGER.debug("%s: %s error calling %s, reach max attempts (%s/%s)",self.name,type(err),func,attempt,max_attempts,exc_info=True,)
                    raise
                LOGGER.debug("%s: %s error calling %s, backing off %ss, retrying (%s/%s)...",self.name,type(err),func,BLEAK_BACKOFF_TIME,attempt,max_attempts,exc_info=True,)
                await asyncio.sleep(BLEAK_BACKOFF_TIME)
            except BLEAK_EXCEPTIONS as err:
                if attempt >= max_attempts:
                    LOGGER.debug("%s: %s error calling %s, reach max attempts (%s/%s): %s",self.name,type(err),func,attempt,max_attempts,err,exc_info=True,)
                    raise
                LOGGER.debug("%s: %s error calling %s, retrying  (%s/%s)...: %s",self.name,type(err),func,attempt,max_attempts,err,exc_info=True,)

    return cast(WrapFuncType, _async_wrap_retry_bluetooth_connection_error)

class CharacteristicMissingError(Exception):
    """Raised when a characteristic is missing."""
class DeviceData():
    def __init__(self, hass, discovery_info):
        self._discovery = discovery_info
        model_manager = Model(hass)
        detected_model = model_manager.detect_model(self._discovery.name or "")
        self._supported = detected_model is not None
        self._address = self._discovery.address
        self._name = self._discovery.name
        self._rssi = self._discovery.rssi
        self._hass = hass
        self._bledevice = async_ble_device_from_address(hass, self._address)
        
    @property
    def is_supported(self) -> bool:
        return self._supported

    @property
    def address(self):
        return self._address

    @property
    def get_device_name(self):
        return self._name

    @property
    def name(self):
        return self._name

    @property
    def rssi(self):
        return self._rssi
    
    def bledevice(self) -> BLEDevice:
        return self._bledevice
    
    def update_device(self):
        #TODO for discovery_info in async_last_service_info(self._hass, self._address):
        for discovery_info in async_discovered_service_info(self._hass):
            if discovery_info.address == self._address:
                self._rssi = discovery_info.rssi
                ##TODO SOMETHING WITH DEVICE discovery_info
        return

    def _start_update(self, service_info: BluetoothServiceInfo) -> None:
        """Update from BLE advertisement data."""
        LOGGER.debug("Parsing Govee BLE advertisement data: %s", service_info)

class BLEDOMInstance:
    def __init__(self, address, reset: bool, delay: int, hass, forced_model: str = None) -> None:
        self.loop = asyncio.get_running_loop()
        self._address = address
        self._reset = reset
        self._delay = delay
        self._hass = hass
        self._forced_model = forced_model
        self._device: BLEDevice | None = None
        self._device_data: DeviceData | None = None
        self._connect_lock: asyncio.Lock = asyncio.Lock()
        self._client: BleakClientWithServiceCache | None = None
        self._disconnect_timer: asyncio.TimerHandle | None = None
        self._cached_services: BleakGATTServiceCollection | None = None
        self._expected_disconnect = False
        self._is_on = None
        self._rgb_color = None
        self._rgb_color_base = (255, 255, 255)  # Base RGB without brightness scaling
        self._brightness = 255
        self._effect = None
        self._effect_speed = 128  # Default medium speed (0-255 range)
        self._color_temp_kelvin = None
        self._mic_effect = None
        self._mic_sensitivity = 50
        self._mic_enabled = False
        self._model = None
        self._model_name = None
        self._color_temp = None
        self._read_uuid = None
        self._write_uuid = None
        
        # New: Brightness mode configuration
        self._brightness_mode = "auto"  # auto, rgb, native
        

        try:
            self._device = async_ble_device_from_address(hass, self._address)
        except (Exception) as error:
            LOGGER.error("Error getting device: %s", error)

        for discovery_info in async_discovered_service_info(hass):
            if discovery_info.address == address:
                devicedata = DeviceData(hass, discovery_info)
                #LOGGER.debug("device %s: %s %s",devicedata.name, devicedata.address, devicedata.rssi)
                if devicedata.is_supported:
                    self._device_data = devicedata
        
        if not self._device:
            raise ConfigEntryNotReady(f"You need to add bluetooth integration (https://www.home-assistant.io/integrations/bluetooth) or couldn't find a nearby device with address: {address}")
            
        # self._adv_data: AdvertisementData | None = None
        self._detect_model()
        LOGGER.debug('Model information for device %s : ModelNo %s, Turn on cmd %s, Turn off cmd %s, rssi %s', 
                     self._device.name, self._model_name, 
                     self._model.get_turn_on_cmd(self._model_name), 
                     self._model.get_turn_off_cmd(self._model_name), 
                     self.rssi)
        
    def _detect_model(self, char_handle: Optional[int] = None):
        """Detect the model using Model manager.
        
        Args:
            char_handle: Optional characteristic handle for refined detection
        """
        if not hasattr(self, '_model') or self._model is None:
            self._model = Model(self._hass)
        
        # Use forced model if provided, otherwise auto-detect
        if self._forced_model:
            self._model_name = self._forced_model
            LOGGER.info("%s: Using forced model: %s", self._device.name, self._forced_model)
        elif char_handle is not None:
            # Use handle-based detection when available
            detected = self._model.detect_model_by_handle(self._device.name or "", char_handle)
            if detected:
                if hasattr(self, '_model_name') and self._model_name and detected != self._model_name:
                    LOGGER.info("%s: Model refined from '%s' to '%s' based on handle 0x%04x", 
                               self._device.name, self._model_name, detected, char_handle)
                self._model_name = detected
            else:
                LOGGER.warning("Unknown model for device %s with handle 0x%04x", self._device.name, char_handle)
                self._model_name = "ELK-BLEDOM"  # Default fallback
        else:
            # Standard name-based detection
            self._model_name = self._model.detect_model(self._device.name or "")
            LOGGER.debug("%s: Auto-detected model: %s", self._device.name, self._model_name)
        
        if not self._model_name:
            LOGGER.warning("Unknown model for device %s", self._device.name)
            self._model_name = "ELK-BLEDOM"  # Default fallback
    
    async def apply_brightness_mode(self, mode: str):
        """Apply new brightness mode and reconnect if needed."""
        mode = (mode or "auto").lower()
        if mode not in ("auto", "rgb", "native"):
            mode = "auto"
        if mode == self._brightness_mode:
            return
        self._brightness_mode = mode
        LOGGER.info("%s: Brightness mode changed to: %s", self.name, mode)

    def get_color_base(self):
        return self._rgb_color_base
            
    async def _write(self, data: bytearray):
        """Send command to device and read response."""
        await self._ensure_connected()
        await self._write_while_connected(data)

    async def _write_while_connected(self, data: bytearray):
        LOGGER.debug(''.join(format(x, ' 03x') for x in data))
        await self._client.write_gatt_char(self._write_uuid, data, False)

    @property
    def address(self):
        return self._address

    @property
    def reset(self):
        return self._reset

    @property
    def name(self):
        return self._device.name

    @property
    def rssi(self):
        return 0 if self._device_data is None else self._device_data.rssi

    @property
    def is_on(self):
        return self._is_on

    @property
    def rgb_color(self):
        return self._rgb_color

    @property
    def brightness(self):
        return self._brightness
    
    @property
    def min_color_temp_kelvin(self):
        return self._model.get_min_color_temp_kelvin(self._model_name)
    
    @property
    def max_color_temp_kelvin(self):
        return self._model.get_max_color_temp_kelvin(self._model_name)
    
    @property
    def color_temp_kelvin(self):
        return self._color_temp_kelvin


    @property
    def effect(self):
        return self._effect
    
    @property
    def effect_speed(self):
        return self._effect_speed
    
    @property
    def mic_effect(self):
        return self._mic_effect
    
    @property
    def mic_sensitivity(self):
        return self._mic_sensitivity
    
    @property
    def mic_enabled(self):
        return self._mic_enabled
    
    @property
    def model_name(self):
        return self._model_name
    
    @property
    def model(self):
        return self._model
    
    @retry_bluetooth_connection_error
    async def set_color_temp(self, value: int):
        if value > 100:
            value = 100
        warm = value
        cold = 100 - value
        color_temp_cmd = self._model.get_color_temp_cmd(self._model_name, warm, cold)
        await self._write(color_temp_cmd)
        self._color_temp = warm

    @retry_bluetooth_connection_error
    async def set_color_temp_kelvin(self, value: int, brightness: int):
        # White colours are represented by colour temperature percentage from 0x0 to 0x64 from warm to cool
        # Warm (0x0) is only the warm white LED, cool (0x64) is only the white LED and then a mixture between the two
        self._color_temp_kelvin = value
        min_temp = self._model.get_min_color_temp_kelvin(self._model_name)
        max_temp = self._model.get_max_color_temp_kelvin(self._model_name)
        if value < min_temp:
            value = min_temp
        if value > max_temp:
            value = max_temp
        
        # Ensure brightness is not None before using it
        if brightness is None:
            brightness = self._brightness if self._brightness is not None else 255
        self._brightness = brightness
        
        # 
        # if value > 5000:
        #     # For high color temperatures, use white mode
        #     intensity = max(0, min(int(brightness), 255))
        #     percent = int(intensity * 100 / 255)
        #     await self.set_white(percent)
        
        # Standard RGB-emulation for color temperature
        # color_temp_percent = int(((value - min_temp) * 100) / (max_temp - min_temp))
        # brightness_percent = int(brightness * 100 / 255)
        
        # Use RGB emulation for wider color temperature range
        warm = (255, 138, 18)  # Warm white ~1800K
        cool = (180, 220, 255)  # Cool white ~7000K
        t = (value - min_temp) / (max_temp - min_temp) if max_temp > min_temp else 1.0
        
        r = int(warm[0] + (cool[0] - warm[0]) * t)
        g = int(warm[1] + (cool[1] - warm[1]) * t)
        b = int(warm[2] + (cool[2] - warm[2]) * t)
        
        # Save the unscaled color as base color for future brightness adjustments
        self._rgb_color_base = (r, g, b)
        
        # Apply brightness scaling
        scale = brightness / 255.0
        r_scaled, g_scaled, b_scaled = int(r * scale), int(g * scale), int(b * scale)
        
        # Send scaled color but mark base color was already saved above
        await self.set_color((r_scaled, g_scaled, b_scaled), is_base_color=False)
        # Note: _rgb_color is set in set_color, but _rgb_color_base is preserved

    @retry_bluetooth_connection_error
    async def set_color(self, rgb: Tuple[int, int, int], is_base_color: bool = False):
        r, g, b = rgb
        color_cmd = self._model.get_color_cmd(self._model_name, r, g, b)
        await self._write(color_cmd)
        self._rgb_color = rgb
        # If this is a base color (not brightness-scaled), save it
        if is_base_color:
            self._rgb_color_base = rgb

    @retry_bluetooth_connection_error
    async def set_white(self, intensity: int):
        if intensity is None:
            intensity = 255  # Valor por defecto si no se especifica
        white_cmd = self._model.get_white_cmd(self._model_name, intensity)
        await self._write(white_cmd)
        self._brightness = intensity

    @retry_bluetooth_connection_error
    async def set_brightness(self, intensity: int):
        """Set brightness with configurable mode (auto/rgb/native)."""
        self._brightness = max(1, min(int(intensity), 255))
        percent = round(self._brightness * 100 / 255)
        mode = (self._brightness_mode or "auto").lower()
        
        # ALWAYS use base RGB color (not already-scaled color) to avoid cumulative scaling
        r, g, b = self._rgb_color_base
        
        async def write_rgb_scaled():
            """Scale RGB values by brightness from base color."""
            scale = self._brightness / 255.0
            rr, gg, bb = int(r * scale), int(g * scale), int(b * scale)
            # Don't save as base color, this is scaled
            await self.set_color((rr, gg, bb), is_base_color=False)
            LOGGER.debug("%s: Brightness set via RGB scaling: %d%% (Base RGB: %d,%d,%d -> Scaled: %d,%d,%d)", self.name, percent, r, g, b, rr, gg, bb)

        async def write_native_then_rgb():
            """Use native brightness command then set base color."""
            brightness_cmd = self._model.get_brightness_cmd(self._model_name, percent)
            await self._write(brightness_cmd)
            await asyncio.sleep(0.05)
            # Use base color, not scaled
            await self.set_color((r, g, b), is_base_color=False)
            LOGGER.debug("%s: Brightness set via native command: %d%%", self.name, percent)

        try:
            if mode == "rgb":
                # Always use RGB scaling
                await write_rgb_scaled()
            elif mode == "native":
                # Always use native brightness command
                await write_native_then_rgb()
            else:  # auto
                # Try native first, fallback to RGB on error
                try:
                    await write_native_then_rgb()
                except Exception as e:
                    LOGGER.warning("%s: Native brightness failed, fallback to RGB: %s", self.name, e)
                    await write_rgb_scaled()
        except Exception as e:
            LOGGER.error("%s: Error setting brightness: %s", self.name, e)  
            
    @retry_bluetooth_connection_error
    async def set_effect_speed(self, value: int):
        effect_speed = self._model.get_effect_speed_cmd(self._model_name, value)
        await self._write(effect_speed)
        self._effect_speed = value

    @retry_bluetooth_connection_error
    async def set_effect(self, value: int):
        effect = self._model.get_effect_cmd(self._model_name, value)
        await self._write(effect)
        self._effect = value

    @retry_bluetooth_connection_error
    async def set_mic_effect(self, value: int):
        """Set microphone effect (0x80-0x87)."""
        if not 0x80 <= value <= 0x87:
            LOGGER.warning("Invalid mic effect value: 0x%02x, must be between 0x80 and 0x87", value)
            return
        await self._write([0x7e, 0x05, 0x03, value, 0x04, 0xff, 0xff, 0x00, 0xef])
        self._mic_effect = value
        LOGGER.debug("Mic effect set to: 0x%02x", value)

    @retry_bluetooth_connection_error
    async def set_mic_sensitivity(self, value: int):
        """Set microphone sensitivity (0-100)."""
        if not 0 <= value <= 100:
            LOGGER.warning("Invalid mic sensitivity value: %d, must be between 0 and 100", value)
            return
        await self._write([0x7e, 0x04, 0x06, value, 0xff, 0xff, 0xff, 0x00, 0xef])
        self._mic_sensitivity = value
        LOGGER.debug("Mic sensitivity set to: %d", value)

    @retry_bluetooth_connection_error
    async def enable_mic(self):
        """Enable external microphone."""
        await self._write([0x7e, 0x04, 0x07, 0x01, 0xff, 0xff, 0xff, 0x00, 0xef])
        self._mic_enabled = True
        LOGGER.debug("External microphone enabled")

    @retry_bluetooth_connection_error
    async def disable_mic(self):
        """Disable external microphone."""
        await self._write([0x7e, 0x04, 0x07, 0x00, 0xff, 0xff, 0xff, 0x00, 0xef])
        self._mic_enabled = False
        LOGGER.debug("External microphone disabled")

    @retry_bluetooth_connection_error
    async def turn_on(self):
        cmd = self._model.get_turn_on_cmd(self._model_name)
        await self._write(cmd)
        self._is_on = True

    @retry_bluetooth_connection_error
    async def turn_off(self):
        cmd = self._model.get_turn_off_cmd(self._model_name)
        await self._write(cmd)
        self._is_on = False

    @retry_bluetooth_connection_error
    async def set_scheduler_on(self, days: int, hours: int, minutes: int, enabled: bool):
        if enabled:
            value = days + 0x80
        else:
            value = days
        await self._write([0x7e, 0x00, 0x82, hours, minutes, 0x00, 0x00, value, 0xef])

    @retry_bluetooth_connection_error
    async def set_scheduler_off(self, days: int, hours: int, minutes: int, enabled: bool):
        if enabled:
            value = days + 0x80
        else:
            value = days
        await self._write([0x7e, 0x00, 0x82, hours, minutes, 0x00, 0x01, value, 0xef])

    @retry_bluetooth_connection_error
    async def sync_time(self):
        date = datetime.date.today()
        year, week_num, day_of_week = date.isocalendar()
        now = datetime.datetime.now()
        cmd = self._model.get_sync_time_cmd(
            self._model_name,
            int(now.strftime('%H')),
            int(now.strftime('%M')),
            int(now.strftime('%S')),
            day_of_week
        )
        await self._write(cmd)

    @retry_bluetooth_connection_error
    async def custom_time(self, hour: int, minute: int, second: int, day_of_week: int):
        cmd = self._model.get_custom_time_cmd(self._model_name, hour, minute, second, day_of_week)
        await self._write(cmd)

    async def query_state(self):
        """Query device state using model-specific command."""
        if not self._client or not self._client.is_connected:
            return
        
        query_cmd = self._model.get_query_cmd(self._model_name)
        if query_cmd:
            try:
                LOGGER.debug("%s: Querying state with model command", self.name)
                await self._write_while_connected(query_cmd)
                await asyncio.sleep(0.2)
            except Exception as e:
                LOGGER.debug("%s: Query command failed: %s", self.name, e)

    @retry_bluetooth_connection_error
    async def update(self):
        try:
            await self._ensure_connected()

            # Query device state
            # if self._read_uuid and self._client and self._client.is_connected:
            #     try:
            #         await self.query_state()
            #     except Exception as e:
            #         LOGGER.debug("%s: Could not query state: %s", self.name, e)

            # PROBLEMS WITH STATUS VALUE, I HAVE NOT VALUE TO WRITE AND GET STATUS
            if(self._is_on is None):
                self._is_on = False
                self._rgb_color = (0, 0, 0)
                self._color_temp_kelvin = 5000
                self._brightness = 255

            self._device_data.update_device()
            #future = asyncio.get_event_loop().create_future()
            #await self._device.start_notify(self._read_uuid, create_status_callback(future))
            #await self._write([0x7e, 0x00, 0x01, 0xfa, 0x00, 0x00, 0x00, 0x00, 0xef])
            #await self._write([0x7e, 0x00, 0x10])
            #await self._write([0xef, 0x01, 0x77])
            #await self._write([0x10])
            #await self._write([0x25, 0x00])
            #await self._write([0x25, 0x02])
            #await asyncio.wait_for(future, 5.0)
            #await self._device.stop_notify(self._read_uuid)
            #res = future.result()
            #self._is_on = True #if res[2] == 0x23 else False if res[2] == 0x24 else None
            # self._rgb_color = (res[6], res[7], res[8])
            # self._brightness = res[9] if res[9] > 0 else None
            # LOGGER.debug(''.join(format(x, ' 03x') for x in res))
            
        except (Exception) as error:
            self._is_on = False
            LOGGER.error("Error getting status: %s", error)
            track = traceback.format_exc()
            LOGGER.debug(track)
        
    async def _ensure_connected(self) -> None:
        """Ensure connection to device is established."""
        if self._connect_lock.locked():
            LOGGER.debug(
                "%s: Connection already in progress, waiting for it to complete; RSSI: %s",
                self.name,
                self.rssi,
            )
        if self._client and self._client.is_connected:
            self._reset_disconnect_timer()
            return
        async with self._connect_lock:
            # Check again while holding the lock
            if self._client and self._client.is_connected:
                self._reset_disconnect_timer()
                return

            LOGGER.debug("%s: Connecting; RSSI: %s", self.name, self.rssi)
            try:
                client = await establish_connection(
                        BleakClientWithServiceCache,
                        self._device,
                        self.name,
                        self._disconnected,
                        cached_services=self._cached_services,
                        ble_device_callback=lambda: self._device,
                    )
            except asyncio.TimeoutError:
                LOGGER.error("%s: Connection attempt timed out; RSSI: %s", self.name, self.rssi)
                return

            LOGGER.debug("%s: Connected; RSSI: %s", self.name, self.rssi)
            
            # Execute login command BEFORE resolving characteristics for MELK/MODELX devices
            # These devices disconnect if login is not performed first
            if self._device.name.lower().startswith("melk") or self._device.name.lower().startswith("modelx"):
                LOGGER.debug("%s: Executing login procedure before service discovery; RSSI: %s", self.name, self.rssi)
                try:
                    # Get services to find write UUID for login
                    temp_services = None
                    try:
                        temp_services = client.services
                    except (AttributeError, Exception):
                        try:
                            temp_services = await client.get_services()
                        except (AttributeError, Exception) as e:
                            LOGGER.error("%s: Failed to get services: %s", self.name, e)
                            raise
                    
                    temp_write_uuid = None
                    
                    # Find write characteristic for login
                    write_uuid = self._model.get_write_uuid(self._model_name)
                    if write_uuid and (char := temp_services.get_characteristic(write_uuid)):
                        temp_write_uuid = str(char.uuid)  # Ensure it's a string
                        LOGGER.debug("%s: Found write UUID for login: %s", self.name, temp_write_uuid)
                    
                    if temp_write_uuid:
                        LOGGER.info("%s: Executing login sequence...", self.name)
                        await client.write_gatt_char(temp_write_uuid, bytes([0x7e, 0x07, 0x83]), response=False)
                        await asyncio.sleep(1)
                        await client.write_gatt_char(temp_write_uuid, bytes([0x7e, 0x04, 0x04]), response=False)
                        await asyncio.sleep(1)
                        LOGGER.info("%s: Login sequence completed", self.name)
                    else:
                        LOGGER.warning("%s: Could not find write UUID for login procedure", self.name)
                except Exception as e:
                    LOGGER.error("%s: Login procedure failed: %s", self.name, e)
                    # Continue anyway, might work for some devices
            
            # Try to get services with fallback
            services_obj = None
            try:
                services_obj = client.services
            except (AttributeError, Exception):
                try:
                    services_obj = await client.get_services()
                except (AttributeError, Exception) as e:
                    LOGGER.error("%s: Failed to get services: %s", self.name, e)
                    await client.disconnect()
                    raise
            
            resolved = self._resolve_characteristics(services_obj)
            if not resolved:
                # Try to handle services failing to load
                try:
                    # Try alternate method
                    alt_services = None
                    try:
                        alt_services = await client.get_services()
                    except (AttributeError, Exception):
                        try:
                            alt_services = client.services
                        except (AttributeError, Exception) as e:
                            LOGGER.warning("%s: Could not get services with either method: %s", self.name, e)
                            raise
                    
                    if alt_services:
                        resolved = self._resolve_characteristics(alt_services)
                        self._cached_services = alt_services if resolved else None
                except (AttributeError, Exception) as error:
                    LOGGER.warning("%s: Could not resolve characteristics from services; RSSI: %s", self.name, self.rssi)
            else:
                self._cached_services = services_obj if resolved else None
            
            if not resolved:
                await client.clear_cache()
                await client.disconnect()
                raise CharacteristicMissingError(
                    "Failed to find supported characteristics, device may not be supported"
                )

            LOGGER.debug("%s: Characteristics resolved: %s; RSSI: %s", self.name, resolved, self.rssi)

            self._client = client
            self._reset_disconnect_timer()

            # Enable notifications (simple method, no manual CCCD)
            try:
                if not self._device.name.lower().startswith("melk") and not self._device.name.lower().startswith("ledble"):
                    if self._read_uuid is not None and isinstance(self._read_uuid, str) and self._read_uuid.lower() != "none":
                        LOGGER.debug("%s: Enabling notifications; RSSI: %s", self.name, self.rssi)
                        await client.start_notify(self._read_uuid, self._notification_handler)
                        LOGGER.info("%s: Notifications enabled", self.name)
                    else:
                        LOGGER.warning("%s: Read UUID not resolved (value: %s), skipping notifications", self.name, self._read_uuid)
            except Exception as e:
                LOGGER.warning("%s: Notifications could not be enabled: %s", self.name, e)



    def _notification_handler(self, _sender: int, data: bytearray) -> None:
        """Handle notification responses."""
        self._notification_received = True  # Mark that we got a response
        LOGGER.info("%s: ✓ Notification received (%d bytes): %s", self.name, len(data), ' '.join(f'{x:02x}' for x in data))
        
        # Parse notification data if available
        if len(data) >= 9 and data[0] == 0x7e and data[8] == 0xef:
            # Valid response packet
            cmd_type = data[2]
            
            # Status response (0x01)
            if cmd_type == 0x01:
                # Power state might be in data[3]
                power_state = data[3]
                if power_state in [0x23, 0xf0, 0x01]:
                    self._is_on = True
                    LOGGER.debug("%s: Parsed power state: ON", self.name)
                elif power_state in [0x24, 0x00]:
                    self._is_on = False
                    LOGGER.debug("%s: Parsed power state: OFF", self.name)
                
                # Try to parse RGB color if available
                if len(data) >= 8:
                    r, g, b = data[4], data[5], data[6]
                    if r != 0xff or g != 0xff or b != 0xff:  # Not default/invalid values
                        self._rgb_color = (r, g, b)
                        LOGGER.debug("%s: Parsed RGB color: (%d, %d, %d)", self.name, r, g, b)
                
                # Brightness might be in data[7]
                if len(data) >= 8 and data[7] != 0xff:
                    brightness_percent = data[7]
                    self._brightness = int(brightness_percent * 255 / 100)
                    LOGGER.debug("%s: Parsed brightness: %d%%", self.name, brightness_percent)
        
        return

    def _resolve_characteristics(self, services: BleakGATTServiceCollection) -> bool:
        """Resolve characteristics."""
        if not services:
            LOGGER.debug("%s: No services provided to resolve characteristics, dont should works", self.name)
        
        # Log all available characteristics for debugging
        LOGGER.debug("%s: Available services and characteristics:", self.name)
        for service in services:
            LOGGER.debug("%s: Service %s", self.name, service.uuid)
            for char in service.characteristics:
                LOGGER.debug("%s:   Characteristic %s (properties: %s)", self.name, char.uuid, char.properties)
        
        # Try to find read characteristic
        read_uuid = self._model.get_read_uuid(self._model_name)
        if read_uuid and (char := services.get_characteristic(read_uuid)):
            self._read_uuid = str(char.uuid)  # Ensure it's a string
            LOGGER.debug("%s: Found read UUID: %s with handle %s", self.name, self._read_uuid, char.handle if hasattr(char, 'handle') else 'Unknown')
        else:
            self._read_uuid = None
            LOGGER.warning("%s: Could not find read characteristic: %s", self.name, read_uuid)
        
        # Try to find write characteristic
        write_uuid = self._model.get_write_uuid(self._model_name)
        if write_uuid and (char := services.get_characteristic(write_uuid)):
            self._write_uuid = str(char.uuid)  # Ensure it's a string
            char_handle = char.handle if hasattr(char, 'handle') else None
            LOGGER.debug("%s: Found write UUID: %s with handle %s", self.name, self._write_uuid, f"0x{char_handle:04x}" if char_handle else 'Unknown')
            
            # Re-detect model based on handle if available
            if char_handle is not None:
                self._detect_model(char_handle)
                # Update write_uuid in case model changed
                write_uuid = self._model.get_write_uuid(self._model_name)
                if write_uuid:
                    self._write_uuid = str(write_uuid)
        else:
            self._write_uuid = None
            LOGGER.error("%s: Could not find write characteristic: %s", self.name, write_uuid)
        
        # For devices like MELK that don't use notifications, only write_uuid is required
        if self._device.name.lower().startswith("melk") or self._device.name.lower().startswith("modelx"):
            result = bool(self._write_uuid)
            LOGGER.debug("%s: Device doesn't require read UUID, resolved: %s", self.name, result)
            return result
        
        return bool(self._read_uuid and self._write_uuid)

    def _reset_disconnect_timer(self) -> None:
        """Reset disconnect timer."""
        if self._disconnect_timer:
            self._disconnect_timer.cancel()
        self._expected_disconnect = False
        if self._delay is not None and self._delay != 0:
            LOGGER.debug("%s: Configured disconnect from device in %s seconds; RSSI: %s", self.name, self._delay, self.rssi)
            self._disconnect_timer = self.loop.call_later(
                self._delay, self._disconnect
            )

    def _disconnected(self, client: BleakClientWithServiceCache) -> None:
        """Disconnected callback."""
        if self._expected_disconnect:
            LOGGER.debug("%s: Disconnected from device; RSSI: %s", self.name, self.rssi)
            return
        LOGGER.warning("%s: Device unexpectedly disconnected; RSSI: %s",self.name,self.rssi,)

    def _disconnect(self) -> None:
        """Disconnect from device."""
        self._disconnect_timer = None
        asyncio.create_task(self._execute_timed_disconnect())

    async def stop(self) -> None:
        """Stop the LEDBLE."""
        LOGGER.debug("%s: Stop", self.name)
        await self._execute_disconnect()

    async def _execute_timed_disconnect(self) -> None:
        """Execute timed disconnection."""
        LOGGER.debug(
            "%s: Disconnecting after timeout of %s",
            self.name,
            self._delay,
        )
        await self._execute_disconnect()
    async def _execute_disconnect(self) -> None:
        """Execute disconnection."""
        async with self._connect_lock:
            read_char = self._read_uuid if hasattr(self, '_read_uuid') else None
            client = self._client
            LOGGER.debug("Disconnecting: READ_UUID=%s, CLIENT_CONNECTED=%s", read_char, client.is_connected if client else "No Client")
            self._expected_disconnect = True
            self._client = None
            self._write_uuid = None
            self._read_uuid = None
            if client and client.is_connected:
                try:
                    if read_char and not self._device.name.lower().startswith("melk") and not self._device.name.lower().startswith("ledble"):
                        await client.stop_notify(read_char)
                    await client.disconnect()
                except Exception as e:
                    LOGGER.error("Error during disconnection: %s", e)