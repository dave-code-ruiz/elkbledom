import asyncio
from datetime import datetime
from homeassistant.components import bluetooth
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
#throw error, see issue #43
#from bluetooth_sensor_state_data import BluetoothData
from typing import Any, TypeVar, cast, Tuple
from collections.abc import Callable
import traceback
import asyncio
import logging

LOGGER = logging.getLogger(__name__)

#handle: 0x0002, char properties: 0x12, char value handle: 0x0003, uuid: 00002a00-0000-1000-8000-00805f9b34fb
#handle: 0x0005, char properties: 0x10, char value handle: 0x0006, uuid: 0000fff4-0000-1000-8000-00805f9b34fb
#handle: 0x0008, char properties: 0x06, char value handle: 0x0009, uuid: 0000fff3-0000-1000-8000-00805f9b34fb
#OTHER LED STRIP ??
#handle: 0x0008, char properties: 0x06, char value handle: 0x0009, uuid: 0000fff0-0000-1000-8000-00805f9b34fb

#gatttool -i hci0 -b be:59:7a:00:08:d5 --char-write-req -a 0x0009 -n 7e00040100000000ef POWERON
#gatttool -i hci0 -b be:59:7a:00:08:d5 --char-write-req -a 0x0009 -n 7e0004000000ff00ef POWEROFF

# sudo gatttool -b be:59:7a:00:08:d5 --char-write-req -a 0x0009 -n 7e0004f00001ff00ef # POWER ON
# sudo gatttool -b be:59:7a:00:08:d5 --char-write-req -a 0x0009 -n 7e000503ff000000ef # RED
# sudo gatttool -b be:59:7a:00:08:d5 --char-write-req -a 0x0009 -n 7e0005030000ff00ef # BLUE
# sudo gatttool -b be:59:7a:00:08:d5 --char-write-req -a 0x0009 -n 7e00050300ff0000ef # GREEN
# sudo gatttool -b be:59:7a:00:08:d5 --char-write-req -a 0x0009 -n 7e0004000000ff00ef # POWER OFF

#https://github.com/TheSylex/ELK-BLEDOM-bluetooth-led-strip-controller/
#https://github.com/FreekBes/bledom_controller/
#https://github.com/sysofwan/ha-triones
#https://github.com/FergusInLondon/ELK-BLEDOM/
#https://linuxthings.co.uk/blog/control-an-elk-bledom-bluetooth-led-strip
#https://github.com/arduino12/ble_rgb_led_strip_controller
#https://github.com/lilgallon/DynamicLedStrips
#https://github.com/kquinsland/JACKYLED-BLE-RGB-LED-Strip-controller


# pi@homeassistant:~/magic $ gatttool -I
# Attempting to connect to be:59:7a:00:08:d5
# Connection successful
# [be:59:7a:00:08:d5][LE]> char-read-uuid 0000fff3-0000-1000-8000-00805f9b34fb
# handle: 0x0009   value: 7e 08 82 00 00 00 01 00 ef 2e 39 52 33 36 30 32
# handle: 0x0009   value: 20 53 48 59 2d 56 38 2e 37 2e 39 52 33 36 30 32
# handle: 0x0009   value: 50 33 30 56 33 32 5f 53 48 59 5f 52 31 34 35 33 - MELK

# [be:59:7a:00:08:d5][LE]> char-read-uuid 0000fff4-0000-1000-8000-00805f9b34fb
# handle: 0x0006   value: 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00
# [be:59:7a:00:08:d5][LE]> char-read-uuid 00002a00-0000-1000-8000-00805f9b34fb
# handle: 0x0003   value: 45 4c 4b 2d 42 4c 45 44 4f 4d 20 20 20 -> NAME ELK-BLEDOM
# [be:59:7a:00:08:d5][LE]>

# CHANGES ARRAYS TO DICT OR MODELDB OBJECT WITH ALL MODEL INFORMATION
NAME_ARRAY = ["ELK-BLE",
              "LEDBLE",
              "MELK",
              "ELK-BULB"]
