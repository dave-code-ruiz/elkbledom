from bluepy.btle import Scanner, DefaultDelegate, BTLEDisconnectError, Peripheral, BTLEException
from queue import Queue
from threading import Thread
import logging

_LOGGER = logging.getLogger(__name__)

class OperationType:
    LOCK_FULL = 1
    LOCK_ONE = 2
    LOCK_NIGHT_MODE = 1
    UNLOCK = 4
    GET_REPORT = 5
    ADJUST_NUMBER_OF_ROTATION = 8
    START_LEARNING_MODE = 9
    DELETE_ALL_CONTROLLERS = 10
    GET_READY_FOR_DELETE_USER = 11
    BUZZER_REPORT = 12
    GET_USERS = 13
    GET_INFORMATION = 14
    START_UPDATE_MODE = 15
    GET_KEY = "!"
    WAIT = "&"
    DISCONNECT = "#"
    GET_CHECK_IN_OUT_TIMES = "?"
    GET_AUTO_LOCK_DAY_TIMES = "+"
    LEARN_SUCCESS = "*"

class BleServicesAndChracteristicsChars:
    CLIENT_CHARACTERISTIC_CONFIG = "00002902-0000-1000-8000-00805f9b34fb"
    BLE_SERVICES = ["00035b03-58e6-07dd-021a-08123a000300","49535343-FE7D-4AE5-8FA9-9FAFD205E455","6e400001-b5a3-f393-e0a9-e50e24dcca9e"]
    BLE_WRITE_CHARACTERISTICS = {"00035b03-58e6-07dd-021a-08123a000301","49535343-1E4D-4BD9-BA61-23C647249616","6e400002-b5a3-f393-e0a9-e50e24dcca9e"}
    BLE_READ_CHARACTERISTICS = {"00035b03-58e6-07dd-021a-08123a0003ff","49535343-1E4D-4BD9-BA61-23C647249616","6e400003-b5a3-f393-e0a9-e50e24dcca9e"}
    DEVICE_NAME_CONTENT = "UTOPIC"
    
class cDelegate(DefaultDelegate):
    def __init__(self):
        DefaultDelegate.__init__(self)

    def handleDiscovery(self, dev, isNewDev, isNewData):
        if isNewDev:
            print("Discovered device", dev.addr)
        elif isNewData:
            print("Received new data from", dev.addr)

class Discovery():
    def __init__(self):
        scanner = Scanner().withDelegate(cDelegate())
        self.devices = scanner.scan(10.0)
        self.utopicdevice = []

    def getDevices(self, address = None):
        if address is None:
            for dev in self.devices:
                print("Device %s (%s), RSSI=%d dB" % (dev.addr, dev.addrType, dev.rssi))
                utdv = UtopicDevice(dev)
                if utdv.getDevice() is not None:
                    self.utopicdevice.append(utdv)
        else:
            print("return device address")
        return self.utopicdevice

class UtopicDevice():
    def __init__(self, device):
        self.device = device
        self.utopicdevice = None
        self.writeChar = None
        self.readChar = None
        self.notChar = None
        for (adtype, desc, value) in device.getScanData():
            print("  %s = %s" % (desc, value))
            if value == BleServicesAndChracteristicsChars.DEVICE_NAME_CONTENT:
                self.utopicdevice = self
            if value in BleServicesAndChracteristicsChars.BLE_SERVICES:
                self.serviceuuid = value

    def getAddress(self):
        return self.device.addr

    def getServiceUUID(self):
        return self.serviceuuid

    def getDevice(self):
        return self.utopicdevice

    def setWriteCharact(self, writeChar):
        self.writeChar = writeChar

    def getWriteCharact(self):
        return self.writeChar

    def setReadCharact(self, readChar):
        self.readChar = readChar

    def getReadCharact(self):
        return self.readChar

    def setNotifyCharact(self, notChar):
        self.notChar = notChar

    def getNotifyCharact(self):
        return self.notChar

