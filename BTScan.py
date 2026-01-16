#!/usr/bin/env python3
"""
BLE LED Strip Discovery and Testing Tool
Helps find commands for new LED strips to add to elkbledom.py
"""

import asyncio
import logging
from bleak import BleakScanner, BleakClient
from bleak.backends.device import BLEDevice
from bleak.exc import BleakError
import sys
from typing import List, Dict, Optional, Tuple
import json
from datetime import datetime

logging.basicConfig(level=logging.INFO)
_LOGGER = logging.getLogger(__name__)

# Características conocidas de elkbledom.py
KNOWN_WRITE_UUIDS = [
    "0000fff3-0000-1000-8000-00805f9b34fb",
    "0000ffe1-0000-1000-8000-00805f9b34fb",
]

KNOWN_READ_UUIDS = [
    "0000fff4-0000-1000-8000-00805f9b34fb",
    "0000ffe2-0000-1000-8000-00805f9b34fb",
]

# Comandos conocidos de elkbledom.py
KNOWN_TURN_ON = [
    [0x7e, 0x04, 0x04, 0xf0, 0x00, 0x01, 0xff, 0x00, 0xef],
    [0x7e, 0x00, 0x04, 0xf0, 0x00, 0x01, 0xff, 0x00, 0xef],
    [0x7e, 0x00, 0x04, 0x01, 0x00, 0x00, 0x00, 0x00, 0xef],
    [0x7e, 0x07, 0x04, 0xff, 0x00, 0x01, 0x02, 0x01, 0xef],
]

KNOWN_TURN_OFF = [
    [0x7e, 0x04, 0x04, 0x00, 0x00, 0x00, 0xff, 0x00, 0xef],
    [0x7e, 0x00, 0x04, 0x00, 0x00, 0x00, 0xff, 0x00, 0xef],
    [0x7e, 0x07, 0x04, 0x00, 0x00, 0x00, 0x02, 0x00, 0xef],
]

KNOWN_WHITE = [
    [0x7e, 0x00, 0x01, 0xbb, 0x00, 0x00, 0x00, 0x00, 0xef],
    [0x7e, 0x07, 0x05, 0x01, 0xbb, 0xff, 0x02, 0x01],
]

KNOWN_COLOR_TEMP = [
    [0x7e, 0x00, 0x05, 0x02, 0xbb, 0xbb, 0x00, 0x00, 0xef],
    [0x7e, 0x06, 0x05, 0x02, 0xbb, 0xbb, 0xff, 0x08, 0xef],
]

# 30+ NEW COMMANDS based on common BLE LED protocols found in forums and documentation
NEW_TURN_ON_COMMANDS = [
    # Variants of 0x7e protocol with different prefixes
    [0x7e, 0x01, 0x04, 0xf0, 0x00, 0x01, 0xff, 0x00, 0xef],
    [0x7e, 0x02, 0x04, 0xf0, 0x00, 0x01, 0xff, 0x00, 0xef],
    [0x7e, 0x03, 0x04, 0xf0, 0x00, 0x01, 0xff, 0x00, 0xef],
    [0x7e, 0x05, 0x04, 0xf0, 0x00, 0x01, 0xff, 0x00, 0xef],
    [0x7e, 0x06, 0x04, 0xf0, 0x00, 0x01, 0xff, 0x00, 0xef],
    [0x7e, 0x08, 0x04, 0xf0, 0x00, 0x01, 0xff, 0x00, 0xef],
    
    # Short protocol (some strips use shorter commands)
    [0xcc, 0x23, 0x33],
    [0xcc, 0x24, 0x33],
    [0x7e, 0x04, 0x01, 0xef],
    [0x7e, 0x00, 0x01, 0xef],
    
    # Alternative 0xaa protocol (used in some Magic Home controllers)
    [0xaa, 0x01, 0x01, 0x00, 0x00, 0x00, 0x00, 0x00, 0x55],
    [0xaa, 0x01, 0xff, 0x00, 0x00, 0x00, 0x00, 0x00, 0x55],
    
    # Variants with different control byte
    [0x7e, 0x00, 0x04, 0xff, 0x01, 0x01, 0xff, 0x00, 0xef],
    [0x7e, 0x00, 0x04, 0x01, 0x01, 0x01, 0x01, 0x00, 0xef],
    [0x7e, 0x00, 0x04, 0xaa, 0x00, 0x01, 0xff, 0x00, 0xef],
    
    # Commands found in Triones/Happy Lighting controllers
    [0x7e, 0x07, 0x04, 0x01, 0xff, 0x01, 0x02, 0x01, 0xef],
    [0x7e, 0x00, 0x04, 0xf1, 0x00, 0x01, 0xff, 0x00, 0xef],
    
    # Simple binary protocol
    [0x01, 0xff, 0x00],
    [0xff, 0x01],
    [0x01],
    
    # Zengge/Magic Light type commands
    [0x71, 0x23, 0x0f],
    [0x71, 0x24, 0x0f],
    
    # Variants with different checksum
    [0x7e, 0x00, 0x04, 0xf0, 0x00, 0x01, 0xff, 0x00, 0xff],
    [0x7e, 0x00, 0x04, 0xf0, 0x00, 0x01, 0xff, 0x00, 0xfe],
    [0x7e, 0x00, 0x04, 0xf0, 0x00, 0x01, 0xff, 0x00, 0xee],
    
    # Commands found in Banggood LED strips
    [0x7e, 0x00, 0x03, 0xff, 0x00, 0x00, 0x00, 0x00, 0xef],
    [0x7e, 0x04, 0x03, 0xff, 0x00, 0x01, 0xff, 0x00, 0xef],

    # Other alternative protocols
    [0xef, 0x01, 0x77],
    [0xbb, 0x00, 0x00, 0x01],
    [0x55, 0xaa, 0x01],       
]

