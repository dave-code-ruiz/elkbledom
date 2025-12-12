import asyncio
from datetime import datetime
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
from typing import Any, TypeVar, cast, Tuple
from collections.abc import Callable
import traceback
import asyncio
import logging

LOGGER = logging.getLogger(__name__)

#gatttool -i hci0 -b be:59:7a:00:08:d5 --char-write-req -a 0x0009 -n 7e00040100000000ef POWERON
# sudo gatttool -b be:59:7a:00:08:d5 --char-write-req -a 0x0009 -n 7e0004f00001ff00ef # POWER ON
# sudo gatttool -b be:59:7a:00:08:d5 --char-write-req -a 0x0009 -n 7e000503ff000000ef # RED
# sudo gatttool -b be:59:7a:00:08:d5 --char-write-req -a 0x0009 -n 7e0005030000ff00ef # BLUE
# sudo gatttool -b be:59:7a:00:08:d5 --char-write-req -a 0x0009 -n 7e00050300ff0000ef # GREEN
# sudo gatttool -b be:59:7a:00:08:d5 --char-write-req -a 0x0009 -n 7e0004000000ff00ef # POWER OFF


#TODO CHANGES ARRAYS TO DICT OR MODELDB OBJECT WITH ALL MODEL INFORMATION
NAME_ARRAY = ["ELK-BLEDDM",
              "ELK-BLE",
              "LEDBLE",
              "MELK-OG10",
              "MELK",
              "ELK-BULB2",
              "ELK-BULB",
              "ELK-LAMPL"]
WRITE_CHARACTERISTIC_UUIDS = ["0000fff3-0000-1000-8000-00805f9b34fb",
                              "0000fff3-0000-1000-8000-00805f9b34fb",
                              "0000ffe1-0000-1000-8000-00805f9b34fb",
                              "0000fff3-0000-1000-8000-00805f9b34fb",
                              "0000fff3-0000-1000-8000-00805f9b34fb",
                              "0000fff3-0000-1000-8000-00805f9b34fb",
                              "0000fff3-0000-1000-8000-00805f9b34fb",
                              "0000fff3-0000-1000-8000-00805f9b34fb"]
READ_CHARACTERISTIC_UUIDS  = ["0000fff4-0000-1000-8000-00805f9b34fb",
                              "0000fff4-0000-1000-8000-00805f9b34fb",
                              "0000ffe2-0000-1000-8000-00805f9b34fb",
                              "0000fff4-0000-1000-8000-00805f9b34fb",
                              "0000fff4-0000-1000-8000-00805f9b34fb",
                              "0000fff4-0000-1000-8000-00805f9b34fb",
                              "0000fff4-0000-1000-8000-00805f9b34fb",
                              "0000fff4-0000-1000-8000-00805f9b34fb"]
TURN_ON_CMD = [[0x7e, 0x04, 0x04, 0xf0, 0x00, 0x01, 0xff, 0x00, 0xef],
               [0x7e, 0x00, 0x04, 0xf0, 0x00, 0x01, 0xff, 0x00, 0xef],
               [0x7e, 0x00, 0x04, 0x01, 0x00, 0x00, 0x00, 0x00, 0xef],
               [0x7e, 0x07, 0x04, 0xff, 0x00, 0x01, 0x02, 0x01, 0xef],
               [0x7e, 0x00, 0x04, 0x01, 0x00, 0x00, 0x00, 0x00, 0xef],
               [0x7e, 0x00, 0x04, 0xf0, 0x00, 0x01, 0xff, 0x00, 0xef],
               [0x7e, 0x00, 0x04, 0x01, 0x00, 0x00, 0x00, 0x00, 0xef],
               [0x7e, 0x00, 0x04, 0x01, 0x00, 0x00, 0x00, 0x00, 0xef]]
TURN_OFF_CMD = [[0x7e, 0x04, 0x04, 0x00, 0x00, 0x00, 0xff, 0x00, 0xef],
                [0x7e, 0x00, 0x04, 0x00, 0x00, 0x00, 0xff, 0x00, 0xef],
                [0x7e, 0x00, 0x04, 0x00, 0x00, 0x00, 0xff, 0x00, 0xef],
                [0x7e, 0x07, 0x04, 0x00, 0x00, 0x00, 0x02, 0x00, 0xef],
                [0x7e, 0x00, 0x04, 0x00, 0x00, 0x00, 0xff, 0x00, 0xef],
                [0x7e, 0x00, 0x04, 0x01, 0x00, 0x00, 0x00, 0x00, 0xef],
                [0x7e, 0x00, 0x04, 0x00, 0x00, 0x00, 0xff, 0x00, 0xef],
                [0x7e, 0x00, 0x04, 0x00, 0x00, 0x00, 0xff, 0x00, 0xef]]

