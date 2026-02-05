<div align="center">

# ELK-BLEDOM Integration for Home Assistant

[![hacs_badge](https://img.shields.io/badge/HACS-Default-41BDF5.svg)](https://github.com/hacs/integration)
[![GitHub Release](https://img.shields.io/github/release/dave-code-ruiz/elkbledom.svg)](https://github.com/dave-code-ruiz/elkbledom/releases)
[![License](https://img.shields.io/github/license/dave-code-ruiz/elkbledom.svg)](LICENSE)
[![Buy Me A Coffee](https://img.shields.io/badge/Buy%20Me%20A%20Coffee-donate-yellow.svg)](https://www.buymeacoffee.com/davecoderuiz)

## Support

If you find this integration useful, consider supporting the development:

<a href="https://www.buymeacoffee.com/davecoderuiz" target="_blank">
  <img src="https://cdn.buymeacoffee.com/buttons/v2/default-yellow.png" alt="Buy Me A Coffee" height="60">
</a>

**Control your Bluetooth LED strips and bulbs directly from Home Assistant**

[Installation](#installation) • [Supported Devices](#-supported-devices) • [Features](#-features) • [Configuration](#-configuration) • [Troubleshooting](#-troubleshooting)

</div>

---

## Overview

This Home Assistant integration allows you to control Bluetooth Low Energy (BLE) LED strips, bulbs, and light bars that use the **ELK-BLEDOM**, **MELK**, **LEDBLE**, and similar protocols. These devices are commonly sold under various brands and controlled via mobile apps like:

-  **duoCo Strip** ([Play Store](https://play.google.com/store/apps/details?id=shy.smartled))
-  **Lotus Lantern** ([Play Store](https://play.google.com/store/apps/details?id=wl.smartled))
-  **Lotus Lamp X** ([Play Store](https://play.google.com/store/apps/details?id=com.szelk.ledlamppro))
-  **Happy Lighting**

---

## Supported Devices

This integration currently supports the following device models:

<table>
<tr>
<td width="50%">

### ELK Family
- **ELK-BLEDOM**
- **ELK-BLEDOB** 
- **ELK-BLEDDM**
- **ELK-BLE**
- **ELK-BTC**
- **ELK-BULB** 
- **ELK-BULB2** 
- **ELK-LAMPL** 
- **MELK**
- **MELK-OA10**
- **MELK-OC10**
- **MELK-OF10**
- **MELK-OG10**
- **MELK-OG10W**
- **LEDBLE**
- **LED-** (Generic LED strips)
- **JACKYLED**
- **XROCKER**
- **DMRRBA-007** 

</td>
</tr>
</table>

> **Note**: These devices use specific Bluetooth UUIDs:
> - Write UUID: `0000fff3-...` or `0000ffe1-...`
> - Read UUID: `0000fff4-...` or `0000ffe2-...`

### Where to Buy

-  [Amazon LED Strips](https://www.amazon.es/gp/product/B00VFME0Q2) (Example)
-  [LED Light Bar](https://www.amazon.es/bedee-Regulable-Inteligente-Bluetooth-Dormitorio/dp/B0BNPMGR1H) (Example)
-  [MELK Strip](https://www.amazon.es/distancia-Bluetooth-aplicaci%C3%B3n-sincronizaci%C3%B3n-habitaci%C3%B3n/dp/B09VC77GCZ) (Example)
- Search for "ELK-BLEDOM", "MELK LED", or "Bluetooth LED Strip" on your local Amazon

---

## Installation

### Method 1: HACS (Recommended)

1. Open **HACS** in your Home Assistant
2. Go to **Integrations**
7. Search for **"elkbledom"** in HACS
8. Click **Download**
9. Restart Home Assistant

### Method 2: Manual Installation

1. Download the latest release from [GitHub](https://github.com/dave-code-ruiz/elkbledom/releases)
2. Extract and copy the `custom_components/elkbledom` folder to your Home Assistant `config/custom_components/` directory
3. Restart Home Assistant

---

## Dependencies

### System Requirements

This integration requires **Bluetooth support** on your Home Assistant installation. The integration uses:

- **Home Assistant Bluetooth integration** (built-in, enabled by default in recent versions)
- **Python BLE libraries** (automatically installed)

### Optional: Manual Bluetooth Tools

If you want to manually test or troubleshoot Bluetooth connections, you can install `gattool`:

**Debian/Ubuntu/Raspberry Pi OS:**
```bash
sudo apt-get update
sudo apt-get install bluez bluez-tools
```

**Fedora:**
```bash
sudo dnf install bluez-deprecated
```

**Arch Linux:**
```bash
paru -S bluez-deprecated-tools
# or
yay -S bluez-deprecated-tools
```

### Python Requirements

The integration automatically installs these dependencies:

```
bleak>=0.21.0
bleak-retry-connector>=3.1.0
home-assistant-bluetooth>=1.10.0
```

For development or manual installation, you can install them with:

```bash
pip install -r requirements.txt
```

---

## Check Device Compatibility

### Quick Compatibility Check

Your device is likely compatible if:
- Device name starts with: `ELK-BLE`, `MELK`, `LEDBLE`, or `XROCKER`
- Controlled by apps: duoCo Strip, Lotus Lantern, Lotus Lamp X, or Happy Lighting
- Has Bluetooth Low Energy (BLE) connectivity

### Advanced Compatibility Check with gattool

If you want to verify compatibility manually, use `gattool`:

```bash
gatttool -I
```

Then connect to your device (replace `XX:XX:XX:XX:XX:XX` with your device's MAC address):

```bash
[LE]> connect XX:XX:XX:XX:XX:XX
Attempting to connect to XX:XX:XX:XX:XX:XX
Connection successful
[XX:XX:XX:XX:XX:XX][LE]> primary
attr handle: 0x0001, end grp handle: 0x0003 uuid: 00001800-0000-1000-8000-00805f9b34fb
attr handle: 0x0004, end grp handle: 0x0009 uuid: 0000fff0-0000-1000-8000-00805f9b34fb

[XX:XX:XX:XX:XX:XX][LE]> characteristics
handle: 0x0002, char properties: 0x12, char value handle: 0x0003, uuid: 00002a00-0000-1000-8000-00805f9b34fb
handle: 0x0005, char properties: 0x10, char value handle: 0x0006, uuid: 0000fff4-0000-1000-8000-00805f9b34fb
handle: 0x0008, char properties: 0x06, char value handle: 0x0009, uuid: 0000fff3-0000-1000-8000-00805f9b34fb
```

**Check the UUIDs:**

| UUID Pattern | Compatibility | Repository |
|--------------|---------------|------------|
| `0000fff3-...` or `0000ffe1-...` | **Compatible** | This repository |
| `0000ff01-...` | Use different integration | [lednetwf_ble](https://github.com/raulgbcr/lednetwf_ble) |
| `0000ffd5-...`, `0000ffd9-...`, etc. | Use different integration | [led_ble](https://www.home-assistant.io/integrations/led_ble/) |

### Using BTScan for Unsupported Devices

If your device isn't supported yet, you can help add support:

```bash
git clone https://github.com/dave-code-ruiz/elkbledom
cd elkbledom
pip install -r requirements.txt
python3 BTScan.py
```

This will scan for BLE devices and create a JSON file with technical information. Then:

1. [Create a new issue](https://github.com/dave-code-ruiz/elkbledom/issues/new) on GitHub
2. Attach the generated JSON file
3. Include device name, brand, and purchase link if available

For more advanced users, check out our [BLE Sniffing Guide](custom_components/elkbledom/sniffing_ble_device.md) to help reverse-engineer the protocol.

---


## Quick Start Guide

### Step 1: Enable Bluetooth

Ensure Bluetooth is enabled on your Home Assistant device:
1. Go to **Settings** → **System** → **Hardware**
2. Verify Bluetooth is detected
3. If not, check your hardware supports Bluetooth or add a USB Bluetooth adapter

### Step 2: Install Integration

Follow the [Installation](#-installation) instructions above.

### Step 3: Add Your Device

1. Go to **Settings** → **Devices & Services** → **Integrations**
2. Click **+ Add Integration**
3. Search for **"elkbledom"**
4. Select your device from the discovered list
5. Watch your light toggle to confirm connection
6. Click **Submit**

### Step 4: Control Your Lights

Your LED device is now available as a `light` entity in Home Assistant!

---

## Troubleshooting

### Common Issues

#### 1. Device Not Discovered

**Problem**: Your LED device doesn't appear in the discovered devices list.

**Solutions**:
- Ensure the device is powered on and within Bluetooth range (~10 meters)
- Disconnect the device from any mobile app
- Restart the Bluetooth service in Home Assistant
- Check if your device name starts with `ELK-BLE`, `MELK`, `LEDBLE`, or similar
- Manually scan for BLE devices using `bluetoothctl` or the BTScan.py script

#### 2. Connection Failed / Out of Slots Error

**Problem**: 
```
BleakOutOfConnectionSlotsError: Failed to connect after 9 attempt(s): 
No backend with an available connection slot that can reach address
```

**Solutions**:
- Only ONE device can connect to the LED strip at a time
- Close the mobile app completely (force stop on Android)
- Disconnect from `gatttool` if you used it for testing
- Wait 30 seconds and try again
- Power cycle the LED strip

#### 3. MELK Devices - Initialization Required

**Problem**: MELK devices don't respond to commands after setup.

**Solution**: MELK devices require initialization commands. Send these via `gatttool` (replace MAC address):

```bash
sudo gatttool -b XX:XX:XX:XX:XX:XX --char-write-req -a 0x0009 -n 7e0783
sudo gatttool -b XX:XX:XX:XX:XX:XX --char-write-req -a 0x0009 -n 7e0404
```

After sending these commands:
1. Restart the LED strip (power off/on)
2. Reload the integration in Home Assistant
3. The device should now work normally

See [Issue #11](https://github.com/dave-code-ruiz/elkbledom/issues/11) for more details.

#### 4. State Not Updating

**Problem**: Changes made via IR remote or mobile app don't reflect in Home Assistant.

**Explanation**: This is a known limitation. The integration doesn't support live state polling.

**Workaround**: 
- Control the lights exclusively through Home Assistant
- Use HA automations instead of physical remotes

#### 5. Interference with TV Remote or Other Devices

**Problem**: LED strip changes randomly when using TV remote or other IR devices.

**Explanation**: Some cheap LED controllers respond to generic IR signals.

**Solution**:
- Block the IR receiver on the LED controller (small piece of tape)
- Control exclusively via Bluetooth/Home Assistant
- Replace the controller with a better quality one

#### 6. Slow Response / Disconnects

**Problem**: Lights are slow to respond or frequently disconnect.

**Solutions**:
- Reduce the disconnect delay in configuration (try 60 seconds)
- Move the Home Assistant device closer to the LED strip
- Check for Bluetooth interference (WiFi routers, microwaves, etc.)
- Use a USB Bluetooth adapter with better range
- Set disconnect delay to `0` (never disconnect) for instant response
- **Use ESPHome Bluetooth Proxy**: Deploy [ESPHome Bluetooth proxy](https://esphome.io/components/bluetooth_proxy.html) devices (ESP32) closer to your LED strips for extended range and better reliability
  - ESP32 devices act as Bluetooth bridges
  - Significantly improves range and connection stability
  - Cost-effective solution (~$5-10 per ESP32 device)
  - Multiple proxies can cover larger areas

---

## Enable Debug Logging

If you're experiencing issues, enable debug logging to get more detailed information:

**Add to `configuration.yaml`:**

```yaml
logger:
  default: info
  logs:
    custom_components.elkbledom: debug
```

**Restart Home Assistant**, reproduce the issue, then check the logs:
- Go to **Settings** → **System** → **Logs**
- Look for entries with `custom_components.elkbledom`
- Include relevant log entries when [creating an issue](https://github.com/dave-code-ruiz/elkbledom/issues)

---

## Configuration

### Initial Setup

1. Go to **Settings** → **Devices & Services** → **Integrations**
2. Click **+ Add Integration**
3. Search for **"elkbledom"**
4. The integration will automatically discover nearby ELK-BLEDOM devices
5. Select your device from the list
6. The setup will validate the connection by toggling the light (make sure it's in range!)
7. Complete the setup

> **Note**: Repeat the setup process for each light you want to add.

### Configuration Options

After setup, you can configure additional options:

#### Available Settings

| Setting | Description | Default | Options |
|---------|-------------|---------|---------|
| **Reset color on turn on** | When the LED turns on, reset to white color | `false` | `true` / `false` |
| **Disconnect delay (seconds)** | Time before disconnecting from the device when idle | `120` | `0` = Never disconnect<br>`30-300` = Seconds |
| **Brightness mode** | How brightness is controlled | `auto` | `auto` = Automatic detection<br>`rgb` = RGB scaling<br>`native` = Device native |
| **Model** | Override auto-detected device model | Auto-detected | `ELK-BLEDOB`, `ELK-BLEDOM`, `MELK`, `LEDBLE`, `XROCKER`, etc. |
| **Effects class** | Change the effects list/behavior | Default | Varies by device model |

#### How to Change Settings

1. Go to **Settings** → **Devices & Services** → **Integrations**
2. Find your **elkbledom** device
3. Click **Configure**
4. Adjust the settings
5. Click **Submit**

#### Setting Recommendations

- **Reset color on turn on**: Enable if you want consistent behavior (always starts with white)
- **Disconnect delay**: 
  - Set to `0` for instant response but higher battery drain on battery-powered hubs
  - Set to `120-180` seconds for balance between responsiveness and efficiency
  - Set to `300+` seconds if you rarely control the lights
- **Brightness mode**:
  - Use `auto` for most devices (automatically detects the best method)
  - Use `rgb` if brightness control doesn't work properly
  - Use `native` for devices with dedicated brightness support
- **Model**:
  - Leave as auto-detected unless device is misidentified
  - Useful if you have a compatible device with a non-standard name
  - Change only if commands don't work with auto-detected model
- **Effects class**:
  - Leave as default for standard device behavior
  - Change if your device has different effect IDs than expected
  - Useful for devices with custom firmware or regional variants

---

## Features

<table>
<tr>
<td width="50%">

### Supported Features

**Automatic Discovery**
- Automatically finds ELK-BLEDOM devices
- No need to manually find MAC addresses

**Power Control**
- Turn lights on/off

**Color Control**
- Full RGB color support
- Color temperature (warm/cool white)
- White mode

**Brightness Control**
- Adjustable brightness (0-100%)
- Multiple brightness modes (RGB scaling, native)

**Effects**
- Built-in light effects
- Adjustable effect speed
- Effect selection
- **EFFECTS** - 22 standard effects (jump, crossfade, blink)
- **EFFECTS_MELK** - 16 MELK-specific effects
- **EFFECTS_MELK_Ox** - 13 MELK-Ox series effects
- **EFFECTS_DMRRBA** - 9 DMRRBA effects (flash, breath, candle)
- **EFFECTS_STRIPX** - 228 advanced effects (music-reactive, chase, fire, fade, pulse, elevator, rainbow)

**Multiple Devices**
- Control multiple lights independently
- Each device configured separately

**Music Reactive** (select models)
- Microphone-based effects
- Adjustable sensitivity

</td>
<td width="50%">

### Current Limitations

**Live State Polling**
- External control (IR remote, mobile app) changes are NOT reflected in Home Assistant
- State updates only work when controlled through HA

**Segments/Zones** (coming soon)
- Multi-zone RGB strips not yet supported
- Single zone control only

**Simultaneous Connections**
- Only one device (HA or mobile app) can connect at a time
- Disconnect from mobile app before using HA

</td>
</tr>
</table>

---

## Usage Examples

### Basic Control

#### Turn On/Off Button

```yaml
type: button
name: Turn On LED Strip
tap_action:
  action: toggle
entity: light.elk_bledom
show_icon: true
show_name: true
```

#### Set Specific Color

```yaml
type: button
name: Red
tap_action:
  action: call-service
  service: light.turn_on
  target:
    entity_id: light.elk_bledom
  data:
    rgb_color: [255, 0, 0]
    brightness: 255
show_icon: true
show_name: true
```

### Advanced Automations

#### Sunrise Simulation

```yaml
automation:
  - alias: "Wake Up Light"
    trigger:
      - platform: time
        at: "07:00:00"
    action:
      - service: light.turn_on
        target:
          entity_id: light.elk_bledom
        data:
          brightness: 1
          rgb_color: [255, 147, 41]  # Warm orange
      - delay: "00:00:01"
      - repeat:
          count: 30
          sequence:
            - service: light.turn_on
              target:
                entity_id: light.elk_bledom
              data:
                brightness: >
                  {{ (repeat.index * 8) | int }}
            - delay: "00:01:00"  # Fade over 30 minutes
```

#### Motion-Activated Night Light

```yaml
automation:
  - alias: "Bedroom Night Light"
    trigger:
      - platform: state
        entity_id: binary_sensor.bedroom_motion
        to: "on"
    condition:
      - condition: time
        after: "22:00:00"
        before: "06:00:00"
    action:
      - service: light.turn_on
        target:
          entity_id: light.elk_bledom
        data:
          brightness: 10
          rgb_color: [255, 100, 0]  # Dim warm light
      - delay: "00:05:00"
      - service: light.turn_off
        target:
          entity_id: light.elk_bledom
```

#### Scene Button Panel

```yaml
type: vertical-stack
cards:
  - type: horizontal-stack
    cards:
      - type: button
        name: Relax
        icon: mdi:weather-sunset
        tap_action:
          action: call-service
          service: light.turn_on
          target:
            entity_id: light.elk_bledom
          data:
            rgb_color: [255, 120, 0]
            brightness: 150
      - type: button
        name: Energize
        icon: mdi:white-balance-sunny
        tap_action:
          action: call-service
          service: light.turn_on
          target:
            entity_id: light.elk_bledom
          data:
            rgb_color: [0, 150, 255]
            brightness: 255
  - type: horizontal-stack
    cards:
      - type: button
        name: Focus
        icon: mdi:lightbulb-on
        tap_action:
          action: call-service
          service: light.turn_on
          target:
            entity_id: light.elk_bledom
          data:
            color_temp: 250  # Cool white
            brightness: 255
      - type: button
        name: Movie
        icon: mdi:movie-open
        tap_action:
          action: call-service
          service: light.turn_on
          target:
            entity_id: light.elk_bledom
          data:
            rgb_color: [100, 0, 150]
            brightness: 50
```

---

## Contributing

Contributions are welcome! Here's how you can help:

### Adding Support for New Devices

1. **Capture BLE traffic** using our [BLE Sniffing Guide](custom_components/elkbledom/sniffing_ble_device.md)
2. **Analyze the protocol** and identify command structures
3. **Add model to `models.json`** following existing patterns
4. **Test thoroughly** with your physical device
5. **Submit a Pull Request** with your changes

### Reporting Bugs

1. [Create a new issue](https://github.com/dave-code-ruiz/elkbledom/issues/new)
2. Include:
   - Device model and brand
   - Home Assistant version
   - Debug logs (see [Enable Debug Logging](#-enable-debug-logging))
   - Steps to reproduce

### Sharing Device Information

Help expand device support by running BTScan:

```bash
python3 BTScan.py
```

Share the generated JSON in a new issue!

---

## Known Issues

| Issue | Status | Workaround |
|-------|--------|------------|
| Live state polling not supported | Won't Fix | Control only via HA |
| Only one connection at a time | Limitation | Disconnect mobile app before using HA |
| TV remote interference | Won't Fix | Cover IR receiver on controller |
| MELK requires initialization | In Progress | See troubleshooting section |
| Segment control not available | Planned | Coming in future update |

For more details, check the [GitHub Issues](https://github.com/dave-code-ruiz/elkbledom/issues) page.

---

## Credits

This integration wouldn't be possible without the amazing work from these projects and contributors:

### Core Inspirations
- [Home Assistant LED BLE Integration](https://www.home-assistant.io/integrations/led_ble/) - Official HA BLE LED integration
- [ha-triones](https://github.com/sysofwan/ha-triones) - Triones LED controller integration
- [elkbledom-fastlink](https://github.com/Satimaro/elkbledom-fastlink) - Protocol analysis and device support

### Protocol Analysis
- [ELK-BLEDOM Controller](https://github.com/TheSylex/ELK-BLEDOM-bluetooth-led-strip-controller/) - TheSylex's controller project
- [bledom_controller](https://github.com/FreekBes/bledom_controller/) - Python-based controller
- [ELK-BLEDOM Analysis](https://github.com/FergusInLondon/ELK-BLEDOM/) - Reverse engineering work
- [BLE RGB LED Strip Controller](https://github.com/arduino12/ble_rgb_led_strip_controller) - Arduino implementation
- [DynamicLedStrips](https://github.com/lilgallon/DynamicLedStrips) - Dynamic effects implementation
- [JACKYLED Controller](https://github.com/kquinsland/JACKYLED-BLE-RGB-LED-Strip-controller) - Alternative controller analysis

### Documentation
- [Linux Things Blog](https://linuxthings.co.uk/blog/control-an-elk-bledom-bluetooth-led-strip) - Control guide and protocol details

### Special Thanks

- All contributors who have submitted device information, bug reports, and pull requests
- The Home Assistant community for continued support and feedback
- Everyone who has helped reverse-engineer protocols for new device models

---

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

## Support

If you find this integration useful, consider supporting the development:

<a href="https://www.buymeacoffee.com/davecoderuiz" target="_blank">
  <img src="https://cdn.buymeacoffee.com/buttons/v2/default-yellow.png" alt="Buy Me A Coffee" height="60">
</a>

---

<div align="center">

**Made for the Home Assistant Community**

[Report Bug](https://github.com/dave-code-ruiz/elkbledom/issues) • [Request Feature](https://github.com/dave-code-ruiz/elkbledom/issues) • [Contribute](https://github.com/dave-code-ruiz/elkbledom/pulls)

</div>
