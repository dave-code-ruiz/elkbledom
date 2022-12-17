import asyncio
from datetime import datetime
from homeassistant.components import bluetooth
from homeassistant.exceptions import ConfigEntryNotReady

from bleak.backends.device import BLEDevice
from bleak.backends.service import BleakGATTCharacteristic, BleakGATTServiceCollection
from bleak.exc import BleakDBusError
from bleak_retry_connector import BLEAK_RETRY_EXCEPTIONS as BLEAK_EXCEPTIONS
from bleak_retry_connector import (
    BleakClientWithServiceCache,
    BleakError,
    BleakNotFoundError,
    ble_device_has_changed,
    establish_connection,
)
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

#gatttool -i hci0 -b be:59:7a:00:08:d5 --char-write-req -a 0x0009 -n 7e0004f00001ff00ef POWERON
#gatttool -i hci0 -b be:59:7a:00:08:d5 --char-write-req -a 0x0009 -n 7e00050300ff0000ef POWEROFF

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
# [be:59:7a:00:08:d5][LE]> char-read-uuid 0000fff4-0000-1000-8000-00805f9b34fb
# handle: 0x0006   value: 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00
# [be:59:7a:00:08:d5][LE]> char-read-uuid 00002a00-0000-1000-8000-00805f9b34fb
# handle: 0x0003   value: 45 4c 4b 2d 42 4c 45 44 4f 4d 20 20 20 -> NAME ELK-BLEDOM
# [be:59:7a:00:08:d5][LE]>

WRITE_CHARACTERISTIC_UUIDS = ["0000fff3-0000-1000-8000-00805f9b34fb", "0000ffe1-0000-1000-8000-00805f9b34fb"]
READ_CHARACTERISTIC_UUIDS  = ["0000fff4-0000-1000-8000-00805f9b34fb", "0000ffe2-0000-1000-8000-00805f9b34fb"]

DEFAULT_ATTEMPTS = 3
DISCONNECT_DELAY = 120
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

class BLEDOMInstance:
    def __init__(self, address, hass) -> None:
        self.loop = asyncio.get_running_loop()
        self._mac = address
        self._hass = hass
        self._device: BLEDevice | None = None
        self._device = bluetooth.async_ble_device_from_address(self._hass, address, connectable=True)
        if not self._device:
            raise ConfigEntryNotReady(f"Couldn't find a nearby device with address: {address}")
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
        self._color_temp = None
        self._write_uuid = None
        self._read_uuid = None

    async def _write(self, data: bytearray):
        """Send command to device and read response."""
        await self._ensure_connected()
        await self._write_while_connected(data)

    async def _write_while_connected(self, data: bytearray):
        LOGGER.debug(''.join(format(x, ' 03x') for x in data))
        await self._client.write_gatt_char(self._write_uuid, data, False)

    @property
    def mac(self):
        return self._device.address

    @property
    def name(self):
        return self._device.name

    @property
    def rssi(self):
        return self._device.rssi

    @property
    def is_on(self):
        return self._is_on
    
    @property
    def rgb_color(self):
        return self._rgb_color

    @property
    def white_brightness(self):
        return self._brightness
    
    @property
    def color_temp(self):
        return self._color_temp

    @property
    def effect(self):
        return self._effect

    @retry_bluetooth_connection_error
    async def set_white(self, intensity: int):
        await self._write([0x7e, 0x00, 0x01, int(intensity*100/255), 0x00, 0x00, 0x00, 0x00, 0xef])
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
        await self._ensure_connected()
        if self._write_uuid.uuid == WRITE_CHARACTERISTIC_UUIDS[1]:
            await self._write([0x7e, 0x00, 0x04, 0x01, 0x00, 0x00, 0x00, 0x00, 0xef])
        else:
            await self._write([0x7e, 0x00, 0x04, 0xf0, 0x00, 0x01, 0xff, 0x00, 0xef])
        self._is_on = True
                
    @retry_bluetooth_connection_error
    async def turn_off(self):
        await self._write([0x7e, 0x00, 0x04, 0x00, 0x00, 0x00, 0xff, 0x00, 0xef])
        self._is_on = False
    
    @retry_bluetooth_connection_error
    async def set_color(self, rgb: Tuple[int, int, int]):
        r, g, b = rgb
        await self._write([0x7e, 0x00, 0x05, 0x03, r, g, b, 0x00, 0xef])
        self._rgb_color = rgb
    
    @retry_bluetooth_connection_error
    async def set_color_temp(self, value: int):
        if value > 100:
            value = 100
        warm = value
        cold = 100 - value
        await self._write([0x7e, 0x00, 0x05, 0x02, warm, cold, 0x00, 0x00, 0xef])
        self._color_temp = warm

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

            #future = asyncio.get_event_loop().create_future()
            #await self._device.start_notify(self._read_uuid, create_status_callback(future))
            # PROBLEMS WITH STATUS VALUE, I HAVE NOT VALUE TO WRITE AND GET STATUS
            if(self._is_on is None):
                self._is_on = False
                self._rgb_color = (0, 0, 0)
                self._brightness = 240

            #await self._write([0x7e, 0x00, 0x01, 0xfa, 0x00, 0x00, 0x00, 0x00, 0xef])
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

            LOGGER.debug("%s: Subscribe to notifications; RSSI: %s", self.name, self.rssi)
            await client.start_notify(self._read_uuid, self._notification_handler)
    
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
        self._disconnect_timer = self.loop.call_later(
            DISCONNECT_DELAY, self._disconnect
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
            DISCONNECT_DELAY,
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
                await client.stop_notify(read_char)
                await client.disconnect()