# Query/Status commands to try for different LED strip models
# Format: [command_bytes, description]
QUERY_COMMANDS = [
    # Standard ELK-BLEDOM commands
    ([0x7e, 0x00, 0x01, 0xfa, 0x00, 0x00, 0x00, 0x00, 0xef], "Standard status query"),
    ([0x7e, 0x00, 0x10, 0x00, 0x00, 0x00, 0x00, 0x00, 0xef], "Alternative query v1"),
    ([0x7e, 0x00, 0x81, 0x00, 0x00, 0x00, 0x00, 0x00, 0xef], "Status query 0x81"),
    ([0x7e, 0x00, 0x82, 0x00, 0x00, 0x00, 0x00, 0x00, 0xef], "Status query 0x82"),
    ([0x7e, 0x00, 0x83, 0x00, 0x00, 0x00, 0x00, 0x00, 0xef], "Status query 0x83"),
    
    # Short format commands
    ([0xef, 0x01, 0x77], "Short query v1"),
    ([0x7e, 0x00, 0x10], "Short query v2"),
    ([0x7e, 0x10], "Minimal query"),
    ([0x25, 0x00], "Minimal query 2"),
    ([0x25, 0x02], "Minimal query 3"),
    
    # MELK specific commands
    ([0x7e, 0x04, 0x01, 0x00, 0xff, 0x00, 0xff, 0x00, 0xef], "MELK status query"),
    ([0x7e, 0x07, 0x01, 0x00, 0x00, 0x00, 0x02, 0x00, 0xef], "MELK query v2"),
    
    # Alternative long format
    ([0x7e, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0xef], "Get all status"),
    ([0x7e, 0x01, 0x01, 0x00, 0x00, 0x00, 0x00, 0x00, 0xef], "Status cmd 0x01"),
    ([0x7e, 0x04, 0x00, 0x00, 0x00, 0x00, 0xff, 0x00, 0xef], "Power status query"),
    
    # LEDBLE specific
    ([0x7e, 0x00, 0x04, 0xfa, 0x00, 0x00, 0x00, 0x00, 0xef], "LEDBLE status"),
    ([0xcc, 0x23, 0x33], "LEDBLE short status"),
    
    # Other variants found in wild
    ([0xaa, 0x01, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x55], "Variant header 0xaa"),
    ([0x7e, 0x00, 0x05, 0x00, 0x00, 0x00, 0x00, 0x00, 0xef], "Query cmd 0x05"),
   
    # Variantes 0x7e con diferentes bytes de comando (0x02-0x0f)
    ([0x7e, 0x00, 0x02, 0x00, 0x00, 0x00, 0x00, 0x00, 0xef], "Query cmd 0x02"),
    ([0x7e, 0x00, 0x03, 0x00, 0x00, 0x00, 0x00, 0x00, 0xef], "Query cmd 0x03"),
    ([0x7e, 0x00, 0x06, 0x00, 0x00, 0x00, 0x00, 0x00, 0xef], "Query cmd 0x06"),
    ([0x7e, 0x00, 0x07, 0x00, 0x00, 0x00, 0x00, 0x00, 0xef], "Query cmd 0x07"),
    ([0x7e, 0x00, 0x08, 0x00, 0x00, 0x00, 0x00, 0x00, 0xef], "Query cmd 0x08"),
    ([0x7e, 0x00, 0x09, 0x00, 0x00, 0x00, 0x00, 0x00, 0xef], "Query cmd 0x09"),
    ([0x7e, 0x00, 0x0a, 0x00, 0x00, 0x00, 0x00, 0x00, 0xef], "Query cmd 0x0a"),
    ([0x7e, 0x00, 0x0b, 0x00, 0x00, 0x00, 0x00, 0x00, 0xef], "Query cmd 0x0b"),
    ([0x7e, 0x00, 0x0c, 0x00, 0x00, 0x00, 0x00, 0x00, 0xef], "Query cmd 0x0c"),
    ([0x7e, 0x00, 0x0d, 0x00, 0x00, 0x00, 0x00, 0x00, 0xef], "Query cmd 0x0d"),
    
    # Comandos con segundo byte variable (prefijo alternativo)
    ([0x7e, 0x01, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0xef], "Query prefix 0x01"),
    ([0x7e, 0x02, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0xef], "Query prefix 0x02"),
    ([0x7e, 0x03, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0xef], "Query prefix 0x03"),
    ([0x7e, 0x05, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0xef], "Query prefix 0x05"),
    ([0x7e, 0x06, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0xef], "Query prefix 0x06"),
    ([0x7e, 0x08, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0xef], "Query prefix 0x08"),
    ([0x7e, 0x09, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0xef], "Query prefix 0x09"),
    
    # Comandos cortos con diferentes protocolos
    ([0xef, 0x01], "Minimal EF query"),
    ([0xef, 0x77], "EF query 0x77"),
    ([0xef, 0x00], "EF query 0x00"),
    ([0x10, 0x00], "Query 0x10 0x00"),
    ([0x10, 0x01], "Query 0x10 0x01"),
    ([0xaa, 0x00], "AA protocol query"),
    ([0xbb, 0x00, 0x00], "BB protocol query"),
    
    # Comandos tipo checksum/CRC diferentes
    ([0x7e, 0x00, 0x01, 0x00, 0x00, 0x00, 0x00, 0x00, 0xff], "Query end 0xff"),
    ([0x7e, 0x00, 0x01, 0x00, 0x00, 0x00, 0x00, 0x00, 0xfe], "Query end 0xfe"),
    ([0x7e, 0x00, 0x01, 0x00, 0x00, 0x00, 0x00, 0x00, 0xee], "Query end 0xee"),
    
    # Comandos tipo "ping" o "hello"
    ([0xff, 0x00, 0x00], "Ping command"),
    ([0x00, 0x00, 0x00], "Null query"),
    ([0x01], "Single byte query"),
    ([0xff], "Single 0xFF query"),
]

NEW_TURN_OFF_COMMANDS = [
    # Variants of 0x7e protocol with different prefixes
    [0x7e, 0x01, 0x04, 0x00, 0x00, 0x00, 0xff, 0x00, 0xef],
    [0x7e, 0x02, 0x04, 0x00, 0x00, 0x00, 0xff, 0x00, 0xef],
    [0x7e, 0x03, 0x04, 0x00, 0x00, 0x00, 0xff, 0x00, 0xef],
    [0x7e, 0x05, 0x04, 0x00, 0x00, 0x00, 0xff, 0x00, 0xef],
    [0x7e, 0x06, 0x04, 0x00, 0x00, 0x00, 0xff, 0x00, 0xef],
    [0x7e, 0x08, 0x04, 0x00, 0x00, 0x00, 0xff, 0x00, 0xef],
    
    # Short protocol
    [0xcc, 0x24, 0x33],
    [0xcc, 0x23, 0x34],
    [0x7e, 0x04, 0x00, 0xef],
    [0x7e, 0x00, 0x00, 0xef],
    
    # Alternative 0xaa protocol
    [0xaa, 0x01, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x55],
    [0xaa, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x55],
    
    # Variants with different control byte
    [0x7e, 0x00, 0x04, 0x00, 0x01, 0x00, 0xff, 0x00, 0xef],
    [0x7e, 0x00, 0x04, 0x00, 0x00, 0x00, 0x00, 0x00, 0xef],
    [0x7e, 0x00, 0x04, 0xaa, 0x00, 0x00, 0xff, 0x00, 0xef],
    
    # Triones/Happy Lighting commands
    [0x7e, 0x07, 0x04, 0x00, 0x00, 0x00, 0x02, 0x00, 0xef],
    [0x7e, 0x00, 0x04, 0xf1, 0x00, 0x00, 0xff, 0x00, 0xef],
    
    # Simple binary protocol
    [0x00, 0x00, 0x00],
    [0xff, 0x00],
    [0x00],
    
    # Zengge/Magic Light type commands
    [0x71, 0x24, 0x0f],
    [0x71, 0x23, 0x0e],
    
    # Variants with different checksum
    [0x7e, 0x00, 0x04, 0x00, 0x00, 0x00, 0xff, 0x00, 0xff],
    [0x7e, 0x00, 0x04, 0x00, 0x00, 0x00, 0xff, 0x00, 0xfe],
    [0x7e, 0x00, 0x04, 0x00, 0x00, 0x00, 0xff, 0x00, 0xee],
    
    # Banggood commands
    [0x7e, 0x00, 0x03, 0x00, 0x00, 0x00, 0x00, 0x00, 0xef],
    [0x7e, 0x04, 0x03, 0x00, 0x00, 0x00, 0xff, 0x00, 0xef],
    
    # Other alternative protocols
    [0xef, 0x00, 0x77],
    [0xbb, 0x00, 0x00, 0x00],
    [0x55, 0xaa, 0x00],
]