WRITE_CHARACTERISTIC_UUIDS = ["0000fff3-0000-1000-8000-00805f9b34fb",
                              "0000ffe1-0000-1000-8000-00805f9b34fb",
                              "0000fff3-0000-1000-8000-00805f9b34fb",
                              "0000fff3-0000-1000-8000-00805f9b34fb"]
READ_CHARACTERISTIC_UUIDS  = ["0000fff4-0000-1000-8000-00805f9b34fb",
                              "0000ffe2-0000-1000-8000-00805f9b34fb",
                              "0000fff4-0000-1000-8000-00805f9b34fb",
                              "0000fff4-0000-1000-8000-00805f9b34fb"]
TURN_ON_CMD = [[0x7e, 0x00, 0x04, 0xf0, 0x00, 0x01, 0xff, 0x00, 0xef],
               [0x7e, 0x00, 0x04, 0x01, 0x00, 0x00, 0x00, 0x00, 0xef],
               [0x7e, 0x00, 0x04, 0x01, 0x00, 0x00, 0x00, 0x00, 0xef],
               [0x7e, 0x00, 0x04, 0x01, 0x00, 0x00, 0x00, 0x00, 0xef]]
TURN_OFF_CMD = [[0x7e, 0x00, 0x04, 0x00, 0x00, 0x00, 0xff, 0x00, 0xef],
                [0x7e, 0x00, 0x04, 0x00, 0x00, 0x00, 0xff, 0x00, 0xef],
                [0x7e, 0x00, 0x04, 0x00, 0x00, 0x00, 0xff, 0x00, 0xef],
                [0x7e, 0x00, 0x04, 0x00, 0x00, 0x00, 0xff, 0x00, 0xef]]
MIN_COLOR_TEMPS_K = [2700,2700,2700,2700]
MAX_COLOR_TEMPS_K = [6500,6500,6500,6500]

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

