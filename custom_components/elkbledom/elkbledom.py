from typing import Tuple
from bleak import BleakClient, BleakScanner
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

WRITE_CHARACTERISTIC_UUIDS = ["0000fff3-0000-1000-8000-00805f9b34fb"]
READ_CHARACTERISTIC_UUIDS  = ["0000fff4-0000-1000-8000-00805f9b34fb"]

async def discover():
    """Discover Bluetooth LE devices."""
    devices = await BleakScanner.discover()
    LOGGER.debug("Discovered devices: %s", [{"address": device.address, "name": device.name} for device in devices])
    return [device for device in devices if device.name.lower().startswith("elk-bledom") or device.name.lower().startswith("othername")]

def create_status_callback(future: asyncio.Future):
    def callback(sender: int, data: bytearray):
        if not future.done():
            future.set_result(data)
    return callback

class BLEDOMInstance:
    def __init__(self, mac: str) -> None:
        self._mac = mac
        self._device = BleakClient(self._mac)
        self._is_on = None
        self._rgb_color = None
        self._brightness = None
        self._write_uuid = None
        self._read_uuid = None

    async def _write(self, data: bytearray):
        LOGGER.debug(''.join(format(x, ' 03x') for x in data))
        await self._device.write_gatt_char(self._write_uuid, data)

    @property
    def mac(self):
        return self._mac

    @property
    def is_on(self):
        return self._is_on
    
    @property
    def rgb_color(self):
        return self._rgb_color

    @property
    def white_brightness(self):
        return self._brightness

    async def set_color(self, rgb: Tuple[int, int, int]):
        self._rgb_color = rgb
        r, g, b = rgb
        await self._write([0x7e, 0x00, 0x05, 0x03, r, g, b, 0x00, 0xef])
    
    async def set_white(self, intensity: int):
        self._brightness = intensity
        await self._write([0x7e, 0x00, 0x01, intensity, 0x00, 0x00, 0x00, 0x00, 0xef])

    async def turn_on(self):
        await self._write([0x7e, 0x00, 0x04, 0xf0, 0x00, 0x01, 0xff, 0x00, 0xef])
        self._is_on = True
        
    async def turn_off(self):
        await self._write([0x7e, 0x00, 0x04, 0x00, 0x00, 0x00, 0xff, 0x00, 0xef])
        self._is_on = False
    
    async def update(self):
        try:
            if not self._device.is_connected:
                await self._device.connect(timeout=20)
                await asyncio.sleep(1)

                for char in self._device.services.characteristics.values():
                    if char.uuid in WRITE_CHARACTERISTIC_UUIDS:
                        self._write_uuid = char.uuid
                    if char.uuid in READ_CHARACTERISTIC_UUIDS:
                        self._read_uuid = char.uuid

                if not self._read_uuid or not self._write_uuid:
                    LOGGER.error("No supported read/write UUIDs found")
                    return

                LOGGER.info(f"Read UUID: {self._read_uuid}, Write UUID: {self._write_uuid}")

            #await asyncio.sleep(2)

            #future = asyncio.get_event_loop().create_future()
            #await self._device.start_notify(self._read_uuid, create_status_callback(future))
            # PROBLEMS WITH STATUS VALUE, I HAVE NOT VALUE TO WRITE AND GET STATUS
            if(self._is_on is None):
                self._is_on = True
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

    async def disconnect(self):
        if self._device.is_connected:
            await self._device.disconnect()