# Commands to set RGB color
NEW_COLOR_COMMANDS = [
    # Format: function that takes (r, g, b) and returns command
    lambda r, g, b: [0x7e, 0x00, 0x05, 0x03, r, g, b, 0x00, 0xef],  # Standard
    lambda r, g, b: [0x7e, 0x04, 0x05, 0x03, r, g, b, 0x00, 0xef],
    lambda r, g, b: [0x7e, 0x07, 0x05, 0x03, r, g, b, 0x02, 0xef],
    lambda r, g, b: [0xaa, 0x01, 0x03, r, g, b, 0x00, 0x00, 0x55],  # Magic Home
    lambda r, g, b: [0x56, r, g, b, 0x00, 0xf0, 0xaa],  # Zengge
    lambda r, g, b: [0x7e, 0x00, 0x03, r, g, b, 0x00, 0x00, 0xef],
    lambda r, g, b: [0x31, r, g, b, 0x00, 0x00, 0x0f],  # Triones
    lambda r, g, b: [0x7e, 0x01, 0x05, 0x03, r, g, b, 0x00, 0xef],
    lambda r, g, b: [0x7e, 0x02, 0x05, 0x03, r, g, b, 0x00, 0xef],
    lambda r, g, b: [0x7e, 0x05, 0x05, 0x03, r, g, b, 0x00, 0xef],
]

# Commands for white
NEW_WHITE_COMMANDS = [
    lambda brightness: [0x7e, 0x00, 0x01, brightness, 0x00, 0x00, 0x00, 0x00, 0xef],
    lambda brightness: [0x7e, 0x04, 0x01, brightness, 0x00, 0x00, 0x00, 0x00, 0xef],
    lambda brightness: [0x7e, 0x07, 0x05, 0x01, brightness, 0xff, 0x02, 0x01],
    lambda brightness: [0xaa, 0x01, 0x01, 0x00, 0x00, 0x00, brightness, 0x00, 0x55],
    lambda brightness: [0x56, 0x00, 0x00, 0x00, brightness, 0xf0, 0xaa],
    lambda brightness: [0x7e, 0x00, 0x06, brightness, 0x00, 0x00, 0x00, 0x00, 0xef],
    lambda brightness: [0x31, 0x00, 0x00, 0x00, brightness, 0x00, 0x0f],
    lambda brightness: [0x7e, 0x01, 0x01, brightness, 0x00, 0x00, 0x00, 0x00, 0xef],
]

# Commands for color temperature
NEW_COLOR_TEMP_COMMANDS = [
    lambda warm, cold: [0x7e, 0x00, 0x05, 0x02, warm, cold, 0x00, 0x00, 0xef],
    lambda warm, cold: [0x7e, 0x06, 0x05, 0x02, warm, cold, 0xff, 0x08, 0xef],
    lambda warm, cold: [0x7e, 0x04, 0x05, 0x02, warm, cold, 0x00, 0x00, 0xef],
    lambda warm, cold: [0xaa, 0x01, 0x02, warm, cold, 0x00, 0x00, 0x00, 0x55],
    lambda warm, cold: [0x7e, 0x07, 0x05, 0x02, warm, cold, 0x02, 0x00, 0xef],
    lambda warm, cold: [0x56, 0x00, 0x00, 0x00, warm, cold, 0xaa],
    lambda warm, cold: [0x7e, 0x01, 0x05, 0x02, warm, cold, 0x00, 0x00, 0xef],
]


