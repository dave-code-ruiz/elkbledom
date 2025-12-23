#!/usr/bin/env python3
"""
Herramienta de descubrimiento y prueba de tiras LED BLE
Ayuda a encontrar comandos para nuevas tiras LED que luego se añaden a elkbledom.py
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

# 30+ NUEVOS COMANDOS basados en protocolos BLE LED comunes encontrados en foros y documentación
NEW_TURN_ON_COMMANDS = [
    # Variantes del protocolo 0x7e con diferentes prefijos
    [0x7e, 0x01, 0x04, 0xf0, 0x00, 0x01, 0xff, 0x00, 0xef],
    [0x7e, 0x02, 0x04, 0xf0, 0x00, 0x01, 0xff, 0x00, 0xef],
    [0x7e, 0x03, 0x04, 0xf0, 0x00, 0x01, 0xff, 0x00, 0xef],
    [0x7e, 0x05, 0x04, 0xf0, 0x00, 0x01, 0xff, 0x00, 0xef],
    [0x7e, 0x06, 0x04, 0xf0, 0x00, 0x01, 0xff, 0x00, 0xef],
    [0x7e, 0x08, 0x04, 0xf0, 0x00, 0x01, 0xff, 0x00, 0xef],
    
    # Protocolo corto (algunas tiras usan comandos más cortos)
    [0xcc, 0x23, 0x33],
    [0xcc, 0x24, 0x33],
    [0x7e, 0x04, 0x01, 0xef],
    [0x7e, 0x00, 0x01, 0xef],
    
    # Protocolo alternativo 0xaa (usado en algunos controladores Magic Home)
    [0xaa, 0x01, 0x01, 0x00, 0x00, 0x00, 0x00, 0x00, 0x55],
    [0xaa, 0x01, 0xff, 0x00, 0x00, 0x00, 0x00, 0x00, 0x55],
    
    # Variantes con byte de control diferente
    [0x7e, 0x00, 0x04, 0xff, 0x01, 0x01, 0xff, 0x00, 0xef],
    [0x7e, 0x00, 0x04, 0x01, 0x01, 0x01, 0x01, 0x00, 0xef],
    [0x7e, 0x00, 0x04, 0xaa, 0x00, 0x01, 0xff, 0x00, 0xef],
    
    # Comandos encontrados en controladoras Triones/Happy Lighting
    [0x7e, 0x07, 0x04, 0x01, 0xff, 0x01, 0x02, 0x01, 0xef],
    [0x7e, 0x00, 0x04, 0xf1, 0x00, 0x01, 0xff, 0x00, 0xef],
    
    # Protocolo simple binario
    [0x01, 0xff, 0x00],
    [0xff, 0x01],
    [0x01],
    
    # Comandos tipo Zengge/Magic Light
    [0x71, 0x23, 0x0f],
    [0x71, 0x24, 0x0f],
    
    # Variantes con checksum diferente
    [0x7e, 0x00, 0x04, 0xf0, 0x00, 0x01, 0xff, 0x00, 0xff],
    [0x7e, 0x00, 0x04, 0xf0, 0x00, 0x01, 0xff, 0x00, 0xfe],
    [0x7e, 0x00, 0x04, 0xf0, 0x00, 0x01, 0xff, 0x00, 0xee],
    
    # Comandos encontrados en Banggood LED strips
    [0x7e, 0x00, 0x03, 0xff, 0x00, 0x00, 0x00, 0x00, 0xef],
    [0x7e, 0x04, 0x03, 0xff, 0x00, 0x01, 0xff, 0x00, 0xef],
    
    # Otros protocolos alternativos
    [0xef, 0x01, 0x77],
    [0xbb, 0x01, 0x00, 0x01],
    [0x55, 0xaa, 0x01],
]

NEW_TURN_OFF_COMMANDS = [
    # Variantes del protocolo 0x7e con diferentes prefijos
    [0x7e, 0x01, 0x04, 0x00, 0x00, 0x00, 0xff, 0x00, 0xef],
    [0x7e, 0x02, 0x04, 0x00, 0x00, 0x00, 0xff, 0x00, 0xef],
    [0x7e, 0x03, 0x04, 0x00, 0x00, 0x00, 0xff, 0x00, 0xef],
    [0x7e, 0x05, 0x04, 0x00, 0x00, 0x00, 0xff, 0x00, 0xef],
    [0x7e, 0x06, 0x04, 0x00, 0x00, 0x00, 0xff, 0x00, 0xef],
    [0x7e, 0x08, 0x04, 0x00, 0x00, 0x00, 0xff, 0x00, 0xef],
    
    # Protocolo corto
    [0xcc, 0x24, 0x33],
    [0xcc, 0x23, 0x34],
    [0x7e, 0x04, 0x00, 0xef],
    [0x7e, 0x00, 0x00, 0xef],
    
    # Protocolo alternativo 0xaa
    [0xaa, 0x01, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x55],
    [0xaa, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x55],
    
    # Variantes con byte de control diferente
    [0x7e, 0x00, 0x04, 0x00, 0x01, 0x00, 0xff, 0x00, 0xef],
    [0x7e, 0x00, 0x04, 0x00, 0x00, 0x00, 0x00, 0x00, 0xef],
    [0x7e, 0x00, 0x04, 0xaa, 0x00, 0x00, 0xff, 0x00, 0xef],
    
    # Comandos Triones/Happy Lighting
    [0x7e, 0x07, 0x04, 0x00, 0x00, 0x00, 0x02, 0x00, 0xef],
    [0x7e, 0x00, 0x04, 0xf1, 0x00, 0x00, 0xff, 0x00, 0xef],
    
    # Protocolo simple binario
    [0x00, 0x00, 0x00],
    [0xff, 0x00],
    [0x00],
    
    # Comandos tipo Zengge/Magic Light
    [0x71, 0x24, 0x0f],
    [0x71, 0x23, 0x0e],
    
    # Variantes con checksum diferente
    [0x7e, 0x00, 0x04, 0x00, 0x00, 0x00, 0xff, 0x00, 0xff],
    [0x7e, 0x00, 0x04, 0x00, 0x00, 0x00, 0xff, 0x00, 0xfe],
    [0x7e, 0x00, 0x04, 0x00, 0x00, 0x00, 0xff, 0x00, 0xee],
    
    # Comandos Banggood
    [0x7e, 0x00, 0x03, 0x00, 0x00, 0x00, 0x00, 0x00, 0xef],
    [0x7e, 0x04, 0x03, 0x00, 0x00, 0x00, 0xff, 0x00, 0xef],
    
    # Otros protocolos alternativos
    [0xef, 0x00, 0x77],
    [0xbb, 0x00, 0x00, 0x00],
    [0x55, 0xaa, 0x00],
]

# Comandos para establecer color RGB
NEW_COLOR_COMMANDS = [
    # Formato: función que toma (r, g, b) y retorna comando
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

# Comandos para blanco
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

# Comandos para temperatura de color
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
        self.discovered_devices: List[BLEDevice] = []
        self.test_results = {
            'device_info': {},
            'characteristics': {},
            'working_commands': {
                'turn_on': [],
                'turn_off': [],
                'color': [],
                'white': [],
                'color_temp': []
            },
            'custom_commands': []
        }
        
    async def scan_devices(self, duration: int = 10) -> List[BLEDevice]:
        """Escanea dispositivos BLE cercanos"""
        print(f"\n{'='*60}")
        print(f"🔍 Escaneando dispositivos Bluetooth LE durante {duration} segundos...")
        print(f"{'='*60}\n")
        
        devices = await BleakScanner.discover(timeout=duration)
        self.discovered_devices = [d for d in devices if d.name]  # Solo dispositivos con nombre
        
        return self.discovered_devices
    
    def display_devices(self):
        """Muestra los dispositivos descubiertos"""
        if not self.discovered_devices:
            print("❌ No se encontraron dispositivos BLE")
            return
        
        print(f"\n{'='*60}")
        print("📱 Dispositivos BLE encontrados:")
        print(f"{'='*60}\n")
        
        for idx, device in enumerate(self.discovered_devices, 1):
            print(f"{idx}. 📍 Dirección: {device.address}")
            print(f"   📝 Nombre: {device.name or 'Sin nombre'}")
            print(f"   📡 RSSI: {device.rssi} dBm")
            print(f"   {'-'*56}")
    
    async def select_device(self) -> Optional[BLEDevice]:
        """Permite al usuario seleccionar un dispositivo"""
        self.display_devices()
        
        if not self.discovered_devices:
            return None
        
        while True:
            try:
                choice = input(f"\n🎯 Selecciona un dispositivo (1-{len(self.discovered_devices)}) o 'q' para salir: ").strip()
                
                if choice.lower() == 'q':
                    return None
                
                idx = int(choice) - 1
                if 0 <= idx < len(self.discovered_devices):
                    device = self.discovered_devices[idx]
                    print(f"\n✅ Dispositivo seleccionado: {device.name} ({device.address})")
                    
                    self.test_results['device_info'] = {
                        'name': device.name,
                        'address': device.address,
                        'rssi': device.rssi
                    }
                    
                    return device
                else:
                    print("❌ Número inválido, intenta de nuevo")
            except ValueError:
                print("❌ Entrada inválida, introduce un número")
    
    async def discover_characteristics(self, device: BLEDevice) -> Dict:
        """Descubre las características BLE del dispositivo"""
        print(f"\n{'='*60}")
        print(f"🔎 Analizando características del dispositivo...")
        print(f"{'='*60}\n")
        
        characteristics = {
            'write': [],
            'read': [],
            'notify': [],
            'all': []
        }
        
        try:
            async with BleakClient(device.address, timeout=20.0) as client:
                print(f"✅ Conectado a {device.name}\n")
                
                for service in client.services:
                    print(f"📦 Servicio: {service.uuid}")
                    
                    for char in service.characteristics:
                        char_info = {
                            'uuid': char.uuid,
                            'properties': char.properties,
                            'service': service.uuid
                        }
                        characteristics['all'].append(char_info)
                        
                        print(f"   └─ Característica: {char.uuid}")
                        print(f"      Propiedades: {', '.join(char.properties)}")
                        
                        if 'write' in char.properties or 'write-without-response' in char.properties:
                            characteristics['write'].append(char_info)
                            print(f"      ✍️  ESCRITURA disponible")
                        
                        if 'read' in char.properties:
                            characteristics['read'].append(char_info)
                            print(f"      📖 LECTURA disponible")
                        
                        if 'notify' in char.properties:
                            characteristics['notify'].append(char_info)
                            print(f"      🔔 NOTIFICACIÓN disponible")
                        
                        print()
                
                self.test_results['characteristics'] = characteristics
                
        except Exception as e:
            print(f"❌ Error al conectar: {e}")
            return characteristics
        
        return characteristics
    
    async def select_write_characteristic(self, characteristics: Dict) -> Optional[str]:
        """Selecciona la característica de escritura"""
        print(f"\n{'='*60}")
        print("✍️  Selección de característica de ESCRITURA")
        print(f"{'='*60}\n")
        
        # Verificar si hay características conocidas
        write_chars = characteristics.get('write', [])
        
        if not write_chars:
            print("❌ No se encontraron características de escritura")
            return None
        
        # Buscar características conocidas
        known_found = []
        for char in write_chars:
            if char['uuid'] in KNOWN_WRITE_UUIDS:
                known_found.append(char)
        
        if known_found:
            print(f"✅ Se encontraron {len(known_found)} características conocidas:\n")
            for char in known_found:
                print(f"   • {char['uuid']}")
            
            if len(known_found) == 1:
                selected = known_found[0]['uuid']
                print(f"\n✅ Usando característica conocida: {selected}")
                return selected
        
        # Si no hay conocidas o hay múltiples, mostrar todas
        print(f"\n📋 Características de escritura disponibles:\n")
        for idx, char in enumerate(write_chars, 1):
            known = "⭐ CONOCIDA" if char['uuid'] in KNOWN_WRITE_UUIDS else ""
            print(f"{idx}. {char['uuid']} {known}")
        
        while True:
            try:
                choice = input(f"\n🎯 Selecciona característica (1-{len(write_chars)}): ").strip()
                idx = int(choice) - 1
                
                if 0 <= idx < len(write_chars):
                    selected = write_chars[idx]['uuid']
                    print(f"\n✅ Característica seleccionada: {selected}")
                    return selected
                else:
                    print("❌ Número inválido")
            except ValueError:
                print("❌ Entrada inválida")
    
    async def test_command(self, client: BleakClient, char_uuid: str, command: List[int], 
                          description: str, ask_user: bool = True) -> bool:
        """Prueba un comando en el dispositivo"""
        try:
            cmd_bytes = bytes(command)
            cmd_hex = ' '.join(f'{b:02x}' for b in cmd_bytes)
            
            print(f"\n📤 Probando: {description}")
            print(f"   Comando: {cmd_hex}")
            
            await client.write_gatt_char(char_uuid, cmd_bytes, response=False)
            
            if ask_user:
                while True:
                    response = input("   ❓ ¿Funcionó el comando? (s/n/r para relanzar): ").strip().lower()
                    
                    if response == 's':
                        print("   ✅ Comando funcional registrado")
                        return True
                    elif response == 'n':
                        print("   ❌ Comando no funcional")
                        return False
                    elif response == 'r':
                        print("   🔄 Relanzando comando...")
                        await client.write_gatt_char(char_uuid, cmd_bytes, response=False)
                    else:
                        print("   ⚠️  Respuesta inválida (s/n/r)")
            else:
                await asyncio.sleep(0.5)
                return False
                
        except Exception as e:
            print(f"   ❌ Error: {e}")
            return False
    
    async def test_power_commands(self, device: BLEDevice, char_uuid: str):
        """Prueba comandos de encendido/apagado"""
        print(f"\n{'='*60}")
        print("🔌 PROBANDO COMANDOS DE ENCENDIDO/APAGADO")
        print(f"{'='*60}\n")
        
        try:
            async with BleakClient(device.address, timeout=20.0) as client:
                print(f"✅ Conectado a {device.name}\n")
                
                # Probar comandos conocidos de encendido
                print("🟢 COMANDOS DE ENCENDIDO CONOCIDOS:")
                print("-" * 60)
                for idx, cmd in enumerate(KNOWN_TURN_ON, 1):
                    if await self.test_command(client, char_uuid, cmd, 
                                              f"Encender #{idx} (conocido)"):
                        self.test_results['working_commands']['turn_on'].append({
                            'command': cmd,
                            'description': f'Known turn on #{idx}',
                            'type': 'known'
                        })
                
                # Probar nuevos comandos de encendido
                print(f"\n🆕 NUEVOS COMANDOS DE ENCENDIDO ({len(NEW_TURN_ON_COMMANDS)} comandos):")
                print("-" * 60)
                for idx, cmd in enumerate(NEW_TURN_ON_COMMANDS, 1):
                    if await self.test_command(client, char_uuid, cmd, 
                                              f"Encender #{idx} (nuevo)"):
                        self.test_results['working_commands']['turn_on'].append({
                            'command': cmd,
                            'description': f'New turn on #{idx}',
                            'type': 'new'
                        })
                
                # Probar comandos conocidos de apagado
                print(f"\n🔴 COMANDOS DE APAGADO CONOCIDOS:")
                print("-" * 60)
                for idx, cmd in enumerate(KNOWN_TURN_OFF, 1):
                    if await self.test_command(client, char_uuid, cmd, 
                                              f"Apagar #{idx} (conocido)"):
                        self.test_results['working_commands']['turn_off'].append({
                            'command': cmd,
                            'description': f'Known turn off #{idx}',
                            'type': 'known'
                        })
                
                # Probar nuevos comandos de apagado
                print(f"\n🆕 NUEVOS COMANDOS DE APAGADO ({len(NEW_TURN_OFF_COMMANDS)} comandos):")
                print("-" * 60)
                for idx, cmd in enumerate(NEW_TURN_OFF_COMMANDS, 1):
                    if await self.test_command(client, char_uuid, cmd, 
                                              f"Apagar #{idx} (nuevo)"):
                        self.test_results['working_commands']['turn_off'].append({
                            'command': cmd,
                            'description': f'New turn off #{idx}',
                            'type': 'new'
                        })
                        
        except Exception as e:
            print(f"\n❌ Error durante las pruebas: {e}")
    
    async def test_color_commands(self, device: BLEDevice, char_uuid: str):
        """Prueba comandos de color RGB"""
        print(f"\n{'='*60}")
        print("🎨 PROBANDO COMANDOS DE COLOR RGB")
        print(f"{'='*60}\n")
        
        # Colores de prueba
        test_colors = [
            (255, 0, 0, "Rojo"),
            (0, 255, 0, "Verde"),
            (0, 0, 255, "Azul"),
        ]
        
        try:
            async with BleakClient(device.address, timeout=20.0) as client:
                print(f"✅ Conectado a {device.name}\n")
                
                for idx, cmd_func in enumerate(NEW_COLOR_COMMANDS, 1):
                    print(f"\n🎨 Probando comando de color #{idx}:")
                    worked = False
                    
                    for r, g, b, color_name in test_colors:
                        cmd = cmd_func(r, g, b)
                        if await self.test_command(client, char_uuid, cmd, 
                                                  f"Color {color_name} (R:{r}, G:{g}, B:{b})"):
                            worked = True
                            break
                    
                    if worked:
                        self.test_results['working_commands']['color'].append({
                            'command_template': 'lambda r, g, b: ' + str([hex(x) if isinstance(x, int) else 'r' if x == test_colors[0][0] else 'g' if x == test_colors[0][1] else 'b' for x in cmd_func(0, 0, 0)]),
                            'description': f'Color command #{idx}',
                            'test_values': test_colors
                        })
                        
        except Exception as e:
            print(f"\n❌ Error durante las pruebas: {e}")
    
    async def test_white_commands(self, device: BLEDevice, char_uuid: str):
        """Prueba comandos de luz blanca"""
        print(f"\n{'='*60}")
        print("⚪ PROBANDO COMANDOS DE LUZ BLANCA")
        print(f"{'='*60}\n")
        
        try:
            async with BleakClient(device.address, timeout=20.0) as client:
                print(f"✅ Conectado a {device.name}\n")
                
                # Probar comandos conocidos
                print("⚪ COMANDOS DE BLANCO CONOCIDOS:")
                print("-" * 60)
                for idx, cmd in enumerate(KNOWN_WHITE, 1):
                    if await self.test_command(client, char_uuid, cmd, 
                                              f"Blanco #{idx} (conocido)"):
                        self.test_results['working_commands']['white'].append({
                            'command': cmd,
                            'description': f'Known white #{idx}',
                            'type': 'known'
                        })
                
                # Probar nuevos comandos
                print(f"\n🆕 NUEVOS COMANDOS DE BLANCO ({len(NEW_WHITE_COMMANDS)} comandos):")
                print("-" * 60)
                for idx, cmd_func in enumerate(NEW_WHITE_COMMANDS, 1):
                    cmd = cmd_func(200)  # Prueba con brillo 200
                    if await self.test_command(client, char_uuid, cmd, 
                                              f"Blanco #{idx} (brillo: 200)"):
                        self.test_results['working_commands']['white'].append({
                            'command_template': f'lambda brightness: {[hex(x) if isinstance(x, int) else "brightness" for x in cmd]}',
                            'description': f'New white #{idx}',
                            'type': 'new'
                        })
                        
        except Exception as e:
            print(f"\n❌ Error durante las pruebas: {e}")
    
    async def test_color_temp_commands(self, device: BLEDevice, char_uuid: str):
        """Prueba comandos de temperatura de color"""
        print(f"\n{'='*60}")
        print("🌡️  PROBANDO COMANDOS DE TEMPERATURA DE COLOR")
        print(f"{'='*60}\n")
        
        try:
            async with BleakClient(device.address, timeout=20.0) as client:
                print(f"✅ Conectado a {device.name}\n")
                
                # Probar comandos conocidos
                print("🌡️  COMANDOS DE TEMP. COLOR CONOCIDOS:")
                print("-" * 60)
                for idx, cmd in enumerate(KNOWN_COLOR_TEMP, 1):
                    if await self.test_command(client, char_uuid, cmd, 
                                              f"Temp. color #{idx} (conocido)"):
                        self.test_results['working_commands']['color_temp'].append({
                            'command': cmd,
                            'description': f'Known color temp #{idx}',
                            'type': 'known'
                        })
                
                # Probar nuevos comandos
                print(f"\n🆕 NUEVOS COMANDOS DE TEMP. COLOR ({len(NEW_COLOR_TEMP_COMMANDS)} comandos):")
                print("-" * 60)
                for idx, cmd_func in enumerate(NEW_COLOR_TEMP_COMMANDS, 1):
                    cmd = cmd_func(50, 50)  # 50% cálido, 50% frío
                    if await self.test_command(client, char_uuid, cmd, 
                                              f"Temp. color #{idx} (50% cálido/frío)"):
                        self.test_results['working_commands']['color_temp'].append({
                            'command_template': f'lambda warm, cold: {[hex(x) if isinstance(x, int) else "warm" if x == 50 else "cold" for x in cmd]}',
                            'description': f'New color temp #{idx}',
                            'type': 'new'
                        })
                        
        except Exception as e:
            print(f"\n❌ Error durante las pruebas: {e}")
    
    async def test_custom_commands(self, device: BLEDevice, char_uuid: str):
        """Permite al usuario probar sus propios comandos"""
        print(f"\n{'='*60}")
        print("🛠️  PRUEBA DE COMANDOS PERSONALIZADOS")
        print(f"{'='*60}\n")
        
        print("Puedes probar tus propios comandos en formato hexadecimal.")
        print("Ejemplo: 7e 00 04 f0 00 01 ff 00 ef")
        print("Escribe 'q' para terminar.\n")
        
        try:
            async with BleakClient(device.address, timeout=20.0) as client:
                print(f"✅ Conectado a {device.name}\n")
                
                while True:
                    cmd_input = input("🔧 Introduce comando (hex separado por espacios) o 'q': ").strip()
                    
                    if cmd_input.lower() == 'q':
                        break
                    
                    try:
                        # Parsear comando hexadecimal
                        cmd = [int(x, 16) for x in cmd_input.split()]
                        
                        description = input("   📝 Descripción del comando: ").strip()
                        
                        if await self.test_command(client, char_uuid, cmd, description):
                            self.test_results['custom_commands'].append({
                                'command': cmd,
                                'description': description,
                                'hex': cmd_input
                            })
                            
                    except ValueError:
                        print("   ❌ Formato inválido. Usa valores hex separados por espacios.")
                    except Exception as e:
                        print(f"   ❌ Error: {e}")
                        
        except Exception as e:
            print(f"\n❌ Error durante las pruebas: {e}")
    
    def generate_report(self):
        """Genera un informe completo de los resultados"""
        print(f"\n{'='*60}")
        print("📊 INFORME DE DESCUBRIMIENTO DE TIRA LED")
        print(f"{'='*60}\n")
        
        # Información del dispositivo
        print("📱 INFORMACIÓN DEL DISPOSITIVO:")
        print("-" * 60)
        info = self.test_results['device_info']
        print(f"Nombre: {info.get('name', 'N/A')}")
        print(f"Dirección MAC: {info.get('address', 'N/A')}")
        print(f"RSSI: {info.get('rssi', 'N/A')} dBm")
        
        # Características
        print(f"\n🔧 CARACTERÍSTICAS BLE:")
        print("-" * 60)
        chars = self.test_results['characteristics']
        print(f"Escritura: {len(chars.get('write', []))} características")
        print(f"Lectura: {len(chars.get('read', []))} características")
        print(f"Notificación: {len(chars.get('notify', []))} características")
        
        if chars.get('write'):
            print(f"\nCaracterísticas de escritura:")
            for char in chars['write']:
                print(f"  • {char['uuid']}")
        
        # Comandos funcionales
        working = self.test_results['working_commands']
        
        print(f"\n✅ COMANDOS FUNCIONALES ENCONTRADOS:")
        print("=" * 60)
        
        # Encendido
        if working['turn_on']:
            print(f"\n🟢 ENCENDIDO ({len(working['turn_on'])} comandos):")
            for cmd_info in working['turn_on']:
                cmd_hex = ' '.join(f'{b:02x}' for b in cmd_info['command'])
                print(f"  • {cmd_info['description']}")
                print(f"    Comando: {cmd_hex}")
                print(f"    Tipo: {cmd_info.get('type', 'N/A')}")
        else:
            print(f"\n🟢 ENCENDIDO: ❌ No se encontraron comandos funcionales")
        
        # Apagado
        if working['turn_off']:
            print(f"\n🔴 APAGADO ({len(working['turn_off'])} comandos):")
            for cmd_info in working['turn_off']:
                cmd_hex = ' '.join(f'{b:02x}' for b in cmd_info['command'])
                print(f"  • {cmd_info['description']}")
                print(f"    Comando: {cmd_hex}")
                print(f"    Tipo: {cmd_info.get('type', 'N/A')}")
        else:
            print(f"\n🔴 APAGADO: ❌ No se encontraron comandos funcionales")
        
        # Color
        if working['color']:
            print(f"\n🎨 COLOR RGB ({len(working['color'])} comandos):")
            for cmd_info in working['color']:
                print(f"  • {cmd_info['description']}")
                print(f"    Template: {cmd_info.get('command_template', 'N/A')}")
        else:
            print(f"\n🎨 COLOR RGB: ❌ No se encontraron comandos funcionales")
        
        # Blanco
        if working['white']:
            print(f"\n⚪ BLANCO ({len(working['white'])} comandos):")
            for cmd_info in working['white']:
                if 'command' in cmd_info:
                    cmd_hex = ' '.join(f'{b:02x}' for b in cmd_info['command'])
                    print(f"  • {cmd_info['description']}")
                    print(f"    Comando: {cmd_hex}")
                else:
                    print(f"  • {cmd_info['description']}")
                    print(f"    Template: {cmd_info.get('command_template', 'N/A')}")
        else:
            print(f"\n⚪ BLANCO: ❌ No se encontraron comandos funcionales")
        
        # Temperatura de color
        if working['color_temp']:
            print(f"\n🌡️  TEMPERATURA COLOR ({len(working['color_temp'])} comandos):")
            for cmd_info in working['color_temp']:
                if 'command' in cmd_info:
                    cmd_hex = ' '.join(f'{b:02x}' for b in cmd_info['command'])
                    print(f"  • {cmd_info['description']}")
                    print(f"    Comando: {cmd_hex}")
                else:
                    print(f"  • {cmd_info['description']}")
                    print(f"    Template: {cmd_info.get('command_template', 'N/A')}")
        else:
            print(f"\n🌡️  TEMPERATURA COLOR: ❌ No se encontraron comandos funcionales")
        
        # Comandos personalizados
        if self.test_results['custom_commands']:
            print(f"\n🛠️  COMANDOS PERSONALIZADOS ({len(self.test_results['custom_commands'])} comandos):")
            for cmd_info in self.test_results['custom_commands']:
                print(f"  • {cmd_info['description']}")
                print(f"    Comando: {cmd_info['hex']}")
        
        # Guardar a archivo JSON
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"led_discovery_{info.get('address', 'unknown').replace(':', '')}_{timestamp}.json"
        
        try:
            with open(filename, 'w') as f:
                json.dump(self.test_results, f, indent=2)
            print(f"\n💾 Informe guardado en: {filename}")
        except Exception as e:
            print(f"\n❌ Error al guardar informe: {e}")
        
        print(f"\n{'='*60}\n")


async def main():
    """Función principal"""
    discovery = LEDStripDiscovery()
    
    print("""
    ╔══════════════════════════════════════════════════════════╗
    ║   🔍 HERRAMIENTA DE DESCUBRIMIENTO DE TIRAS LED BLE    ║
    ║                                                          ║
    ║   Esta herramienta te ayudará a descubrir comandos      ║
    ║   para tiras LED BLE desconocidas                       ║
    ╚══════════════════════════════════════════════════════════╝
    """)
    
    try:
        # 1. Escanear dispositivos
        await discovery.scan_devices(duration=10)
        
        # 2. Seleccionar dispositivo
        device = await discovery.select_device()
        if not device:
            print("\n👋 Proceso cancelado")
            return
        
        # 3. Descubrir características
        characteristics = await discovery.discover_characteristics(device)
        
        # 4. Seleccionar característica de escritura
        char_uuid = await discovery.select_write_characteristic(characteristics)
        if not char_uuid:
            print("\n❌ No se pudo seleccionar característica de escritura")
            return
        
        # 5. Probar comandos de encendido/apagado
        response = input("\n¿Probar comandos de encendido/apagado? (s/n): ").strip().lower()
        if response == 's':
            await discovery.test_power_commands(device, char_uuid)
        
        # 6. Probar comandos de blanco
        response = input("\n¿Probar comandos de luz blanca? (s/n): ").strip().lower()
        if response == 's':
            await discovery.test_white_commands(device, char_uuid)
        
        # 7. Probar comandos de temperatura de color
        response = input("\n¿Probar comandos de temperatura de color? (s/n): ").strip().lower()
        if response == 's':
            await discovery.test_color_temp_commands(device, char_uuid)
        
        # 8. Probar comandos de color RGB
        response = input("\n¿Probar comandos de color RGB? (s/n): ").strip().lower()
        if response == 's':
            await discovery.test_color_commands(device, char_uuid)
        
        # 9. Comandos personalizados
        response = input("\n¿Probar comandos personalizados? (s/n): ").strip().lower()
        if response == 's':
            await discovery.test_custom_commands(device, char_uuid)
        
        # 10. Generar informe
        response = input("\n¿Mostrar informe final? (s/n): ").strip().lower()
        if response == 's':
            discovery.generate_report()
        
        print("\n✅ Proceso completado!")
        
    except KeyboardInterrupt:
        print("\n\n⚠️  Proceso interrumpido por el usuario")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
