# Sniffing BLE Traffic for Protocol Analysis

This guide will help you capture Bluetooth Low Energy (BLE) traffic from your unsupported LED device to analyze the protocol and add support for new devices in the elkbledom integration.

## Why Sniff BLE Traffic?

When we encounter a new LED device model that isn't supported by this integration, we need to understand how the official app communicates with the device. By capturing and analyzing the BLE packets, we can:

- Identify command structures (power on/off, colors, brightness, effects)
- Understand packet formats and checksums
- Map effect IDs and speed values
- Discover device-specific features

## Method 1: nRF52840 USB Dongle (Recommended)

This is the most reliable and comprehensive method for capturing BLE traffic.

### Hardware Requirements

- **nRF52840 USB Dongle** (~$10-15 USD)
  - Official: [Nordic Semiconductor nRF52840 Dongle (PCA10059)](https://www.nordicsemi.com/Products/Development-hardware/nRF52840-Dongle)
  - Compatible alternatives available from various vendors (search "nRF52840 dongle")
- USB-A port on your computer (or USB-C adapter)

### Software Requirements

- **Wireshark** (latest version with BLE support)
  - Download from [wireshark.org](https://www.wireshark.org/download.html)
- **nRF Sniffer for Bluetooth LE**
  - Download from [Nordic's website](https://www.nordicsemi.com/Products/Development-tools/nRF-Sniffer-for-Bluetooth-LE)
- **nrfutil** (for flashing the dongle)
  - Install via pip: `pip install nrfutil`

### Setup Instructions

#### Step 1: Flash the Sniffer Firmware

1. Download the nRF Sniffer for Bluetooth LE package from Nordic
2. Extract the package and locate the firmware hex file:
   - Usually in `nrf_sniffer_for_bluetooth_le/hex/sniffer_nrf52840dongle_nrf52840_<version>.hex`
3. Put the dongle into DFU (Device Firmware Update) mode:
   - Plug in the dongle
   - Press and hold the small button on the side
   - While holding, unplug and replug the USB dongle
   - Release the button - the LED should pulse red
4. Flash the firmware:
   ```bash
   nrfutil dfu usb-serial -pkg sniffer_nrf52840dongle_nrf52840_<version>.zip -p /dev/ttyACM0
   ```
   - On Windows, replace `/dev/ttyACM0` with the appropriate COM port (e.g., `COM3`)
   - On macOS, use `/dev/cu.usbmodem<number>`
5. After successful flashing, unplug and replug the dongle

#### Step 2: Install Wireshark Plugin

1. Extract the nRF Sniffer package
2. Locate the Wireshark extcap plugin:
   - `nrf_sniffer_for_bluetooth_le/extcap/`
3. Copy the plugin files to Wireshark's extcap directory:
   - **Linux**: `~/.config/wireshark/extcap/` or `/usr/lib/wireshark/extcap/`
   - **Windows**: `%APPDATA%\Wireshark\extcap\` or `C:\Program Files\Wireshark\extcap\`
   - **macOS**: `/Applications/Wireshark.app/Contents/MacOS/extcap/`
4. Make the plugin executable (Linux/macOS):
   ```bash
   chmod +x ~/.config/wireshark/extcap/nrf_sniffer_ble.sh
   ```
5. Restart Wireshark

#### Step 3: Capture BLE Traffic

1. **Start Wireshark**
2. **Select the nRF Sniffer interface**:
   - Look for "nRF Sniffer for Bluetooth LE" in the interface list
   - Click the gear icon next to it to configure
3. **Configure the sniffer**:
   - **Device**: Select your nRF52840 dongle (e.g., `/dev/ttyACM0` or `COM3`)
   - **Advertising Channel**: Leave as "All advertising channels" (37, 38, 39)
   - **BLE PHY**: Leave as "Auto" or select "1M" for most devices
4. **Start capture**:
   - Click "Start" to begin capturing
   - The dongle LED should turn green
5. **Identify your device**:
   - Look for advertising packets in Wireshark
   - Filter by device name or MAC address:
     ```
     bluetooth.device_name contains "ELK" or bluetooth.device_name contains "MELK" or bluetooth.device_name contains "LEDBLE" or btle.advertising_address == aa:bb:cc:dd:ee:ff
     ```
   - Common device name patterns: `ELK-BLEDOM`, `ELK-BLEDOB`, `MELK-`, `LEDBLE-`, `XROCKER`
6. **Follow the device**:
   - Right-click on an advertising packet from your device
   - Select "Follow" → "Bluetooth LE Connection"
   - This will track the connection automatically
7. **Control the device**:
   - Open the official app on your phone
   - Connect to the LED device
   - Perform various actions (see "What to Capture" section below)
8. **Stop and save**:
   - Stop the capture in Wireshark
   - Save as `.pcap` or `.pcapng` file
   - File → Save As → choose location

#### Tips for nRF Sniffer

- **Distance matters**: Keep the dongle relatively close to your LED device (within 1-2 meters)
- **Reduce interference**: Turn off other Bluetooth devices if possible
- **Multiple captures**: If you miss the connection, restart the capture and reconnect the app
- **LED indicators**:
  - Green: Capturing
  - Red pulsing: DFU mode
  - Off: Not powered or not running

### Analyzing the Capture

Once you have the capture:

1. **Filter for writes**:
   ```wireshark
   btatt.opcode == 0x52 || btatt.opcode == 0x12
   ```
   - `0x52` = Write Request
   - `0x12` = Write Command
2. **Look for the control characteristic**:
   - Usually `0000fff3-0000-1000-8000-00805f9b34fb` (write) for ELK/MELK devices
   - Or `0000ffe1-0000-1000-8000-00805f9b34fb` (write) for LEDBLE/XROCKER devices
   - Notifications come from `0000fff4-0000-1000-8000-00805f9b34fb` (read/notify) for ELK/MELK
   - Or `0000ffe2-0000-1000-8000-00805f9b34fb` (read/notify) for LEDBLE/XROCKER
3. **Export packet data**:
   - Right-click on a packet → Copy → "...as Hex Dump"
   - Or use File → Export Packet Dissections → as JSON/CSV

---

## Method 2: Android HCI Snoop

This method uses Android's built-in Bluetooth HCI (Host Controller Interface) logging. It's easier to set up but requires an Android device.

### Requirements

- Android device (phone or tablet)
- USB cable for connecting to computer
- ADB (Android Debug Bridge) installed on your computer
  - Download: [Android SDK Platform Tools](https://developer.android.com/studio/releases/platform-tools)
- Your led strip app installed

### Setup Instructions

#### Step 1: Enable Developer Options

1. Open **Settings** on your Android device
2. Navigate to **About Phone** (or **About Device**)
3. Find **Build Number**
4. Tap **Build Number** 7 times rapidly
5. You should see a message: "You are now a developer!"
6. Go back to main Settings

#### Step 2: Enable HCI Snoop Log

1. Go to **Settings** → **System** → **Developer Options**
   - On some devices: **Settings** → **Developer Options**
2. Scroll down to the Debugging section
3. Enable **Bluetooth HCI snoop log**
   - Some devices show "Enable Bluetooth HCI snoop log"
   - Others show "Bluetooth HCI snoop log" with On/Off toggle
4. Some devices will ask you to restart - do so if prompted

#### Step 3: Capture Traffic

1. **Ensure HCI logging is enabled** (green/on)
2. **Forget the device** in Bluetooth settings (if previously paired)
3. **Open the led strip app**
4. **Connect to your LED device**
5. **Perform actions** (see "What to Capture" section below)
6. **Disconnect** when done

#### Step 4: Retrieve the Log File

The log file location varies by Android version and manufacturer:

**Common locations**:
- `/sdcard/btsnoop_hci.log` (some Samsung, older Android)
- `/sdcard/Android/data/btsnoop_hci.log`
- `/data/misc/bluetooth/logs/btsnoop_hci.log` (requires root)
- `/data/misc/bluedroid/btsnoop_hci.log` (older Android)

**Method A: Using ADB (Recommended)**

1. **Connect your device** to computer via USB
2. **Enable USB Debugging** in Developer Options
3. **Authorize computer** (popup on phone)
4. **Pull the log file**:
   ```bash
   # Try common locations
   adb pull /sdcard/btsnoop_hci.log btsnoop_hci.log
   adb pull /sdcard/Android/data/btsnoop_hci.log btsnoop_hci.log
   
   # If you have root access
   adb shell su -c "cp /data/misc/bluetooth/logs/btsnoop_hci.log /sdcard/"
   adb pull /sdcard/btsnoop_hci.log btsnoop_hci.log
   ```
5. **Disable HCI snoop** after capturing (it can fill storage)

**Method B: Using File Manager App**

1. Install a file manager app (e.g., [Solid Explorer](https://play.google.com/store/apps/details?id=pl.solidexplorer2))
2. Navigate to the log location
3. Copy the file to a location you can access
4. Transfer to your computer (USB, cloud, email, etc.)

**Method C: Android Studio**

1. Open **Android Studio**
2. Go to **View** → **Tool Windows** → **Device File Explorer**
3. Navigate to log location
4. Right-click file → **Save As**

#### Step 5: Open in Wireshark

1. **Launch Wireshark**
2. **Open the log**: File → Open → select `btsnoop_hci.log`
3. **Filter for your device**:
   ```wireshark
   bluetooth.addr == aa:bb:cc:dd:ee:ff
   ```
   Replace with your device's MAC address
4. **Filter for ATT writes**:
   ```wireshark
   btatt.opcode == 0x52 || btatt.opcode == 0x12
   ```

### Troubleshooting HCI Snoop

**Problem**: Can't find the log file
- **Solution**: Try all common locations listed above
- **Solution**: Check if HCI logging is actually enabled
- **Solution**: Some devices save to different locations - check XDA forums for your device model

**Problem**: Log file is empty
- **Solution**: Ensure you performed Bluetooth actions after enabling logging
- **Solution**: Restart Bluetooth or reboot device after enabling
- **Solution**: Some devices require Bluetooth to be turned off and on again

**Problem**: ADB not authorized
- **Solution**: Check phone for authorization popup
- **Solution**: Revoke USB debugging authorizations in Developer Options, then try again
- **Solution**: Run `adb kill-server` then `adb start-server`

**Problem**: File too large
- **Solution**: The log captures ALL Bluetooth traffic - filter in Wireshark
- **Solution**: Clear the log before capturing: Turn HCI logging off, delete old log, turn back on

---

## Method 3: iOS Packet Logging (Advanced)

**Note**: iOS BLE sniffing is significantly more difficult than Android and generally not recommended unless you have specific expertise.

### Requirements

- iOS device
- macOS computer with Xcode installed
- Device must be in developer mode

### Brief Overview

1. Connect iOS device to macOS
2. Open **Xcode** → **Window** → **Devices and Simulators**
3. Select your device
4. Click **gear icon** → **Start Logging**
5. Reproduce the actions
6. Stop logging and save the file
7. The log format is different from standard packet captures and requires parsing

**Recommendation**: Use the nRF52840 dongle method instead for iOS devices - it's much simpler and more reliable.

---

## What to Capture

To help us analyze the protocol, please perform these actions **in order** and note what you're doing:

### Basic Controls

1. **Power ON** - Turn the lights on
2. **Power OFF** - Turn the lights off  
3. **Power ON** again - Turn back on
4. Wait 2-3 seconds between each action

### Colors (Full Brightness)

5. **Pure RED** - RGB (255, 0, 0)
6. **Pure GREEN** - RGB (0, 255, 0)
7. **Pure BLUE** - RGB (0, 0, 255)
8. **Pure WHITE** - RGB (255, 255, 255)
9. **Yellow** - RGB (255, 255, 0)
10. **Cyan** - RGB (0, 255, 255)
11. **Magenta** - RGB (255, 0, 255)

### Brightness

12. **Brightness 100%** - Maximum brightness
13. **Brightness 50%** - Mid-level
14. **Brightness 25%** - Low brightness
15. **Brightness 10%** - Very dim
16. **Brightness 100%** - Back to full

### Effects (if available)

17. **Effect 1** - Select first effect
18. **Effect Speed Slow** - Slowest speed setting
19. **Effect Speed Fast** - Fastest speed setting
20. **Effect Speed Medium** - Middle speed
21. **Effect 2** - Select second effect (if available)
22. **Effect 5** - Select fifth effect (if available)
23. **Effect OFF** - Return to solid color mode

### Special Features (if your device has them)

24. **White/Color Temperature** mode (if separate from RGB)
25. **Segments** (if device has multiple sections)
26. **Music reactive** mode (if available)
27. **Custom effects** or patterns

### Important Notes

- **Wait 2-3 seconds** between each action so packets are clearly separated
- **Make notes** of the timestamp or packet number for each action
- **Try edge cases**: 
  - Brightness 0% (off vs. dim)
  - Rapid changes
  - Multiple quick color changes
  - Disconnecting and reconnecting

---

## Analyzing the Protocol

Once you have the capture, here's what to look for:

### Packet Structure

Most LED strip devices in this integration follow this general structure:

```
[Byte 0] [Byte 1] [Byte 2] [Byte 3+]        [Last Byte]
7e       Variant  Command  Payload          ef or bf
```

**Examples from supported models**:

```
ELK-BLEDOB Power ON:   7e 07 04 ff 00 01 02 01 ef
ELK-BLEDOB Power OFF:  7e 07 04 00 00 00 02 01 ef
ELK-BLEDOB Set RED:    7e 07 05 03 ff 00 00 0a ef
ELK-BLEDOB Set BLUE:   7e 07 05 03 00 00 ff 0a ef

LEDBLE Power ON:       7e 00 04 01 00 00 00 00 ef
LEDBLE Power OFF:      7e 00 04 00 00 00 ff 00 ef
LEDBLE Set GREEN:      7e 00 05 03 00 ff 00 00 ef

XROCKER Power ON:      7b ff 04 01 ff ff ff ff bf
XROCKER Power OFF:     7b ff 04 00 ff ff ff ff bf
```

### Key Observations

1. **Start byte**: Almost always `0x7e` (126), `0x7b` (123) for XROCKER
2. **Variant byte** (byte 1): Model-specific identifier (0x00, 0x04, 0x05, 0x06, 0x07, 0xff)
3. **Command byte** (byte 2): Indicates command type:
   - `0x04` = Power ON/OFF
   - `0x05` = Color or Color Temperature
   - `0x01` = White/Brightness
   - `0x02` = Effect Speed
   - `0x03` = Effect Mode
4. **Payload**: Contains the actual data (RGB values, effect ID, speed, etc.)
5. **End byte**: Usually `0xef` (239), `0xbf` (191) for XROCKER

### Common Patterns

**Power State** (Command 0x04):
- ELK-BLEDOB: `0xff` (byte 3) = ON, `0x00` = OFF
- LEDBLE: `0x01` (byte 3) = ON, `0x00` = OFF
- Some models use `0xf0` for ON

**Color Mode** (Command 0x05, Subcommand 0x03):
- Structure: `7e [variant] 05 03 [R] [G] [B] [modifier] ef`
- RGB values: 0-255 (0x00-0xFF)
- Modifier byte varies by model (0x00, 0x0a, etc.)

**White/Brightness** (Command 0x01):
- Structure: `7e [variant] 01 [intensity] ...`
- Intensity: 0-255 (0x00-0xFF)

**Effects** (Command 0x03):
- Structure: `7e [variant] 03 [effect_id] [mode] ...`
- Effect ID varies by model
- Speed set separately with Command 0x02

**Color Temperature** (Command 0x05, Subcommand 0x02):
- Structure: `7e [variant] 05 02 [warm] [cold] ...`
- Warm + Cold = 100 (percentage distribution)

### Look for Notifications

Some devices send status updates back:
- Check packets on characteristic `0000fff4-0000-1000-8000-00805f9b34fb` (ELK/MELK)
- Or characteristic `0000ffe2-0000-1000-8000-00805f9b34fb` (LEDBLE/XROCKER)
- These echo back the current state
- Helpful for understanding the complete protocol
- Not all models support notifications (MELK models typically don't)

---

## Sharing Your Captures

Once you have captured the traffic, please share:

### What to Include

1. **The capture file** (`.pcap`, `.pcapng`, or `btsnoop_hci.log`)
2. **Device information**:
   - Firmware version (from manufacturer data or app)
   - Model number (0x??)
   - Device name as advertised
   - Where you bought it / brand name
   - Link to product page if available
3. **Your notes**:
   - What action corresponds to which packets
   - Timestamp or packet number for each action
   - Any special features the device has
4. **App information**:
   - App name and version (e.g., "Lotus Lantern", "Happy Lighting", "Duoco Strip", etc.)
   - Download link (Play Store / App Store)
   - Package name for Android apps (helps identify protocol family)

### How to Share

**Option 1: GitHub Issue**
1. Create a new issue at [github.com/dave-code-ruiz/elkbledom/issues](https://github.com/dave-code-ruiz/elkbledom/issues)
2. Title: "New device support: [Device Name] - [Model Number if known]"
3. Attach the capture file (GitHub allows up to 25MB)
4. Include output from BTScan.py or easyBTScan.py
5. Include all the information listed above

**Option 2: Cloud Storage**
1. Upload to Google Drive, Dropbox, WeTransfer, etc.
2. Share the link in a GitHub issue
3. Include your notes and device info in the issue

**Option 3: Pull Request**
If you've already analyzed the protocol and created a working model:
1. Fork the repository
2. Add a new model entry in `custom_components/elkbledom/models.json`
3. Follow the structure of existing models (ELK-BLEDOB, LEDBLE, etc.)
4. Test thoroughly with your physical device
5. Submit a pull request with your changes
6. Include the capture file and notes in the PR description

---

## Privacy Considerations

### What's in the Capture

BLE captures may contain:
- **MAC addresses** of your devices and phone
- **Device names** you've set
- **WiFi credentials** if the device does WiFi provisioning over BLE
- All Bluetooth traffic from your device during the capture period

### Before Sharing

1. **Filter the capture** to only your LED device:
   - In Wireshark: `bluetooth.addr == aa:bb:cc:dd:ee:ff`
   - File → Export Specified Packets → Displayed
2. **Check for sensitive data**:
   - Review the exported file
   - Look for any data you don't want to share
3. **Anonymize if needed**:
   - You can change MAC addresses in the description
   - Remove any personal device names from your notes

---

## Tools and Resources

### Software

- **Wireshark**: [wireshark.org](https://www.wireshark.org/)
- **nRF Sniffer**: [Nordic Semiconductor](https://www.nordicsemi.com/Products/Development-tools/nRF-Sniffer-for-Bluetooth-LE)
- **Android SDK Platform Tools**: [developer.android.com](https://developer.android.com/studio/releases/platform-tools)
- **nrfutil**: `pip install nrfutil`

### Hardware

- **nRF52840 Dongle**: [nordicsemi.com](https://www.nordicsemi.com/Products/Development-hardware/nRF52840-Dongle)
- Generic nRF52840 dongles: Search Amazon, AliExpress, etc.

### Documentation

- **Bluetooth Core Specification**: [bluetooth.com](https://www.bluetooth.com/specifications/specs/)
- **BLE Advertising**: Understanding how devices announce themselves
- **ATT Protocol**: Attribute Protocol used for reading/writing characteristics
- **GATT Services**: Generic Attribute Profile for BLE services

### Community

- **GitHub Issues**: [github.com/dave-code-ruiz/elkbledom/issues](https://github.com/dave-code-ruiz/elkbledom/issues)
- **Home Assistant Community**: [community.home-assistant.io](https://community.home-assistant.io/)
- **Reddit**: r/homeassistant, r/bluetooth

---

## Example Analysis

Here's a real example of analyzing captures from supported devices:

### Example 1: ELK-BLEDOB Power On

```
7e 07 04 ff 00 01 02 01 ef
```

**Breakdown**:
- `7e` - Start byte (always 126 decimal)
- `07` - Variant identifier for ELK-BLEDOB model
- `04` - Command: Power control
- `ff` - Power state: 0xff = ON (255 decimal)
- `00 01 02 01` - Additional parameters (model-specific)
- `ef` - End byte (always 239 decimal)

### Example 2: ELK-BLEDOB Set Red Color

```
7e 07 05 03 ff 00 00 0a ef
```

**Breakdown**:
- `7e` - Start byte
- `07` - Variant identifier
- `05` - Command: Color/Temperature control
- `03` - Subcommand: RGB color mode
- `ff` - Red: 255 (full red)
- `00` - Green: 0 (no green)
- `00` - Blue: 0 (no blue)
- `0a` - Modifier byte (10 decimal, purpose varies)
- `ef` - End byte

### Example 3: LEDBLE Power On (Different Model)

```
7e 00 04 01 00 00 00 00 ef
```

**Breakdown**:
- `7e` - Start byte
- `00` - Variant identifier for LEDBLE model
- `04` - Command: Power control
- `01` - Power state: 0x01 = ON (note: different from ELK-BLEDOB!)
- `00 00 00 00` - Padding/unused bytes
- `ef` - End byte

### Example 4: XROCKER (Completely Different Pattern)

```
7b ff 04 01 ff ff ff ff bf
```

**Breakdown**:
- `7b` - Start byte (123 decimal - different from others!)
- `ff` - Variant identifier for XROCKER
- `04` - Command: Power control
- `01` - Power state: ON
- `ff ff ff ff` - Padding (all 0xff)
- `bf` - End byte (191 decimal - different from others!)

**Key Lessons**:
1. Start/End bytes are usually consistent per manufacturer
2. Variant byte helps identify model family
3. Same command number (0x04) used across models but payloads differ
4. Always capture multiple commands to identify patterns
5. Different manufacturers may use completely different structures

---

## Frequently Asked Questions

**Q: How long should I capture for?**  
A: Just long enough to perform all the actions listed above - usually 2-5 minutes total.

**Q: The capture file is huge (hundreds of MB)**  
A: Filter it in Wireshark to only your device's MAC address before exporting. Most of the data is probably from other Bluetooth devices.

**Q: Can I capture from multiple devices at once?**  
A: Yes, but it's clearer to capture one device at a time to avoid confusion in analysis.

**Q: My device uses WiFi, not Bluetooth**  
A: This integration is specifically for Bluetooth Low Energy (BLE) LED devices. WiFi-based devices require different integrations and are not supported here.

**Q: The official app won't connect during capture**  
A: Try moving the sniffer dongle further away, or try the Android HCI method instead which doesn't interfere with connections.

**Q: I already have Wireshark experience - any shortcuts?**  
A: Look for writes to UUID `fff3` (ELK/MELK) or `ffe1` (LEDBLE/XROCKER), extract just those packets, focus on the value field of ATT Write Request/Command packets. Use the BTScan.py or easyBTScan.py scripts in the repo to quickly identify device characteristics.

**Q: Can I help even if I can't capture traffic?**  
A: Yes! If someone else provides a capture, you can help analyze it and create the model file. Programming knowledge of Python is helpful.

---

## Next Steps

Once traffic is captured and analyzed:

1. **Create a model file** based on an existing similar device
2. **Add the protocol commands** from your analysis
3. **Test thoroughly** with your physical device
4. **Submit a pull request** with your changes
5. **Help others** who have the same device model

Thank you for helping expand device support!