class LEDStripDiscovery:
    def __init__(self):
        self.read_uuid: Optional[str] = None
        self.write_uuid: Optional[str] = None
        self.discovered_devices: List[BLEDevice] = []
        self.test_results = {
            'device_info': {},
            'characteristics': {},
            'working_commands': {
                'turn_on': [],
                'turn_off': [],
                'color': [],
                'white': [],
                'color_temp': [],
                'query': []
            },
            'custom_commands': []
        }
        
    async def scan_devices(self, duration: int = 30) -> List[BLEDevice]:
        """Scans nearby BLE devices"""
        print(f"\n{'='*60}")
        print(f"Scanning for Bluetooth LE devices for {duration} seconds...")
        print(f"{'='*60}\n")
        
        devices = await BleakScanner.discover(timeout=duration, scanning_mode='active')
        self.discovered_devices = [d for d in devices]  # Only devices with name
        
        return self.discovered_devices
    
    def display_devices(self):
        """Displays discovered devices"""
        if not self.discovered_devices:
            print("No BLE devices found")
            return
        
        print(f"\n{'='*60}")
        print("BLE Devices Found:")
        print(f"{'='*60}\n")
        
        for idx, device in enumerate(self.discovered_devices, 1):
            print(f"{idx}. Address: {device.address}")
            print(f"   Name: {device.name or 'No name'}")
            print(f"   RSSI: N/A dBm")  # Will be shown in select_device
            print(f"   {'-'*56}")
    
    async def select_device(self) -> Optional[BLEDevice]:
        """Allows user to select a device"""
        self.display_devices()
        
        if not self.discovered_devices:
            return None
        
        while True:
            try:
                choice = input(f"\nSelect a device (1-{len(self.discovered_devices)}) or 'q' to exit: ").strip()
                
                if choice.lower() == 'q':
                    return None
                
                idx = int(choice) - 1
                if 0 <= idx < len(self.discovered_devices):
                    device = self.discovered_devices[idx]
                    print(f"\nDevice selected: {device.name} ({device.address})")
                    
                    self.test_results['device_info'] = {
                        'name': device.name,
                        'address': device.address,
                        'rssi': 'N/A'
                    }
                    
                    return device
                else:
                    print("Invalid number, try again")
            except ValueError:
                print("Invalid input, enter a number")
    
    async def discover_characteristics(self, device: BLEDevice) -> Dict:
        """Discovers BLE characteristics of the device"""
        print(f"\n{'='*60}")
        print(f"Analyzing device characteristics...")
        print(f"{'='*60}\n")
        
        characteristics = {
            'write': [],
            'read': [],
            'notify': [],
            'all': []
        }
        
        try:
            async with BleakClient(device.address, timeout=20.0) as client:
                print(f"Connected to {device.name}\n")
                
                # Special login procedure for MELK and MODELX devices
                # Must be done BEFORE full service discovery or device will disconnect
                if device.name and (device.name.lower().startswith("melk") or device.name.lower().startswith("modelx")):
                    print(f"Device {device.name} requires special login procedure...")
                    print("Getting initial services to find write characteristic...\n")
                    
                    # Force service discovery
                    try:
                        temp_services = await client.get_services()
                    except Exception as e:
                        print(f"Could not get services for login: {e}")
                        temp_services = client.services
                    
                    write_char = None
                    read_char = None
                    
                    for service in temp_services:
                        for char in service.characteristics:
                            if char.uuid in KNOWN_WRITE_UUIDS or 'write' in char.properties or 'write-without-response' in char.properties:
                                write_char = char.uuid
                                print(f"Found write characteristic: {write_char}")
                            if char.uuid in KNOWN_READ_UUIDS:
                                read_char = char.uuid
                                print(f"Found read characteristic (used as write): {read_char}")
                            if read_char and write_char:
                                break
                        if read_char and write_char:
                            break
                   
                    if read_char:
                        self.read_uuid = read_char
                        print(f"Found read characteristic: {read_char}")

                    if write_char:
                        self.write_uuid = write_char
                        # Execute login sequence
                        print("Executing login commands...")
                        try:
                            await client.write_gatt_char(write_char, bytes([0x7e, 0x07, 0x83]), response=False)
                            print("  ✓ Sent: 7e 07 83")
                            await asyncio.sleep(1)
                            await client.write_gatt_char(write_char, bytes([0x7e, 0x04, 0x04]), response=False)
                            print("  ✓ Sent: 7e 04 04")
                            await asyncio.sleep(1)
                            print("✓ Login procedure completed!\n")
                        except Exception as e:
                            print(f"✗ Login procedure failed: {e}\n")
                            raise
                    else:
                        print("✗ Could not find write characteristic for login\n")
                        raise Exception("No write characteristic found for login")
                
                # Now discover all services properly
                print("Discovering all services and characteristics...\n")
                for service in client.services:
                    print(f"Service: {service.uuid}")
                    
                    for char in service.characteristics:
                        char_info = {
                            'uuid': char.uuid,
                            'properties': char.properties,
                            'service': service.uuid
                        }
                        characteristics['all'].append(char_info)
                        
                        print(f"   └─ Characteristic: {char.uuid}")
                        print(f"      Properties: {', '.join(char.properties)}")
                        
                        if 'write' in char.properties or 'write-without-response' in char.properties:
                            characteristics['write'].append(char_info)
                            print(f"      ✍️  WRITE available")
                        
                        if 'read' in char.properties:
                            characteristics['read'].append(char_info)
                            print(f"      📖 READ available")
                        
                        if 'notify' in char.properties:
                            characteristics['notify'].append(char_info)
                            print(f"      🔔 NOTIFY available")
                        
                        print()
                
                self.test_results['characteristics'] = characteristics
                
        except Exception as e:
            print(f"Connection error: {e}")
            return characteristics
        
        return characteristics
    
    async def select_write_characteristic(self, characteristics: Dict) -> Optional[str]:
        """Selects the write characteristic"""
        print(f"\n{'='*60}")
        print("WRITE Characteristic Selection")
        print(f"{'='*60}\n")
        
        # Check if there are known characteristics
        write_chars = characteristics.get('write', [])
        
        if not write_chars:
            print("No write characteristics found")
            return None
        
        # Search for known characteristics
        known_found = []
        for char in write_chars:
            if char['uuid'] in KNOWN_WRITE_UUIDS:
                known_found.append(char)
        
        if known_found:
            print(f"Found {len(known_found)} known characteristics:\n")
            for char in known_found:
                print(f"   - {char['uuid']}")
            
            if len(known_found) == 1:
                selected = known_found[0]['uuid']
                print(f"\nUsing known characteristic: {selected}")
                return selected
        
        # If there are no known ones or there are multiple, show all
        print(f"\nAvailable write characteristics:\n")
        for idx, char in enumerate(write_chars, 1):
            known = "[KNOWN]" if char['uuid'] in KNOWN_WRITE_UUIDS else ""
            print(f"{idx}. {char['uuid']} {known}")
        
        while True:
            try:
                choice = input(f"\nSelect characteristic (1-{len(write_chars)}): ").strip()
                idx = int(choice) - 1
                
                if 0 <= idx < len(write_chars):
                    selected = write_chars[idx]['uuid']
                    print(f"\nCharacteristic selected: {selected}")
                    return selected
                else:
                    print("Invalid number")
            except ValueError:
                print("Invalid input")

    async def select_read_characteristic(self, characteristics: Dict) -> Optional[str]:
        """Selects the read characteristic"""
        print(f"\n{'='*60}")
        print("READ Characteristic Selection")
        print(f"{'='*60}\n")
        
        # Check if there are known characteristics
        read_chars = characteristics.get('read', [])
        
        if not read_chars:
            print("No read characteristics found")
            return None
        
        # Search for known characteristics
        known_found = []
        for char in read_chars:
            if char['uuid'] in KNOWN_READ_UUIDS:
                known_found.append(char)
        
        if known_found:
            print(f"Found {len(known_found)} known characteristics:\n")
            for char in known_found:
                print(f"   - {char['uuid']}")
            
            if len(known_found) == 1:
                selected = known_found[0]['uuid']
                print(f"\nUsing known characteristic: {selected}")
                return selected
        
        # If there are no known ones or there are multiple, show all
        print(f"\nAvailable read characteristics:\n")
        for idx, char in enumerate(read_chars, 1):
            known = "[KNOWN]" if char['uuid'] in KNOWN_READ_UUIDS else ""
            print(f"{idx}. {char['uuid']} {known}")
        
        while True:
            try:
                choice = input(f"\nSelect characteristic (1-{len(read_chars)}): ").strip()
                idx = int(choice) - 1
                
                if 0 <= idx < len(read_chars):
                    selected = read_chars[idx]['uuid']
                    print(f"\nCharacteristic selected: {selected}")
                    return selected
                else:
                    print("Invalid number")
            except ValueError:
                print("Invalid input")
    
    async def _execute_login(self, client: BleakClient, device: BLEDevice, char_uuid: str):
        """Execute login procedure for MELK/MODELX devices"""
        if device.name and (device.name.lower().startswith("melk") or device.name.lower().startswith("modelx")):
            try:
                print("Executing login procedure...")
                await client.write_gatt_char(char_uuid, bytes([0x7e, 0x07, 0x83]), response=False)
                await asyncio.sleep(1)
                await client.write_gatt_char(char_uuid, bytes([0x7e, 0x04, 0x04]), response=False)
                await asyncio.sleep(1)
                print("Login completed!\n")
            except Exception as e:
                print(f"Login procedure failed: {e}\n")
    
    async def test_command(self, client: BleakClient, char_uuid: str, command: List[int], 
                          description: str, ask_user: bool = True, turn_on_first: List[int] = None) -> bool:
        """Tests a command on the device"""
        try:
            # Check if still connected
            if not client.is_connected:
                print(f"   [ERROR] Not connected")
                raise Exception("Client disconnected")
            
            # Turn on the strip first if a working turn_on command is provided
            if turn_on_first is not None:
                try:
                    await client.write_gatt_char(char_uuid, bytes(turn_on_first), response=False)
                    await asyncio.sleep(0.3)  # Wait for the strip to turn on
                except Exception as e:
                    print(f"   [WARNING] Could not turn on strip before test: {e}")
            
            cmd_bytes = bytes(command)
            cmd_hex = ' '.join(f'{b:02x}' for b in cmd_bytes)
            
            print(f"\nTesting: {description}")
            print(f"   Command: {cmd_hex}")
            
            await client.write_gatt_char(char_uuid, cmd_bytes, response=False)
            await asyncio.sleep(0.3)  # Wait a bit between commands
            
            if ask_user:
                while True:
                    response = input("   Did the command work? (y/n/r to relaunch): ").strip().lower()
                    
                    if response == 'y':
                        print("   [OK] Working command registered")
                        return True
                    elif response == 'n':
                        print("   [FAIL] Command doesn't work")
                        return False
                    elif response == 'r':
                        print("   [RETRY] Relaunching command...")
                        if client.is_connected:
                            await client.write_gatt_char(char_uuid, cmd_bytes, response=False)
                            await asyncio.sleep(0.3)
                        else:
                            print("   [ERROR] Not connected, cannot retry")
                            return False
                    else:
                        print("   [WARNING] Invalid response (y/n/r)")
            else:
                await asyncio.sleep(0.5)
                return False
                
        except Exception as e:
            print(f"   [ERROR] {e}")
            return False
    
    async def test_power_commands(self, device: BLEDevice, char_uuid: str):
        """Tests on/off commands"""
        print(f"\n{'='*60}")
        print("TESTING ON/OFF COMMANDS")
        print(f"{'='*60}\n")
        
        max_retries = 3
        for attempt in range(max_retries):
            try:
                async with BleakClient(device.address, timeout=20.0) as client:
                    print(f"Connected to {device.name}\n")
                    
                    # Login for MELK/MODELX devices
                    await self._execute_login(client, device, char_uuid)
                    
                    # STEP 1: Test TURN ON commands
                    print("STEP 1/3: TESTING TURN ON COMMANDS")
                    print("=" * 60)
                    print("KNOWN TURN ON COMMANDS:")
                    print("-" * 60)
                    found_turn_on = False
                    working_turn_on_cmd = None
                    
                    for idx, cmd in enumerate(KNOWN_TURN_ON, 1):
                        if not client.is_connected:
                            print("\n[WARNING] Connection lost, stopping tests...")
                            break
                        
                        if await self.test_command(client, char_uuid, cmd, 
                                                  f"Turn on #{idx} (known)"):
                            self.test_results['working_commands']['turn_on'].append({
                                'command': cmd,
                                'description': f'Known turn on #{idx}',
                                'type': 'known'
                            })
                            found_turn_on = True
                            working_turn_on_cmd = cmd
                            print("\n[OK] Working turn on command found!\n")
                            break
                    
                    # Test new turn on commands only if not found
                    if not found_turn_on and client.is_connected:
                        print(f"\nNEW TURN ON COMMANDS ({len(NEW_TURN_ON_COMMANDS)} commands):")
                        print("-" * 60)
                        print("Testing new commands, press Ctrl+C to skip if taking too long...\n")
                        for idx, cmd in enumerate(NEW_TURN_ON_COMMANDS, 1):
                            if not client.is_connected:
                                print("\n[WARNING] Connection lost, stopping tests...")
                                break
                            
                            if await self.test_command(client, char_uuid, cmd, 
                                                      f"Turn on #{idx} (new)"):
                                self.test_results['working_commands']['turn_on'].append({
                                    'command': cmd,
                                    'description': f'New turn on #{idx}',
                                    'type': 'new'
                                })
                                found_turn_on = True
                                working_turn_on_cmd = cmd
                                print("\n[OK] Working turn on command found!\n")
                                break
                    
                    if not found_turn_on:
                        print("\n[WARNING] No working turn on command found, cannot continue tests\n")
                        return
                    
                    if not client.is_connected:
                        raise Exception("Connection lost during turn on tests")
                    
                    # Wait a bit before turn off tests
                    await asyncio.sleep(1)
                    
                    # STEP 2: Test TURN OFF commands
                    print("\nSTEP 2/3: TESTING TURN OFF COMMANDS")
                    print("=" * 60)
                    print("KNOWN TURN OFF COMMANDS:")
                    print("-" * 60)
                    found_turn_off = False
                    working_turn_off_cmd = None
                    
                    for idx, cmd in enumerate(KNOWN_TURN_OFF, 1):
                        if not client.is_connected:
                            print("\n[WARNING] Connection lost, stopping tests...")
                            break
                        
                        if await self.test_command(client, char_uuid, cmd, 
                                                  f"Turn off #{idx} (known)"):
                            self.test_results['working_commands']['turn_off'].append({
                                'command': cmd,
                                'description': f'Known turn off #{idx}',
                                'type': 'known'
                            })
                            found_turn_off = True
                            working_turn_off_cmd = cmd
                            print("\n[OK] Working turn off command found!\n")
                            break
                    
                    # Test new turn off commands only if not found
                    if not found_turn_off and client.is_connected:
                        print(f"\nNEW TURN OFF COMMANDS ({len(NEW_TURN_OFF_COMMANDS)} commands):")
                        print("-" * 60)
                        print("Testing new commands, press Ctrl+C to skip if taking too long...\n")
                        for idx, cmd in enumerate(NEW_TURN_OFF_COMMANDS, 1):
                            if not client.is_connected:
                                print("\n[WARNING] Connection lost, stopping tests...")
                                break
                            
                            if await self.test_command(client, char_uuid, cmd, 
                                                      f"Turn off #{idx} (new)"):
                                self.test_results['working_commands']['turn_off'].append({
                                    'command': cmd,
                                    'description': f'New turn off #{idx}',
                                    'type': 'new'
                                })
                                found_turn_off = True
                                working_turn_off_cmd = cmd
                                print("\n[OK] Working turn off command found!\n")
                                break
                    
                    if not found_turn_off:
                        print("\n[WARNING] No working turn off command found\n")
                    
                    # STEP 3: Turn ON again to leave the strip ready for other tests
                    if found_turn_on and client.is_connected:
                        await asyncio.sleep(1)
                        print("\nSTEP 3/3: TURNING ON AGAIN FOR NEXT TESTS")
                        print("=" * 60)
                        try:
                            cmd_hex = ' '.join(f'{b:02x}' for b in working_turn_on_cmd)
                            print(f"Sending turn on command: {cmd_hex}")
                            await client.write_gatt_char(char_uuid, bytes(working_turn_on_cmd), response=False)
                            await asyncio.sleep(0.5)
                            print("[OK] Strip is now ON and ready for color/white tests\n")
                        except Exception as e:
                            print(f"[WARNING] Could not turn on strip: {e}\n")
                    
                    print(f"\n{'='*60}")
                    print("POWER COMMAND TESTS COMPLETED")
                    print(f"{'='*60}\n")
                    
                    # If we got here, tests completed successfully
                    return
                    
            except KeyboardInterrupt:
                print("\n\n[INFO] Tests skipped by user")
                raise
            except Exception as e:
                print(f"\nConnection error (attempt {attempt + 1}/{max_retries}): {e}")
                if attempt < max_retries - 1:
                    print("Retrying in 2 seconds...")
                    await asyncio.sleep(2)
                else:
                    print("\nMax retries reached, giving up on power command tests")
                    return
    
    async def test_color_commands(self, device: BLEDevice, char_uuid: str):
        """Tests RGB color commands"""
        print(f"\n{'='*60}")
        print("TESTING RGB COLOR COMMANDS")
        print(f"{'='*60}\n")
        
        # Get working turn on command from previous tests
        turn_on_cmd = None
        if self.test_results['working_commands']['turn_on']:
            turn_on_cmd = self.test_results['working_commands']['turn_on'][0]['command']
            print(f"[INFO] Will turn on strip before each test using: {' '.join(f'{b:02x}' for b in turn_on_cmd)}\n")
        
        # Test colors
        test_colors = [
            (255, 0, 0, "Red"),
            (0, 255, 0, "Green"),
            (0, 0, 255, "Blue"),
        ]
        
        try:
            async with BleakClient(device.address, timeout=20.0) as client:
                print(f"Connected to {device.name}\n")
                
                # Login for MELK/MODELX devices
                await self._execute_login(client, device, char_uuid)
                
                found_color = False
                for idx, cmd_func in enumerate(NEW_COLOR_COMMANDS, 1):
                    if found_color:
                        break
                    
                    print(f"\nTesting color command #{idx}:")
                    print("Testing all 3 colors (Red, Green, Blue)...\n")
                    
                    colors_worked = 0
                    
                    for r, g, b, color_name in test_colors:
                        cmd = cmd_func(r, g, b)
                        if await self.test_command(client, char_uuid, cmd, 
                                                  f"Color {color_name} (R:{r}, G:{g}, B:{b})", turn_on_first=turn_on_cmd):
                            colors_worked += 1
                    
                    # If at least 2 out of 3 colors worked, consider it a success
                    if colors_worked >= 2:
                        self.test_results['working_commands']['color'].append({
                            'command_template': 'lambda r, g, b: ' + str([hex(x) if isinstance(x, int) else 'r' if x == test_colors[0][0] else 'g' if x == test_colors[0][1] else 'b' for x in cmd_func(0, 0, 0)]),
                            'description': f'Color command #{idx}',
                            'test_values': test_colors,
                            'colors_confirmed': colors_worked
                        })
                        found_color = True
                        print(f"\n[OK] Working color command found ({colors_worked}/3 colors confirmed), tests completed!\n")
                        break
                    elif colors_worked > 0:
                        print(f"\n[WARNING] Only {colors_worked}/3 colors worked, trying next command template...\n")
                    else:
                        print("\n[FAIL] No colors worked with this command template\n")
                        
        except Exception as e:
            print(f"\nError during tests: {e}")
    
    async def test_white_commands(self, device: BLEDevice, char_uuid: str):
        """Tests white light commands"""
        print(f"\n{'='*60}")
        print("TESTING WHITE LIGHT COMMANDS")
        print(f"{'='*60}\n")
        
        # Get working turn on command from previous tests
        turn_on_cmd = None
        if self.test_results['working_commands']['turn_on']:
            turn_on_cmd = self.test_results['working_commands']['turn_on'][0]['command']
            print(f"[INFO] Will turn on strip before each test using: {' '.join(f'{b:02x}' for b in turn_on_cmd)}\n")
        
        max_retries = 3
        for attempt in range(max_retries):
            try:
                async with BleakClient(device.address, timeout=20.0) as client:
                    print(f"Connected to {device.name}\n")
                    
                    # Login for MELK/MODELX devices
                    await self._execute_login(client, device, char_uuid)
                    
                    # Test known commands
                    print("KNOWN WHITE COMMANDS:")
                    print("-" * 60)
                    found_white = False
                    for idx, cmd in enumerate(KNOWN_WHITE, 1):
                        if not client.is_connected:
                            print("\n[WARNING] Connection lost, stopping tests...")
                            break
                        
                        if await self.test_command(client, char_uuid, cmd, 
                                                  f"White #{idx} (known)", turn_on_first=turn_on_cmd):
                            self.test_results['working_commands']['white'].append({
                                'command': cmd,
                                'description': f'Known white #{idx}',
                                'type': 'known'
                            })
                            found_white = True
                            print("\n[OK] Working white command found, tests completed!\n")
                            break
                    
                    # Test new commands only if not found
                    if not found_white and client.is_connected:
                        print(f"\nNEW WHITE COMMANDS ({len(NEW_WHITE_COMMANDS)} commands):")
                        print("-" * 60)
                        for idx, cmd_func in enumerate(NEW_WHITE_COMMANDS, 1):
                            if not client.is_connected:
                                print("\n[WARNING] Connection lost, stopping tests...")
                                break
                            
                            cmd = cmd_func(200)  # Test with brightness 200
                            if await self.test_command(client, char_uuid, cmd, 
                                                      f"White #{idx} (brightness: 200)", turn_on_first=turn_on_cmd):
                                self.test_results['working_commands']['white'].append({
                                    'command_template': f'lambda brightness: {[hex(x) if isinstance(x, int) else "brightness" for x in cmd]}',
                                    'description': f'New white #{idx}',
                                    'type': 'new'
                                })
                                found_white = True
                                print("\n[OK] Working white command found, tests completed!\n")
                                break
                    
                    return
                    
            except KeyboardInterrupt:
                print("\n\n[INFO] Tests skipped by user")
                raise
            except Exception as e:
                print(f"\nConnection error (attempt {attempt + 1}/{max_retries}): {e}")
                if attempt < max_retries - 1:
                    print("Retrying in 2 seconds...")
                    await asyncio.sleep(2)
                else:
                    print("\nMax retries reached, skipping white command tests")
                    return
    
    async def test_color_temp_commands(self, device: BLEDevice, char_uuid: str):
        """Tests color temperature commands"""
        print(f"\n{'='*60}")
        print("TESTING COLOR TEMPERATURE COMMANDS")
        print(f"{'='*60}\n")
        
        # Get working turn on command from previous tests
        turn_on_cmd = None
        if self.test_results['working_commands']['turn_on']:
            turn_on_cmd = self.test_results['working_commands']['turn_on'][0]['command']
            print(f"[INFO] Will turn on strip before each test using: {' '.join(f'{b:02x}' for b in turn_on_cmd)}\n")
        
        max_retries = 3
        for attempt in range(max_retries):
            try:
                async with BleakClient(device.address, timeout=20.0) as client:
                    print(f"Connected to {device.name}\n")
                    
                    # Login for MELK/MODELX devices
                    await self._execute_login(client, device, char_uuid)
                    
                    # Test known commands
                    print("KNOWN COLOR TEMP COMMANDS:")
                    print("-" * 60)
                    found_color_temp = False
                    for idx, cmd in enumerate(KNOWN_COLOR_TEMP, 1):
                        if not client.is_connected:
                            print("\n[WARNING] Connection lost, stopping tests...")
                            break
                        
                        if await self.test_command(client, char_uuid, cmd, 
                                                  f"Color temp #{idx} (known)", turn_on_first=turn_on_cmd):
                            self.test_results['working_commands']['color_temp'].append({
                                'command': cmd,
                                'description': f'Known color temp #{idx}',
                                'type': 'known'
                            })
                            found_color_temp = True
                            print("\n[OK] Working color temp command found, tests completed!\n")
                            break
                    
                    # Test new commands only if not found
                    if not found_color_temp and client.is_connected:
                        print(f"\nNEW COLOR TEMP COMMANDS ({len(NEW_COLOR_TEMP_COMMANDS)} commands):")
                        print("-" * 60)
                        for idx, cmd_func in enumerate(NEW_COLOR_TEMP_COMMANDS, 1):
                            if not client.is_connected:
                                print("\n[WARNING] Connection lost, stopping tests...")
                                break
                            
                            cmd = cmd_func(50, 50)  # 50% warm, 50% cold
                            if await self.test_command(client, char_uuid, cmd, 
                                                      f"Color temp #{idx} (50% warm/cold)", turn_on_first=turn_on_cmd):
                                self.test_results['working_commands']['color_temp'].append({
                                    'command_template': f'lambda warm, cold: {[hex(x) if isinstance(x, int) else "warm" if x == 50 else "cold" for x in cmd]}',
                                    'description': f'New color temp #{idx}',
                                    'type': 'new'
                                })
                                found_color_temp = True
                                print("\n[OK] Working color temp command found, tests completed!\n")
                                break
                    
                    return
                    
            except KeyboardInterrupt:
                print("\n\n[INFO] Tests skipped by user")
                raise
            except Exception as e:
                print(f"\nConnection error (attempt {attempt + 1}/{max_retries}): {e}")
                if attempt < max_retries - 1:
                    print("Retrying in 2 seconds...")
                    await asyncio.sleep(2)
                else:
                    print("\nMax retries reached, skipping color temp command tests")
                    return
    
    async def test_query_commands(self, device: BLEDevice, char_uuid: str, read_uuid: Optional[str] = None):
        """Test query/status commands to find which one works"""
        print(f"\n{'='*60}")
        print("QUERY/STATUS COMMAND TESTING")
        print(f"{'='*60}\n")
        
        print(f"Testing {len(QUERY_COMMANDS)} query commands...")
        print("Query commands are used to read the current state of the LED strip.")
        print("(Note: Many strips don't support queries, this is optional)\n")
        
        max_retries = 3
        for attempt in range(max_retries):
            try:
                async with BleakClient(device.address, timeout=20.0) as client:
                    print(f"Connected to {device.name}\n")
                    
                    # Login for MELK/MODELX devices
                    await self._execute_login(client, device, char_uuid)
                    
                    # Enable notifications to detect responses
                    notification_received = False
                    
                    def notification_handler(sender, data):
                        nonlocal notification_received
                        notification_received = True
                        print(f"  ✓ Response received: {' '.join(f'{b:02x}' for b in data)}")
                    
                    if read_uuid:
                        try:
                            await client.start_notify(read_uuid, notification_handler)
                            print(f"[INFO] Notifications enabled on {read_uuid}\n")
                        except Exception as e:
                            print(f"[WARNING] Could not enable notifications: {e}\n")
                    
                    found_query = False
                    
                    for idx, (cmd, description) in enumerate(QUERY_COMMANDS, 1):
                        if not client.is_connected:
                            print("\n[WARNING] Connection lost, stopping tests...")
                            break
                        
                        notification_received = False
                        cmd_hex = ' '.join(f'{b:02x}' for b in cmd)
                        print(f"[{idx}/{len(QUERY_COMMANDS)}] Testing: {description}")
                        print(f"  Command: {cmd_hex}")
                        
                        try:
                            await client.write_gatt_char(char_uuid, bytes(cmd), response=False)
                            await asyncio.sleep(0.5)  # Wait for potential response
                            
                            if notification_received:
                                self.test_results['working_commands']['query'] = [{
                                    'command': cmd,
                                    'description': description,
                                    'hex': cmd_hex
                                }]
                                found_query = True
                                print(f"\n[OK] Working query command found: {description}\n")
                                break
                            else:
                                print("  ✗ No response")
                                
                        except Exception as e:
                            print(f"  ✗ Error: {e}")
                    
                    if read_uuid:
                        try:
                            await client.stop_notify(read_uuid)
                        except:
                            pass
                    
                    if not found_query:
                        print("\n[INFO] No working query command found (device may not support status queries)")
                        print("[INFO] This is normal for many LED strips, they work without query support\n")
                    
                    print(f"\n{'='*60}")
                    print("QUERY COMMAND TESTS COMPLETED")
                    print(f"{'='*60}\n")
                    return
                    
            except KeyboardInterrupt:
                print("\n\n[INFO] Tests skipped by user")
                raise
            except Exception as e:
                print(f"\nConnection error (attempt {attempt + 1}/{max_retries}): {e}")
                if attempt < max_retries - 1:
                    print("Retrying in 2 seconds...")
                    await asyncio.sleep(2)
                else:
                    print("\nMax retries reached, skipping query command tests")
                    return

    async def test_custom_commands(self, device: BLEDevice, char_uuid: str):
        """Allows user to test their own commands"""
        print(f"\n{'='*60}")
        print("CUSTOM COMMAND TESTING")
        print(f"{'='*60}\n")
        
        # Get working turn on command from previous tests
        turn_on_cmd = None
        if self.test_results['working_commands']['turn_on']:
            turn_on_cmd = self.test_results['working_commands']['turn_on'][0]['command']
            print(f"[INFO] Will turn on strip before each test using: {' '.join(f'{b:02x}' for b in turn_on_cmd)}\n")
        
        print("You can test your own commands in hexadecimal format.")
        print("Example: 7e 00 04 f0 00 01 ff 00 ef")
        print("Type 'q' to finish.\n")
        
        try:
            async with BleakClient(device.address, timeout=20.0) as client:
                print(f"Connected to {device.name}\n")
                
                # Login for MELK/MODELX devices
                await self._execute_login(client, device, char_uuid)
                
                while True:
                    cmd_input = input("Enter command (hex separated by spaces) or 'q': ").strip()
                    
                    if cmd_input.lower() == 'q':
                        break
                    
                    try:
                        # Parse hexadecimal command
                        cmd = [int(x, 16) for x in cmd_input.split()]
                        
                        description = input("   Command description: ").strip()
                        
                        if await self.test_command(client, char_uuid, cmd, description, turn_on_first=turn_on_cmd):
                            self.test_results['custom_commands'].append({
                                'command': cmd,
                                'description': description,
                                'hex': cmd_input
                            })
                            
                    except ValueError:
                        print("   Invalid format. Use hex values separated by spaces.")
                    except Exception as e:
                        print(f"   Error: {e}")
                        
        except Exception as e:
            print(f"\nError during tests: {e}")
    
    def generate_report(self):
        """Generates a complete results report"""
        print(f"\n{'='*60}")
        print("LED STRIP DISCOVERY REPORT")
        print(f"{'='*60}\n")
        
        # Device information
        print("DEVICE INFORMATION:")
        print("-" * 60)
        info = self.test_results['device_info']
        print(f"Name: {info.get('name', 'N/A')}")
        print(f"MAC Address: {info.get('address', 'N/A')}")
        print(f"RSSI: {info.get('rssi', 'N/A')} dBm")
        
        # Characteristics
        print(f"\nBLE CHARACTERISTICS:")
        print("-" * 60)
        chars = self.test_results['characteristics']
        print(f"Write: {len(chars.get('write', []))} characteristics")
        print(f"Read: {len(chars.get('read', []))} characteristics")
        print(f"Notify: {len(chars.get('notify', []))} characteristics")
        
        if chars.get('write'):
            print(f"\nWrite characteristics:")
            for char in chars['write']:
                print(f"  - {char['uuid']}")
        
        # Working commands
        working = self.test_results['working_commands']
        
        print(f"\nWORKING COMMANDS FOUND:")
        print("=" * 60)
        
        # Turn on
        if working['turn_on']:
            print(f"\nTURN ON ({len(working['turn_on'])} commands):")
            for cmd_info in working['turn_on']:
                cmd_hex = ' '.join(f'{b:02x}' for b in cmd_info['command'])
                print(f"  - {cmd_info['description']}")
                print(f"    Command: {cmd_hex}")
                print(f"    Type: {cmd_info.get('type', 'N/A')}")
        else:
            print(f"\nTURN ON: No working commands found")
        
        # Turn off
        if working['turn_off']:
            print(f"\nTURN OFF ({len(working['turn_off'])} commands):")
            for cmd_info in working['turn_off']:
                cmd_hex = ' '.join(f'{b:02x}' for b in cmd_info['command'])
                print(f"  - {cmd_info['description']}")
                print(f"    Command: {cmd_hex}")
                print(f"    Type: {cmd_info.get('type', 'N/A')}")
        else:
            print(f"\nTURN OFF: No working commands found")
        
        # Color
        if working['color']:
            print(f"\nRGB COLOR ({len(working['color'])} commands):")
            for cmd_info in working['color']:
                print(f"  - {cmd_info['description']}")
                print(f"    Template: {cmd_info.get('command_template', 'N/A')}")
        else:
            print(f"\nRGB COLOR: No working commands found")
        
        # White
        if working['white']:
            print(f"\nWHITE ({len(working['white'])} commands):")
            for cmd_info in working['white']:
                if 'command' in cmd_info:
                    cmd_hex = ' '.join(f'{b:02x}' for b in cmd_info['command'])
                    print(f"  - {cmd_info['description']}")
                    print(f"    Command: {cmd_hex}")
                else:
                    print(f"  - {cmd_info['description']}")
                    print(f"    Template: {cmd_info.get('command_template', 'N/A')}")
        else:
            print(f"\nWHITE: No working commands found")
        
        # Color temperature
        if working['color_temp']:
            print(f"\nCOLOR TEMPERATURE ({len(working['color_temp'])} commands):")
            for cmd_info in working['color_temp']:
                if 'command' in cmd_info:
                    cmd_hex = ' '.join(f'{b:02x}' for b in cmd_info['command'])
                    print(f"  - {cmd_info['description']}")
                    print(f"    Command: {cmd_hex}")
                else:
                    print(f"  - {cmd_info['description']}")
                    print(f"    Template: {cmd_info.get('command_template', 'N/A')}")
        else:
            print(f"\nCOLOR TEMPERATURE: No working commands found")
        
        # Query/Status
        if working['query']:
            print(f"\nQUERY/STATUS ({len(working['query'])} commands):")
            for cmd_info in working['query']:
                print(f"  - {cmd_info['description']}")
                print(f"    Command: {cmd_info['hex']}")
        else:
            print(f"\nQUERY/STATUS: No working commands found (this is normal)")
        
        # Custom commands
        if self.test_results['custom_commands']:
            print(f"\nCUSTOM COMMANDS ({len(self.test_results['custom_commands'])} commands):")
            for cmd_info in self.test_results['custom_commands']:
                print(f"  - {cmd_info['description']}")
                print(f"    Command: {cmd_info['hex']}")
        
        # Save to JSON file
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"led_discovery_{info.get('address', 'unknown').replace(':', '')}_{timestamp}.json"
        
        try:
            with open(filename, 'w') as f:
                json.dump(self.test_results, f, indent=2)
            print(f"\nReport saved to: {filename}")
        except Exception as e:
            print(f"\nError saving report: {e}")
        
        print(f"\n{'='*60}\n")


