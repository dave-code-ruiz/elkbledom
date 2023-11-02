# elkbledom HA Integration

<a href="https://www.buymeacoffee.com/davecoderuiz" target="_blank"><img src="https://cdn.buymeacoffee.com/buttons/default-orange.png" alt="Buy Me A Coffee" height="41" width="174"></a>

[![hacs_badge](https://img.shields.io/badge/HACS-Default-41BDF5.svg)](https://github.com/hacs/integration)
[![hacs_badge](https://img.shields.io/badge/HACS-Custom-41BDF5.svg)](https://github.com/hacs/integration)

Home Assistant integration for LED STRIP or LED Desktop light (lightbar) NAME ELK BLEDOM with android/iphone mobile app duoCo Strip (https://play.google.com/store/apps/details?id=shy.smartled&hl=es&gl=US) or mobile app Lantern Lotus (https://play.google.com/store/apps/details?id=wl.smartled&hl=es&gl=US).

I buy it in amazon spain (https://www.amazon.es/gp/product/B00VFME0Q2)

Or lightbar like this (https://www.amazon.es/bedee-Regulable-Inteligente-Bluetooth-Dormitorio/dp/B0BNPMGR1H)

New support for MELK strip, you can buy it in amazon spain (https://www.amazon.es/distancia-Bluetooth-aplicaci%C3%B3n-sincronizaci%C3%B3n-habitaci%C3%B3n/dp/B09VC77GCZ) or search "B09VC77GCZ" in your amazon country shop.  MELK device confirmed working: https://www.amazon.com/dp/B07R7NTX6D 

## Supported strips

You can scan BT device with BTScan.py in my repository exec: ``` sudo python3 BTScan.py ```, code supports led strips whose name begins with "ELK-BLE" or "MELK" or "ELK-BULB".

Code supports controlling lights in HA with write uuid: 0000fff3-0000-1000-8000-00805f9b34fb or 0000ffe1-0000-1000-8000-00805f9b34fb

You can know your uuid with gatttool:

```

gatttool -I

[be:59:7a:00:08:xx][LE]> connect be:59:7a:00:08:xx

Attempting to connect to be:59:7a:00:08:xx

Connection successful

[be:59:7a:00:08:xx][LE]> primary
attr handle: 0x0001, end grp handle: 0x0003 uuid: 00001800-0000-1000-8000-00805f9b34fb
attr handle: 0x0004, end grp handle: 0x0009 uuid: 0000fff0-0000-1000-8000-00805f9b34fb

[be:59:7a:00:08:xx][LE]> Characteristics
handle: 0x0002, char properties: 0x12, char value handle: 0x0003, uuid: 00002a00-0000-1000-8000-00805f9b34fb
handle: 0x0005, char properties: 0x10, char value handle: 0x0006, uuid: 0000fff4-0000-1000-8000-00805f9b34fb
handle: 0x0008, char properties: 0x06, char value handle: 0x0009, uuid: 0000fff3-0000-1000-8000-00805f9b34fb

```

If your strip show some uuid like "0000fff3-0000-1000-8000-00805f9b34fb" , your strip it is supported

If your strip show some uuid like "0000ffe1-0000-1000-8000-00805f9b34fb" , your strip it is supported

If your strip show some uuid like "0000ff01-0000-1000-8000-00805f9b34fb", go to your correct repository: https://github.com/raulgbcr/lednetwf_ble

If your strip show some uuid like:

    "0000xxxx-0000-1000-8000-00805f9b34fb"
    xxxx can be one of these values ("ff01", "ffd5", "ffd9", "ffe5", "ffe9", "ff02", "ffd0", "ffd4", "ffe0", "ffe4")
     
Go to your correct repository: https://www.home-assistant.io/integrations/led_ble/

If your uuid is none of the above, create issue with: 1- strip name 2- your results uuid 3- handle information

You can use gatttool to try discover your turn on/off command with:

```
sudo gatttool -i hci0 -b be:59:7a:00:08:xx --char-write-req -a 0x0009 -n 7e00040100000000ef # POWERON
sudo gatttool -i hci0 -b be:59:7a:00:08:xx --char-write-req -a 0x0009 -n 7e0004000000ff00ef # POWEROFF
```
or
```
sudo gatttool -b be:59:7a:00:08:xx --char-write-req -a 0x0009 -n 7e0004f00001ff00ef # POWER ON
sudo gatttool -b be:59:7a:00:08:xx --char-write-req -a 0x0009 -n 7e000503ff000000ef # RED
sudo gatttool -b be:59:7a:00:08:xx --char-write-req -a 0x0009 -n 7e0005030000ff00ef # BLUE
sudo gatttool -b be:59:7a:00:08:xx --char-write-req -a 0x0009 -n 7e00050300ff0000ef # GREEN
sudo gatttool -b be:59:7a:00:08:xx --char-write-req -a 0x0009 -n 7e0004000000ff00ef # POWER OFF
```

## Installation

### [HACS](https://hacs.xyz/) (recommended)

Installation can be done through HACS , search "elkbledom" and download it

### Manual installation

You can manually clone this repository inside `config/custom_components/` HA folder.

## Setup

After installation, you should find elkbledom under the Settings -> Integrations -> Add integration -> search elkbledom integration -> follow instructions.

The setup step includes discovery which will list out all ELK BLEDOM lights discovered. The setup will validate connection by toggling the selected light. Make sure your light is in-sight to validate this.

The setup needs to be repeated for each light.

## Config

After Setup, you can config two elkbledom params under Settings -> Integrations -> search elkbledom integration -> Config.

Reset color when led turn on: When led strip turn on, led reset to color white or not. This is needed if you want because i don´t know led strip state and is needed a reset.

Disconnect delay or timeout: You can configure time led strip disconnected from HA (0 equal never disconnect).

## Features
Discovery: Automatically discover ELK BLEDOM based lights without manually hunting for Bluetooth MAC address

On/Off/RGB/Brightness support

Emulated RGB brightness: Supports adjusting brightness of RGB lights

Multiple light support

## Not supported

Live state polling: External control (i.e. IR remote) state changes NO reflect in Home Assistant and NO updated.

[Light modes] (blinking, fading, etc) is not yet supported.

## enable debug mode

Use debug log to see more information of posible errors and post it in your issue description

In configuration.yaml:

```
logger:
  default: info
  logs:
    custom_components.elkbledom: debug
```

## Examples

Create button to turn on:
```
show_name: true
show_icon: true
name: turn on
type: button
tap_action:
  action: toggle
entity: light.tiraled
```

Create button to set color:
```
show_name: true
show_icon: true
name: Red
type: button
tap_action:
  action: call-service
  service: light.turn_on
  target:
    entity_id: light.test
  data:
    rgb_color:
      - 255
      - 0
      - 0
    brightness: 255
```
## Known issues

1. Live state polling dont work.

3. I am waiting for read status value:

            ```
            
            future = asyncio.get_event_loop().create_future()
            await self._device.start_notify(self._read_uuid, create_status_callback(future))
            # PROBLEMS WITH STATUS VALUE, I HAVE NOT VALUE TO WRITE AND GET STATUS
            await self._write(bytearray([0xEF, 0x01, 0x77]))
            await asyncio.wait_for(future, 5.0)
            await self._device.stop_notify(self._read_uuid)
            
            ```

## Credits
This integration will not be possible without the awesome work of this github repositories:

https://www.home-assistant.io/integrations/led_ble/

https://github.com/sysofwan/ha-triones

https://github.com/TheSylex/ELK-BLEDOM-bluetooth-led-strip-controller/

https://github.com/FreekBes/bledom_controller/

https://github.com/FergusInLondon/ELK-BLEDOM/

https://github.com/arduino12/ble_rgb_led_strip_controller

https://github.com/lilgallon/DynamicLedStrips

https://github.com/kquinsland/JACKYLED-BLE-RGB-LED-Strip-controller

https://linuxthings.co.uk/blog/control-an-elk-bledom-bluetooth-led-strip
