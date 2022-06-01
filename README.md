# elkbledom-ha

<a href="https://www.buymeacoffee.com/davecoderuiz" target="_blank"><img src="https://cdn.buymeacoffee.com/buttons/default-orange.png" alt="Buy Me A Coffee" height="41" width="174"></a>

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://github.com/custom-components/hacs)

Home Assistant integration for LED STRIP NAME ELK BLEDOM with android/iphone mobile app duoCo Strip (https://play.google.com/store/apps/details?id=shy.smartled&hl=es&gl=US)

## Supported strips

Code supports controlling ELK-BLEDOM based lights in HA with write uuid: 0000fff3-0000-1000-8000-00805f9b34fb

You can know your uuid with gatttool:

```

gatttool -I

connect FF:FF:FF:FF:FF:XX

primary

```

If your strip show some uuid like "0000fff3-0000-1000-8000-00805f9b34fb" , your strip it is supported

If your strip show some uuid like:

            "0000ffd5-0000-1000-8000-00805f9b34fb"
            "0000ffd9-0000-1000-8000-00805f9b34fb"
            "0000ffe5-0000-1000-8000-00805f9b34fb"
            "0000ffe9-0000-1000-8000-00805f9b34fb"
            
Go to your correct repository: https://github.com/sysofwan/ha-triones

If your uuid is none of the above, create issue with your results uuid and handle information

## Installation

### [HACS](https://hacs.xyz/) (recommended)

Installation can be done through [HACS custom repository](https://hacs.xyz/docs/faq/custom_repositories).

### Manual installation

You can manually clone this repository inside `config/custom_components/` HA folder.

## Setup

After installation, you should find elkbledom under the Configuration -> Integrations -> Add integration.

The setup step includes discovery which will list out all ELK BLEDOM lights discovered. The setup will validate connection by toggling the selected light. Make sure your light is in-sight to validate this.

The setup needs to be repeated for each light.

## Features
Discovery: Automatically discover ELK BLEDOM based lights without manually hunting for Bluetooth MAC address

On/Off/RGB/Brightness support

Emulated RGB brightness: Supports adjusting brightness of RGB lights

Multiple light support

## Not supported

Live state polling: External control (i.e. IR remote) state changes NO reflect in Home Assistant and NO updated.

[Light modes] (blinking, fading, etc) is not yet supported.

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

https://github.com/sysofwan/ha-triones

https://github.com/TheSylex/ELK-BLEDOM-bluetooth-led-strip-controller/

https://github.com/FreekBes/bledom_controller/

https://github.com/FergusInLondon/ELK-BLEDOM/

https://github.com/arduino12/ble_rgb_led_strip_controller

https://github.com/lilgallon/DynamicLedStrips

https://github.com/kquinsland/JACKYLED-BLE-RGB-LED-Strip-controller

https://linuxthings.co.uk/blog/control-an-elk-bledom-bluetooth-led-strip
