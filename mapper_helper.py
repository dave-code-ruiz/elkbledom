import csv
import asyncio
from bleak import BleakClient

import asyncio
from datetime import datetime

from bleak.backends.device import BLEDevice
from bleak.backends.service import BleakGATTServiceCollection
from bleak.exc import BleakDBusError
from bleak_retry_connector import BLEAK_RETRY_EXCEPTIONS as BLEAK_EXCEPTIONS
from bleak_retry_connector import (
    BleakNotFoundError,
)
from typing import Any, TypeVar, cast
from collections.abc import Callable
import asyncio
import logging

address = "BE:16:83:00:16:21"

LOGGER = logging.getLogger(__name__)

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

async def send_packet(packet, client):
    print("Sending packet " + packet)
    try:
        data = bytes.fromhex(packet)
    except Exception as e:
        print(e)
        return
    await client.write_gatt_char("0000fff3-0000-1000-8000-00805f9b34fb", data, False)


async def main():
    notes = []
    prev_note = ""
    note_index = 0
    packet_vals = []
    async with BleakClient(address) as client:
        for i in range(0x00,0x10):
            hex_val = f"{i:#0{4}x}"
            val = "7e07038"+hex_val[3:]+"04ffff00ef"
            await send_packet(val, client)    
            note = input("Note:")
            if note == "":
                note = f"{prev_note}_{note_index}"
                note_index += 1
            else:
                prev_note = note
                note_index = 0
            notes.append(note)
            packet_vals.append(hex_val)
            

        '''
        # extract packets.csv with only the packets from BLE Logs via Vireshark
        with open('packets.csv', newline='') as csvfile:
            packets = csv.reader(csvfile, delimiter=' ', quotechar='|')
            for packet in packets:
                val = packet[0].replace('"', '')
                if val.find("Data") != -1:
                    continue
                await send_packet(val, client)       
                notes.append(input("Note:"))
                packet_vals.append(val)
        '''
    with open('packet_notes.txt', 'w') as outfile:
        for i in range(0,len(notes)):
            outfile.write(f"{notes[i]} = {packet_vals[i]}\n")
    
    '''
    with open('packet_notes.csv', 'w', newline='') as csvfile:
        writer = csv.writer(csvfile, delimiter=' ',quoting=csv.QUOTE_NONE)
        writer.writerow(['Packet', 'Note'])
    '''

asyncio.run(main())
