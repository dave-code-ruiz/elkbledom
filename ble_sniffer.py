#!/usr/bin/env python3
"""
BLE Traffic Sniffer for LED Strips
Captures all BLE traffic to discover the command protocol used by the device's app
"""

import asyncio
import sys
from datetime import datetime
from bleak import BleakClient, BleakScanner
from typing import Optional

# Known UUIDs for ELK-BLEDOM
WRITE_UUID = "0000fff3-0000-1000-8000-00805f9b34fb"
NOTIFY_UUID = "0000fff4-0000-1000-8000-00805f9b34fb"
READ_UUID = "00002a00-0000-1000-8000-00805f9b34fb"

class BLESniffer:
    def __init__(self):
        self.captured_commands = []
        self.log_file = f"ble_capture_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        
    def log(self, message: str, also_print: bool = True):
        """Log message to file and optionally print"""
        timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
        log_entry = f"[{timestamp}] {message}"
        
        with open(self.log_file, 'a') as f:
            f.write(log_entry + '\n')
        
        if also_print:
            print(log_entry)
    
    async def find_device(self, device_name: str = "ELK-BLEDOM") -> Optional[str]:
        """Scan for the LED strip device"""
        print(f"Scanning for '{device_name}'...")
        devices = await BleakScanner.discover(timeout=10.0)
        
        for device in devices:
            if device.name and device_name.lower() in device.name.lower():
                print(f"Found: {device.name} ({device.address})")
                return device.address
        
        print(f"Device '{device_name}' not found")
        return None
    
    async def sniff_traffic(self, address: str):
        """Connect and monitor all BLE traffic"""
        print(f"\n{'='*70}")
        print(f"BLE TRAFFIC SNIFFER")
        print(f"{'='*70}\n")
        print(f"Target device: {address}")
        print(f"Log file: {self.log_file}\n")
        print("INSTRUCTIONS:")
        print("1. This script will connect to your LED strip")
        print("2. Open the LED control app on your phone")
        print("3. Try different commands in the app:")
        print("   - Turn ON/OFF")
        print("   - Change colors (Red, Green, Blue, etc.)")
        print("   - Change brightness")
        print("   - Try different modes/effects")
        print("4. All received notifications will be logged")
        print("5. Press Ctrl+C when done\n")
        print(f"{'='*70}\n")
        
        input("Press ENTER when ready to start monitoring...")
        
        try:
            async with BleakClient(address, timeout=20.0) as client:
                print(f"\n✓ Connected to {address}")
                self.log(f"Connected to {address}")
                
                # List all services and characteristics
                print("\nAvailable characteristics:")
                self.log("\n=== DEVICE CHARACTERISTICS ===")
                for service in client.services:
                    for char in service.characteristics:
                        props = ", ".join(char.properties)
                        handle_info = f" [Handle: {char.handle}]"
                        print(f"  {char.uuid}: {props}{handle_info}")
                        self.log(f"Char: {char.uuid} (Handle: {char.handle}, {props})")
                
                # Notification handler
                notification_count = 0
                
                def notification_handler(sender, data):
                    nonlocal notification_count
                    notification_count += 1
                    hex_data = ' '.join(f'{b:02x}' for b in data)
                    msg = f"[#{notification_count}] NOTIFY from {sender.uuid}: {hex_data} (len={len(data)})"
                    self.log(msg)
                    
                    # Try to decode as ASCII if possible
                    try:
                        ascii_data = ''.join(chr(b) if 32 <= b < 127 else '.' for b in data)
                        self.log(f"           ASCII: {ascii_data}", also_print=False)
                    except:
                        pass
                
                # Enable notifications on all possible UUIDs
                notify_uuids = [NOTIFY_UUID, READ_UUID]
                enabled_notifications = []
                
                for uuid in notify_uuids:
                    try:
                        await client.start_notify(uuid, notification_handler)
                        print(f"✓ Notifications enabled on {uuid}")
                        self.log(f"Notifications enabled on {uuid}")
                        enabled_notifications.append(uuid)
                    except Exception as e:
                        print(f"✗ Could not enable notifications on {uuid}: {e}")
                
                if not enabled_notifications:
                    print("\n⚠ WARNING: No notifications could be enabled!")
                    print("The device might not send status updates.\n")
                    print("Note: Some devices don't send notifications - this is normal.")
                    print("Use command_tester.py instead to actively test commands.\n")
                    print("Waiting for notifications... (Press Ctrl+C to stop)\n")
                
                self.log("\n=== MONITORING STARTED ===\n")
                
                # Keep connection alive
                while True:
                    await asyncio.sleep(1)
                    
        except KeyboardInterrupt:
            print("\n\nMonitoring stopped by user")
            self.log("\n=== MONITORING STOPPED ===")
        except Exception as e:
            print(f"\nError: {e}")
            self.log(f"ERROR: {e}")
        
        print(f"\n{'='*70}")
        print(f"Capture complete!")
        print(f"Total notifications received: {notification_count}")
        print(f"Log saved to: {self.log_file}")
        print(f"{'='*70}\n")
        
        if notification_count == 0:
            print("⚠ WARNING: No notifications were received!")
            print("This device might not send status updates via BLE notifications.")
            print("This is normal for many LED strips.")
            print("\nUse command_tester.py instead to actively test commands.\n")

async def main():
    sniffer = BLESniffer()
    
    # Allow custom device name
    device_name = input("Enter device name [ELK-BLEDOM]: ").strip() or "ELK-BLEDOM"
    
    # Find device
    address = await sniffer.find_device(device_name)
    
    if not address:
        # Allow manual address entry
        address = input("\nEnter MAC address manually (or press Enter to exit): ").strip()
        if not address:
            print("Exiting...")
            return
    
    # Start sniffing
    await sniffer.sniff_traffic(address)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nExiting...")
        sys.exit(0)