class BLEMagic(DefaultDelegate):

    def __init__(self):
        super().__init__()
        discover = Discovery()
        self.devices = discover.getDevices()
        self.utopicKey = None
        self.utopicdevices = []
        self.periph = None
        
        # create the TX queue
        self._tx_queue = Queue()

        # start the bluepy IO thread
        self._bluepy_thread = Thread(target=self._bluepy_handler)
        self._bluepy_thread.name = "bluepy_handler"
        self._bluepy_thread.daemon = True
        self._bluepy_thread.start()

    def handleNotification(self, cHandle, data):
        """This is the notification delegate function from DefaultDelegate
        """
        print("\nReceived Notification: %s Handle: %s",str(data), cHandle)

    def _bluepy_handler(self):
        """This is the bluepy IO thread
        :return:
        """
        #ADDRESS OF MAGIC: 04:91:62:25:cb:6f
        for utopicdevice in self.devices:
            serviceuuid = utopicdevice.getServiceUUID()
            address = utopicdevice.getAddress()
            # address = "04:91:62:25:cb:6f"
            print(address)
            if serviceuuid in BleServicesAndChracteristicsChars.BLE_SERVICES:
                try:
                    self.periph = Peripheral(address.upper())
                    self.periph.withDelegate(self)
                    print("conecta")
                except BTLEDisconnectError as e:
                    _LOGGER.error("Disconected: %s", e)
                except BTLEException as e:
                    _LOGGER.error("Error: %s", e)
                if self.periph is not None:
                    service = self.periph.getServiceByUUID(serviceuuid)
                    print(service)
                    #for charact in service.getCharacteristics():
                    descs = service.getDescriptors()
                    for desc in descs:
                        str_uuid = str(desc.uuid).lower()
                        print(str_uuid, desc.handle)
                        if str_uuid in BleServicesAndChracteristicsChars.BLE_WRITE_CHARACTERISTICS:
                            utopicdevice.setWriteCharact(desc.handle)
                        if str_uuid in BleServicesAndChracteristicsChars.CLIENT_CHARACTERISTIC_CONFIG:
                            utopicdevice.setNotifyCharact(desc.handle)
                        if str_uuid in BleServicesAndChracteristicsChars.BLE_READ_CHARACTERISTICS:
                            #state = self.kv2dict(charact.read().decode())
                            #print(state)
                            utopicdevice.setReadCharact(desc.handle)
            subscribe_bytes = b'\x01\x00'
            if utopicdevice.getReadCharact() is not None and utopicdevice.getWriteCharact() is not None:
                response = self.periph.writeCharacteristic(utopicdevice.getNotifyCharact(), subscribe_bytes, withResponse=True)
                print(response)
                # now that we're subscribed for notifications, waiting for TX/RX...
                while True:
                    while not self._tx_queue.empty():
                        msg = self._tx_queue.get_nowait()
                        msg_bytes = bytes(msg, encoding="utf-8")
                        self.periph.writeCharacteristic(utopicdevice.getWriteCharact(), msg_bytes)

                    self.periph.waitForNotifications(1.0)
            else:
                print("not read")
            self.utopicdevices.append(utopicdevice)
    
    def kv2dict(kvstr, sep=";"):
        result = {}
        for x in kvstr.split(sep, 50):
            (k, v) = x.split("=", 2)
            result[k] = v
        return result

    def get_key(self):
        return self.utopicKey

    def getDevices(self):
        return self.utopicdevices

    def onDataReceived(self, data):
        #String data = new String(dataRaw);
        if(data.contains("DEV_KEY:")):
            key = data.substring(8,data.length())
            self.utopicKey = key
            # Database.getInstance().addNewBarrel(UtopicDevice.SelectedUtopicDevice.getMacId(),UtopicDevice.SelectedUtopicDevice.getName(),SelectedTag);
            # RecognitionState = eRecognitionState.S2_SENDING_OPEN;

    # Utopic
    def create_operation(self, type):
        if type in (OperationType.GET_KEY, OperationType.DISCONNECT, OperationType.GET_CHECK_IN_OUT_TIMES, OperationType.GET_AUTO_LOCK_DAY_TIMES, OperationType.LEARN_SUCCESS):
            return type
        else:
            utopicKey = self.utopicdevices.getAddress()
            myMacAdress = '22:33:44:55:66:77' #GetMacAdress()
            userKey = ""
            for pos in myMacAdress.split(":"):
                userKey += pos
            print(userKey)
            counter=0
            counter+=1

            # hashit = counter + type + settings
            # self.key = base64.b64encode(hashlib.md5(hashit.encode()).digest())[:16]
            # try:
            #     auth.write("M=0;K=".encode() + self.key, True)
            # except:
            #     print("ERROR: failed to unlock %s - wrong pincode?" % self.name)
            # return not self.locked

            # Encryption encryp = new Encryption(new BigInteger(userKey.trim(), 16).longValue(), utopicKey);
            # byte[] key = encryp.encrypt(counter, operation, settings);
            # return key;

    def send(self, message):
        """Call this function to send a BLE message over the UART service
        :param message: Message to send
        :return:
        """

        # put the message in the TX queue
        self._tx_queue.put_nowait(message)

Ble = BLEMagic()