async def main():
    """Main function"""
    discovery = LEDStripDiscovery()
    
    print("""
    ============================================================
       BLE LED STRIP DISCOVERY TOOL
    
       This tool will help you discover commands for
       unknown BLE LED strips
    ============================================================
    """)
    
    try:
        # 1. Scan devices
        await discovery.scan_devices(duration=30)
        
        # 2. Select device
        device = await discovery.select_device()
        if not device:
            print("\nProcess cancelled")
            return
        
        # 3. Discover characteristics
        characteristics = await discovery.discover_characteristics(device)
        
        # 4. Select write and read characteristic
        char_uuid = await discovery.select_write_characteristic(characteristics)
        if not char_uuid:
            print("\nCould not select write characteristic")
            return
        
        read_uuid = await discovery.select_read_characteristic(characteristics)
        if not read_uuid:
            print("\nCould not select read characteristic")
            return
        else:
            discovery.read_uuid = read_uuid
        
        # 5. Test on/off commands
        response = input("\nTest on/off commands? (y/n): ").strip().lower()
        if response == 'y':
            await discovery.test_power_commands(device, char_uuid)
        
        # 6. Test white commands
        response = input("\nTest white light commands? (y/n): ").strip().lower()
        if response == 'y':
            await discovery.test_white_commands(device, char_uuid)
        
        # 7. Test color temperature commands
        response = input("\nTest color temperature commands? (y/n): ").strip().lower()
        if response == 'y':
            await discovery.test_color_temp_commands(device, char_uuid)
        
        # 8. Test RGB color commands
        response = input("\nTest RGB color commands? (y/n): ").strip().lower()
        if response == 'y':
            await discovery.test_color_commands(device, char_uuid)
        
        # 9. Test query/status commands
        response = input("\nTest query/status commands? (y/n): ").strip().lower()
        if response == 'y':
            await discovery.test_query_commands(device, char_uuid, discovery.read_uuid)
        
        # 10. Custom commands
        response = input("\nTest custom commands? (y/n): ").strip().lower()
        if response == 'y':
            await discovery.test_custom_commands(device, char_uuid)
        
        # 11. Generate report
        response = input("\nShow final report? (y/n): ").strip().lower()
        if response == 'y':
            discovery.generate_report()
        
        print("\nProcess completed if you discover commands to turn on an turn off you can post your final report in https://github.com/dave-code-ruiz/elkbledom/issues !")
        
    except KeyboardInterrupt:
        print("\n\nProcess interrupted by user")
    except Exception as e:
        print(f"\nError: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