WHITE_CMD = [[0x7e, 0x00, 0x01, 0xbb, 0x00, 0x00, 0x00, 0x00, 0xef],
                [0x7e, 0x00, 0x01, 0xbb, 0x00, 0x00, 0x00, 0x00, 0xef],
                [0x7e, 0x00, 0x01, 0xbb, 0x00, 0x00, 0x00, 0x00, 0xef],
                [0x7e, 0x07, 0x05, 0x01, 0xbb, 0xff, 0x02, 0x01],
                [0x7e, 0x00, 0x01, 0xbb, 0x00, 0x00, 0x00, 0x00, 0xef],
                [0x7e, 0x00, 0x01, 0xbb, 0x00, 0x00, 0x00, 0x00, 0xef],
                [0x7e, 0x00, 0x01, 0xbb, 0x00, 0x00, 0x00, 0x00, 0xef],
                [0x7e, 0x00, 0x01, 0xbb, 0x00, 0x00, 0x00, 0x00, 0xef]]

EFFECT_SPEED_CMD = [[0x7e, 0x00, 0x02, 0xbb, 0x00, 0x00, 0x00, 0x00, 0xef],
                [0x7e, 0x00, 0x02, 0xbb, 0x00, 0x00, 0x00, 0x00, 0xef],
                [0x7e, 0x00, 0x02, 0xbb, 0x00, 0x00, 0x00, 0x00, 0xef],
                [0x7e, 0x04, 0x02, 0xbb, 0xff, 0xff, 0xff, 0x00, 0xef],
                [0x7e, 0x04, 0x02, 0xbb, 0xff, 0xff, 0xff, 0x00, 0xef],
                [0x7e, 0x00, 0x02, 0xbb, 0x00, 0x00, 0x00, 0x00, 0xef],
                [0x7e, 0x00, 0x02, 0xbb, 0x00, 0x00, 0x00, 0x00, 0xef],
                [0x7e, 0x00, 0x02, 0xbb, 0x00, 0x00, 0x00, 0x00, 0xef]]

EFFECT_CMD = [[0x7e, 0x00, 0x03, 0xbb, 0x03, 0x00, 0x00, 0x00, 0xef],
                [0x7e, 0x00, 0x03, 0xbb, 0x03, 0x00, 0x00, 0x00, 0xef],
                [0x7e, 0x00, 0x03, 0xbb, 0x03, 0x00, 0x00, 0x00, 0xef],
                [0x7e, 0x05, 0x03, 0xbb, 0x06, 0xff, 0xff, 0x00, 0xef],
                [0x7e, 0x05, 0x03, 0xbb, 0x06, 0xff, 0xff, 0x00, 0xef],
                [0x7e, 0x00, 0x03, 0xbb, 0x03, 0x00, 0x00, 0x00, 0xef],
                [0x7e, 0x00, 0x03, 0xbb, 0x03, 0x00, 0x00, 0x00, 0xef],
                [0x7e, 0x00, 0x03, 0xbb, 0x03, 0x00, 0x00, 0x00, 0xef]]

COLOR_TEMP_CMD = [[0x7e, 0x00, 0x05, 0x02, 0xbb, 0xbb, 0x00, 0x00, 0xef],
                [0x7e, 0x00, 0x05, 0x02, 0xbb, 0xbb, 0x00, 0x00, 0xef],
                [0x7e, 0x00, 0x05, 0x02, 0xbb, 0xbb, 0x00, 0x00, 0xef],
                [0x7e, 0x06, 0x05, 0x02, 0xbb, 0xbb, 0xff, 0x08, 0xef],
                [0x7e, 0x06, 0x05, 0x02, 0xbb, 0xbb, 0xff, 0x08, 0xef],
                [0x7e, 0x00, 0x05, 0x02, 0xbb, 0xbb, 0x00, 0x00, 0xef],
                [0x7e, 0x00, 0x05, 0x02, 0xbb, 0xbb, 0x00, 0x00, 0xef],
                [0x7e, 0x00, 0x05, 0x02, 0xbb, 0xbb, 0x00, 0x00, 0xef]]