#class DeviceData(BluetoothData):
class DeviceData():
    def __init__(self, hass, discovery_info):
        self._discovery = discovery_info
        self._supported = self._discovery.name.lower().startswith("elk-ble") or self._discovery.name.lower().startswith("elk-bulb") or self._discovery.name.lower().startswith("ledble") or self._discovery.name.lower().startswith("melk")
        self._address = self._discovery.address
        self._name = self._discovery.name
        self._rssi = self._discovery.rssi
        self._hass = hass
        self._bledevice = async_ble_device_from_address(hass, self._address)
        # try:
        #     discovered_devices_and_advertisement_data = await BleakScanner.discover(return_adv=True)
        #     for device, adv_data in discovered_devices_and_advertisement_data.values():
        #         if device.address == address:
        #             self._bledevice = device
        #             self._adv_data = adv_data
        # except (Exception) as error:
        #     LOGGER.warning("Warning getting device: %s", error)
        #     self._bledevice = bluetooth.async_ble_device_from_address(self._hass, address)
        # if not self._bledevice:
        #     raise ConfigEntryNotReady(f"You need to add bluetooth integration (https://www.home-assistant.io/integrations/bluetooth) or couldn't find a nearby device with address: {address}")
        

    # def __init__(self, *args):
    #     if isinstance(args[0], BluetoothServiceInfoBleak):
    #         self._discovery = args[0]
    #         self._supported = self._discovery.name.lower().startswith("elk-ble") or self._discovery.name.lower().startswith("elk-bulb") or self._discovery.name.lower().startswith("ledble") or self._discovery.name.lower().startswith("melk")
    #         self.address = self._discovery.address
    #         self.name = self._discovery.name
    #         self.rssi = self._discovery.rssi
    #     else:
    #         self._supported = args[0]
    #         self.address = args[1]
    #         self.name = args[2]
    #         self.rssi = args[3]

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
                #devicedata = DeviceData(self._hass, discovery_info)
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
        self._brightness = None
        self._effect = None
        self._effect_speed = None
        self._color_temp_kelvin = None
        self._write_uuid = None
        self._read_uuid = None
        self._turn_on_cmd = None
        self._turn_off_cmd = None
        self._max_color_temp_kelvin = None
        self._min_color_temp_kelvin = None
        self._model = None

        try:
            #self._device = self._device_data.bledevice()
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
        LOGGER.debug('Model information for device %s : ModelNo %s, Turn on cmd %s, Turn off cmd %s, rssi %s', self._device.name, self._model, self._turn_on_cmd, self._turn_off_cmd, self.rssi)
        
    def _detect_model(self):
        x = 0
        for name in NAME_ARRAY:
            if self._device.name.lower().startswith(name.lower()):
                self._turn_on_cmd = TURN_ON_CMD[x]
                self._turn_off_cmd = TURN_OFF_CMD[x]
                self._max_color_temp_kelvin = MAX_COLOR_TEMPS_K[x]
                self._min_color_temp_kelvin = MIN_COLOR_TEMPS_K[x]
                self._model = name
                return x
            x = x + 1

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
    
    @retry_bluetooth_connection_error
    async def set_color_temp(self, value: int):
        if value > 100:
            value = 100
        warm = value
        cold = 100 - value
        await self._write([0x7e, 0x00, 0x05, 0x02, warm, cold, 0x00, 0x00, 0xef])
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
        if brightness is None:
            brightness = self._brightness
        brightness_percent = int(brightness * 100 / 255) 
        await self._write([0x7e, 0x00, 0x05, 0x02, color_temp_percent, brightness_percent, 0x00, 0x00, 0xef])

    @retry_bluetooth_connection_error
    async def set_color(self, rgb: Tuple[int, int, int]):
        r, g, b = rgb
        await self._write([0x7e, 0x00, 0x05, 0x03, r, g, b, 0x00, 0xef])
        self._rgb_color = rgb

    @DeprecationWarning
    @retry_bluetooth_connection_error
    async def set_white(self, intensity: int):
        await self._write([0x7e, 0x00, 0x01, int(intensity*100/255), 0x00, 0x00, 0x00, 0x00, 0xef])
        self._brightness = intensity

    @retry_bluetooth_connection_error
    async def set_brightness(self, intensity: int):
        await self._write([0x7e, 0x04, 0x01, int(intensity*100/255), 0xff, 0x00, 0xff, 0x00, 0xef])
        self._brightness = intensity

    @retry_bluetooth_connection_error
    async def set_effect_speed(self, value: int):
        await self._write([0x7e, 0x00, 0x02, value, 0x00, 0x00, 0x00, 0x00, 0xef])
        self._effect_speed = value

    @retry_bluetooth_connection_error
    async def set_effect(self, value: int):
        await self._write([0x7e, 0x00, 0x03, value, 0x03, 0x00, 0x00, 0x00, 0xef])
        self._effect = value

    @retry_bluetooth_connection_error
    async def turn_on(self):
        #NOT NEEDED, self._write() call to self._ensure_connected()
        #await self._ensure_connected()
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
            client = await establish_connection(
                BleakClientWithServiceCache,
                self._device,
                self.name,
                self._disconnected,
                cached_services=self._cached_services,
                ble_device_callback=lambda: self._device,
            )
            LOGGER.debug("%s: Connected; RSSI: %s", self.name, self.rssi)
            resolved = self._resolve_characteristics(client.services)
            if not resolved:
                # Try to handle services failing to load
                resolved = self._resolve_characteristics(await client.get_services())
            self._cached_services = client.services if resolved else None

            self._client = client
            self._reset_disconnect_timer()

            #login commands
            await self._login_command()

            if not self._device.name.lower().startswith("melk"):
                LOGGER.debug("%s: Subscribe to notifications; RSSI: %s", self.name, self.rssi)
                await client.start_notify(self._read_uuid, self._notification_handler)

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
        for characteristic in READ_CHARACTERISTIC_UUIDS:
            if char := services.get_characteristic(characteristic):
                self._read_uuid = char
                break
        for characteristic in WRITE_CHARACTERISTIC_UUIDS:
            if char := services.get_characteristic(characteristic):
                self._write_uuid = char
                break
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
            self._expected_disconnect = True
            self._client = None
            self._write_uuid = None
            self._read_uuid = None
            if client and client.is_connected:
                if not self._device.name.lower().startswith("melk"):
                    await client.stop_notify(read_char)
                await client.disconnect()
