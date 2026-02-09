# LED BLE Discovery Tools

## Purpose

These tools help you discover the command protocol of **any BLE LED strip** when BTScan.py doesn't detect working commands correctly.

Use when:
- ✅ LED strip connects properly
- ✅ Characteristic UUIDs seem correct
- ❌ But **no test commands work**
- ❌ Or LED reacts but **not with expected behavior**

## Available Tools

### 1. `BTScan.py` - Main Discovery Tool (RECOMMENDED)

Complete discovery script that:
- Scans for BLE devices
- Discovers characteristics (now **includes handles**)
- Tests known commands systematically
- Generates complete JSON report

**Recent improvement:** Now **loads all commands from models.json** and shows the **handle** of each characteristic in the report.

**How to use:**

```bash
python3 BTScan.py
```

**Steps:**
1. Run the script
2. Select your LED strip from the list
3. Script will test all commands from models.json
4. Interactive prompts to confirm what works
5. Generates a JSON report with results

**Output:**
- File `led_discovery_ADDRESS_TIMESTAMP.json` with complete results
- **Includes handle information** to identify specific models

---

### 2. `ble_sniffer.py` - BLE Traffic Capture (Passive Method)

Captures BLE notifications while you use the official LED control app.

**How to use:**

```bash
python3 ble_sniffer.py
```

**Steps:**
1. Run the script on your PC/Linux
2. Script connects to your LED strip
3. Open the control app on your phone (Lotus Lantern, Happy Lighting, Magic Home, etc.)
4. Try different actions in the app:
   - Turn ON/OFF
   - Change colors (Red, Green, Blue, etc.)
   - Change brightness
   - Try different modes/effects
5. Script logs all notifications received
6. Press Ctrl+C when done

**Output:**
- File `ble_capture_YYYYMMDD_HHMMSS.txt` with all captured notifications
- **Includes handle of each characteristic** for model identification

⚠️ **NOTE:** This method only works if the device sends notifications. If nothing is captured, that's normal for many LED strips.

---

## What to do with results?

### If you used `BTScan.py`:
Check the generated JSON file:
- ✅ Verify UUIDs
- ✅ **Note the handle** of write characteristic
- ✅ Check which commands worked in `working_commands` section

### If you used `ble_sniffer.py`:
Send the `ble_capture_*.txt` file. It includes:
- **Handles** of each characteristic
- Complete UUIDs
- Captured notifications

This information can:
1. Identify the exact device protocol
2. Update HA integration to support it
3. Create a specific profile in models.json (with correct handle if needed)

---

## Common Command Formats

If you want to test commands manually:

### Turn ON (common formats):
```
7e 07 04 ff ff ff 00 ff ef  (Format 1)
7e 04 04 f0 00 01 ff 00 ef  (Format 2)
aa 0f 00                     (Short format)
```

### Turn OFF (common formats):
```
7e 07 04 00 00 00 00 ff ef  (Format 1)
7e 04 04 00 00 00 ff 00 ef  (Format 2)
aa 0e 00                     (Short format)
```

### Colors (format 1 examples):
```
# Red:    7e 07 05 03 ff 00 00 10 ef
# Green:  7e 07 05 03 00 ff 00 10 ef
# Blue:   7e 07 05 03 00 00 ff 10 ef
```

### General color format:
```
7e 07 05 03 RR GG BB 10 ef  (Format 1)
7e 00 05 03 RR GG BB 00 ef  (Format 2)
```
Where RR, GG, BB are hex values 00-FF for Red, Green, Blue.

---

## Requirements

Make sure you have:

```bash
pip install bleak
```

---

## Recommended Next Step

**Run `BTScan.py` first**, as it's the most comprehensive tool. It automatically loads all known commands from models.json and tests them systematically.

If you need to capture actual app traffic (for devices with unknown protocols), use `ble_sniffer.py`.

---

## Importance of Handle

In [models.json](custom_components/elkbledom/models.json) some models specify a `handle`:

```json
{
  "name": "ELK-BLEDOM",
  "write_uuid": "0000fff3-0000-1000-8000-00805f9b34fb",
  "read_uuid": "0000fff4-0000-1000-8000-00805f9b34fb",
  "handle": 13,
  ...
}
```

The **handle** is important because:
- Two devices with same name may have different handles
- Handle identifies the specific characteristic within BLE service
- Some devices require writing to a specific handle to work

Scripts now **show the handle** in all reports to help identify model variants.

---

## Common Analysis Cases

### Case 1: Correct UUIDs but no commands work
- ✅ UUIDs match (fff3 for write, fff4 for notify)
- ❌ **No standard commands worked**
- ⚠ LED **reacts but incorrectly**

**Cause:** Device uses protocol variant with:
- Different header/footer bytes
- Different checksum calculation
- Different parameter order
- **Possible different handle**

**Solution:** Use `BTScan.py` and/or `ble_sniffer.py`

### Case 2: Same name, different commands
Some manufacturers use same name (e.g., "ELK-BLEDOM") for different models:
- May have different handles
- Different command formats
- Different capabilities (some support color temperature, others don't)

**Solution:** Identify specific handle and create separate entry in models.json

---

## Adding New Model to models.json

Once protocol is identified:

```json
{
  "name": "YOUR-DEVICE",
  "write_uuid": "0000fff3-0000-1000-8000-00805f9b34fb",
  "read_uuid": "0000fff4-0000-1000-8000-00805f9b34fb",
  "handle": 13,  // ← IMPORTANT: Add if different from standard
  "effects_class": "EFFECTS",
  "effects_list": "EFFECTS_list",
  "commands": {
    "turn_on": [126, 7, 4, 255, 0, 1, 2, 1, 239],
    "turn_off": [126, 7, 4, 0, 0, 0, 2, 0, 239],
    "color": [126, 7, 5, 3, "r", "g", "b", 10, 239]
  }
}
```

BTScan.py will automatically load and test these commands on next run.

---

**Version:** 2.0 (with models.json integration and handle support)
**Updated:** 2026-02-09