MIN_COLOR_TEMPS_K = [2700,2700,2700,2700,2700,2700,2700,2700]
MAX_COLOR_TEMPS_K = [6500,6500,6500,6500,6500,6500,6500,6500]

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
        self._supported = any(self._discovery.name.lower().startswith(option.lower()) for option in NAME_ARRAY)
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
    def __init__(self, address, reset: bool, delay: int, hass) -> None:
        self.loop = asyncio.get_running_loop()
        self._address = address
        self._reset = reset
        self._delay = delay
        self._hass = hass
        self._device: BLEDevice | None = None
        self._device_data: DeviceData | None = None
        self._connect_lock: asyncio.Lock = asyncio.Lock()
        self._client: BleakClientWithServiceCache | None = None
        self._disconnect_timer: asyncio.TimerHandle | None = None
        self._cached_services: BleakGATTServiceCollection | None = None
        self._expected_disconnect = False
        self._is_on = None
        self._rgb_color = None
        self._brightness = 255
        self._effect = None
        self._effect_speed = 128  # Default medium speed (0-255 range)
        self._color_temp_kelvin = None
        self._mic_effect = None
        self._mic_sensitivity = 50
        self._mic_enabled = False
        self._write_uuid = None
        self._read_uuid = None
        self._turn_on_cmd = None
        self._turn_off_cmd = None
        self._white_cmd = None
        self._effect_speed_cmd = None
        self._effect_cmd = None
        self._color_temp_cmd = None
        self._color_temp = None
        self._max_color_temp_kelvin = None
        self._min_color_temp_kelvin = None
        self._model = None

        try:
            self._device = async_ble_device_from_address(hass, self._address)
        except (Exception) as error:
            LOGGER.error("Error getting device: %s", error)

        for discovery_info in async_discovered_service_info(hass):
            if discovery_info.address == address:
                devicedata = DeviceData(hass, discovery_info)
                LOGGER.debug("device %s: %s %s",devicedata.name, devicedata.address, devicedata.rssi)
                if devicedata.is_supported:
                    self._device_data = devicedata
        
        if not self._device:
            raise ConfigEntryNotReady(f"You need to add bluetooth integration (https://www.home-assistant.io/integrations/bluetooth) or couldn't find a nearby device with address: {address}")
            
        # self._adv_data: AdvertisementData | None = None
        self._detect_model()
        LOGGER.debug('Model information for device %s : ModelNo %s, Turn on cmd %s, Turn off cmd %s, White cmd %s, rssi %s', self._device.name, self._model, self._turn_on_cmd, self._turn_off_cmd, self._white_cmd, self.rssi)
        
    def _detect_model(self):
        x = 0
        for name in NAME_ARRAY:
            if self._device.name.lower().startswith(name.lower()):
                self._turn_on_cmd = TURN_ON_CMD[x]
                self._turn_off_cmd = TURN_OFF_CMD[x]
                self._white_cmd = WHITE_CMD[x]
                self._effect_speed_cmd = EFFECT_SPEED_CMD[x]
                self._effect_cmd = EFFECT_CMD[x]
                self._color_temp_cmd = COLOR_TEMP_CMD[x]
                self._max_color_temp_kelvin = MAX_COLOR_TEMPS_K[x]
                self._min_color_temp_kelvin = MIN_COLOR_TEMPS_K[x]
                self._model = name
                return x
            x = x + 1
    
    def get_white_cmd(self, intensity: int):
        white_cmd = self._white_cmd.copy()
        bb_index = white_cmd.index(0xbb) if 0xbb in white_cmd else -1
        if bb_index >= 0:
            white_cmd[bb_index] = int(intensity*100/255)
        return white_cmd
    
    def get_effect_speed_cmd(self, value: int):
        effect_speed_cmd = self._effect_speed_cmd.copy()
        bb_index = effect_speed_cmd.index(0xbb) if 0xbb in effect_speed_cmd else -1
        if bb_index >= 0:
            effect_speed_cmd[bb_index] = int(value)
        return effect_speed_cmd
    
    def get_effect_cmd(self, value: int):
        effect_cmd = self._effect_cmd.copy()
        bb_index = effect_cmd.index(0xbb) if 0xbb in effect_cmd else -1
        if bb_index >= 0:
            effect_cmd[bb_index] = int(value)
        return effect_cmd

    def get_color_temp_cmd(self, warm: int, cold: int):
        color_temp_cmd = self._color_temp_cmd.copy()
        # Find all 0xbb positions
        bb_indices = [i for i, v in enumerate(color_temp_cmd) if v == 0xbb]
        if len(bb_indices) >= 2:
            color_temp_cmd[bb_indices[0]] = int(warm)
            color_temp_cmd[bb_indices[1]] = int(cold)
        return color_temp_cmd
            
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
        return self._min_color_temp_kelvin
    
    @property
    def max_color_temp_kelvin(self):
        return self._max_color_temp_kelvin
    
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
    
    @retry_bluetooth_connection_error
    async def set_color_temp(self, value: int):
        if value > 100:
            value = 100
        warm = value
        cold = 100 - value
        color_temp_cmd = self.get_color_temp_cmd(warm, cold)
        await self._write(color_temp_cmd)
        self._color_temp = warm

    @retry_bluetooth_connection_error
    async def set_color_temp_kelvin(self, value: int, brightness: int):
        # White colours are represented by colour temperature percentage from 0x0 to 0x64 from warm to cool
        # Warm (0x0) is only the warm white LED, cool (0x64) is only the white LED and then a mixture between the two
        self._color_temp_kelvin = value
        if value < self._min_color_temp_kelvin:
            value = self._min_color_temp_kelvin
        if value > self._max_color_temp_kelvin:
            value = self._max_color_temp_kelvin
        color_temp_percent = int(((value - self._min_color_temp_kelvin) * 100) / (self._max_color_temp_kelvin - self._min_color_temp_kelvin))
        # Ensure brightness is not None before using it
        if brightness is None:
            brightness = self._brightness if self._brightness is not None else 255
        brightness_percent = int(brightness * 100 / 255) 
        color_temp_cmd = self.get_color_temp_cmd(color_temp_percent, brightness_percent)
        await self._write(color_temp_cmd)

    @retry_bluetooth_connection_error
    async def set_color(self, rgb: Tuple[int, int, int]):
        r, g, b = rgb
        await self._write([0x7e, 0x00, 0x05, 0x03, int(r), int(g), int(b), 0x00, 0xef])
        self._rgb_color = rgb

    @retry_bluetooth_connection_error
    async def set_white(self, intensity: int):
        if intensity is None:
            intensity = 255  # Valor por defecto si no se especifica
        white_cmd = self.get_white_cmd(intensity)
        await self._write(white_cmd)
        self._brightness = intensity

    @retry_bluetooth_connection_error
    async def set_brightness(self, intensity: int):
        await self._write([0x7e, 0x04, 0x01, int(intensity*100/255), 0xff, 0x00, 0xff, 0x00, 0xef])
        self._brightness = intensity

    @retry_bluetooth_connection_error
    async def set_effect_speed(self, value: int):
        effect_speed = self.get_effect_speed_cmd(value)
        await self._write(effect_speed)
        self._effect_speed = value

    @retry_bluetooth_connection_error
    async def set_effect(self, value: int):
        effect = self.get_effect_cmd(value)
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
        await self._write(self._turn_on_cmd)
        self._is_on = True

    @retry_bluetooth_connection_error
    async def turn_off(self):
        await self._write(self._turn_off_cmd)
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
        date=datetime.date.today()
        year, week_num, day_of_week = date.isocalendar()
        await self._write([0x7e, 0x00, 0x83, datetime.datetime.now().strftime('%H'), datetime.datetime.now().strftime('%M'), datetime.datetime.now().strftime('%S'), day_of_week, 0x00, 0xef])

    @retry_bluetooth_connection_error
    async def custom_time(self, hour: int, minute: int, second: int, day_of_week: int):
        await self._write([0x7e, 0x00, 0x83, hour, minute, second, day_of_week, 0x00, 0xef])

    @retry_bluetooth_connection_error
    async def update(self):
        try:
            await self._ensure_connected()

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
            
            resolved = self._resolve_characteristics(client.services)
            if not resolved:
                # Try to handle services failing to load
                try:    
                    resolved = self._resolve_characteristics(await client.get_services())
                    self._cached_services = client.get_services() if resolved else None
                except (AttributeError) as error:
                    LOGGER.warning("%s: Could not resolve characteristics from services; RSSI: %s", self.name, self.rssi)
            else:
                self._cached_services = client.services if resolved else None
            
            if not resolved:
                await client.clear_cache()
                await client.disconnect()
                raise CharacteristicMissingError(
                    "Failed to find supported characteristics, device may not be supported"
                )

            LOGGER.debug("%s: Characteristics resolved: %s; RSSI: %s", self.name, resolved, self.rssi)

            self._client = client
            self._reset_disconnect_timer()

            #login commands
            await self._login_command()

            try:
                if not self._device.name.lower().startswith("melk") and not self._device.name.lower().startswith("ledble"):
                    if self._read_uuid is not None and self._read_uuid != "None":
                        LOGGER.debug("%s: Subscribe to notifications; RSSI: %s", self.name, self.rssi)
                        await client.start_notify(self._read_uuid, self._notification_handler)
                    else:
                        LOGGER.warning("%s: Read UUID not resolved (value: %s), skipping notifications", self.name, self._read_uuid)
            except Exception as e:
                LOGGER.error("Error during connection: %s", e)

    async def _login_command(self):
        try:
            if self._device.name.lower().startswith("modelx"):
                LOGGER.debug("Executing login command for: %s; RSSI: %s", self.name, self.rssi)
                await self._write([0x7e, 0x07, 0x83])
                await asyncio.sleep(1)
                await self._write([0x7e, 0x04, 0x04])
                await asyncio.sleep(1)
            else:
                LOGGER.debug("login command for: %s not needed; RSSI: %s", self.name, self.rssi)

        except (Exception) as error:
            LOGGER.error("Error login command: %s", error)
            track = traceback.format_exc()
            LOGGER.debug(track)

    async def _init_command(self):
        try:
            if self._device.name.lower().startswith("melk"):
                LOGGER.debug("Executing init command for: %s; RSSI: %s", self.name, self.rssi)
                await self._write([0x7e, 0x07, 0x83])
                await asyncio.sleep(1)
                await self._write([0x7e, 0x04, 0x04])
                await asyncio.sleep(1)
            else:
                LOGGER.debug("init command for: %s not needed; RSSI: %s", self.name, self.rssi)

        except (Exception) as error:
            LOGGER.error("Error login command: %s", error)
            track = traceback.format_exc()
            LOGGER.debug(track)

    def _notification_handler(self, _sender: int, data: bytearray) -> None:
        """Handle notification responses."""
        LOGGER.debug("%s: Notification received: %s", self.name, data.hex())
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
        for characteristic in READ_CHARACTERISTIC_UUIDS:
            if char := services.get_characteristic(characteristic):
                self._read_uuid = char.uuid
                LOGGER.debug("%s: Found read UUID: %s with handle %s", self.name, self._read_uuid, char.handle if hasattr(char, 'handle') else 'Unknown')
                break
        
        if not self._read_uuid:
            LOGGER.warning("%s: Could not find any read characteristic from: %s", self.name, READ_CHARACTERISTIC_UUIDS)
        
        # Try to find write characteristic
        for characteristic in WRITE_CHARACTERISTIC_UUIDS:
            if char := services.get_characteristic(characteristic):
                self._write_uuid = char.uuid
                LOGGER.debug("%s: Found write UUID: %s with handle %s", self.name, self._write_uuid, char.handle if hasattr(char, 'handle') else 'Unknown')
                if self.name == "ELK-BLEDOM" and char.handle if hasattr(char, 'handle') else 'Unknown' == 0x000d:
                    LOGGER.debug("%s: Adjusting model for ELK-BLEDOM specific handle issue", self.name)
                    self._turn_on_cmd = TURN_ON_CMD[0]
                    self._turn_off_cmd = TURN_OFF_CMD[0]
                    self._white_cmd = WHITE_CMD[0]
                    self._effect_speed_cmd = EFFECT_SPEED_CMD[0]
                    self._effect_cmd = EFFECT_CMD[0]
                    self._color_temp_cmd = COLOR_TEMP_CMD[0]
                    self._max_color_temp_kelvin = MAX_COLOR_TEMPS_K[0]
                    self._min_color_temp_kelvin = MIN_COLOR_TEMPS_K[0]
                break
        
        if not self._write_uuid:
            LOGGER.error("%s: Could not find any write characteristic from: %s", self.name, WRITE_CHARACTERISTIC_UUIDS)
        
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
            read_char = self._read_uuid
            client = self._client
            LOGGER.debug("Disconnecting: READ_UUID=%s, CLIENT_CONNECTED=%s", read_char, client.is_connected if client else "No Client")
            self._expected_disconnect = True
            self._client = None
            self._write_uuid = None
            self._read_uuid = None
            if client and client.is_connected:
                try:
                    if not self._device.name.lower().startswith("melk") and not self._device.name.lower().startswith("ledble"):
                        await client.stop_notify(read_char)
                    await client.disconnect()
                except Exception as e:
                    LOGGER.error("Error during disconnection: %s", e)