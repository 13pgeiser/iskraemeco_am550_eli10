#!/usr/bin/python3
import datetime
import serial
from enum import Enum

class Mode(Enum):
    STATIC = 1
    DYNAMIC = 2
    PROMETHEUS = 3

MODE = Mode.PROMETHEUS

# IEC 62056 HDLC (mode E)
def crc16(data):
    crc = 0xFFFF
    for c in data:
        crc ^= c
        for _ in range(8):
            if (crc & 1) > 0:
                crc = (crc >> 1) ^ 0x8408
            else:
                crc = crc >> 1
        crc &= 0xFFFF
    crc = ~crc
    return crc & 0xFFFF


class Am550:
    TAG_STRUCTURE = 2
    TAG_UINT32 = 6
    TAG_OCTET_STRING = 9
    TAG_UINT16 = 18
    debug = False

    def __init__(self):
        self._escape_next = False
        self._data = []

    def parse(self, data: bytes):
        data = data[1:-1]
        crc = data[-2:]
        crc = crc[1] << 8 | crc[0]
        data = data[:-2]
        computed_crc = crc16(data)
        if crc == computed_crc:
            return self.parse_cosem_frame(data)
        else:
            print("Invalid crc16 -> 0x%04X 0x%04X" % (crc, computed_crc))
            return []

    def parse_cosem_frame(self, data: bytes):
        values = []
        try:
            if self.debug:
                print("##################################################")
                print(len(data))
                print(" ".join(["%02X" % x for x in data]))
                print("---")
            data = data[16:]
            if self.debug:
                print(" ".join(["%02X" % x for x in data]))
                print("##################################################")
            indent = 0
            structure_len = 0
            offset = 0
            array_len = data[offset]
            array_data = data[offset + 1 : offset + 1 + array_len]
            # print(' ' * indent + 'array_data: ' + str(array_data))
            year = array_data[0] << 8 | array_data[1]
            month = array_data[2]
            day = array_data[3]
            _dayOfWeek = array_data[4]
            hour = array_data[5]
            minute = array_data[6]
            second = array_data[7]
            ms = array_data[8]
            # print('%d/%d/%d %d:%d:%d:%d' % (year, month, day, hour, minute, second, ms))
            dt = datetime.datetime(year, month, day, hour, minute, second, ms * 1000)
            if self.debug:
                print(dt)
            values.append(dt)
            offset += 1 + array_len

            while offset < len(data):
                if structure_len == 0:
                    indent = 0
                if structure_len > 0:
                    structure_len -= 1

                if data[offset] == Am550.TAG_STRUCTURE:
                    structure_len = data[offset + 1]
                    indent = 4
                    offset += 2
                    continue

                if data[offset] == Am550.TAG_UINT32:
                    value = int.from_bytes(
                        data[offset + 1 : offset + 5], byteorder="big", signed=False
                    )
                    if self.debug:
                        print(" " * indent + "Uint32: 0x%08X (%d)" % (value, value))
                    values.append(value)
                    offset += 5
                    continue

                if data[offset] == Am550.TAG_OCTET_STRING:
                    length = data[offset + 1]
                    string = data[offset + 2 : offset + 2 + length].decode()
                    if self.debug:
                        print(" " * indent + "OctetString: " + string)
                    values.append(string)
                    offset += length + 2
                    continue

                if data[offset] == Am550.TAG_UINT16:
                    value = int.from_bytes(
                        data[offset + 1 : offset + 3], byteorder="big", signed=False
                    )
                    if self.debug:
                        print(" " * indent + "Uint16: 0x%04X (%d)" % (value, value))
                    values.append(value)
                    offset += 3
                    continue

                if self.debug:
                    print(data[offset])
                break
        except Exception as e:
            print(e)
        return values

def get_serial():
    ser = serial.Serial()
    ser.baudrate = 115200
    ser.stopbits = serial.STOPBITS_ONE
    ser.bytesize = serial.EIGHTBITS
    ser.parity = serial.PARITY_NONE
    ser.timeout = 5
    ser.port = "/dev/ttyUSB0"
    ser.open()
    return ser

am550 = Am550()
if MODE == Mode.STATIC:
    # 7EA05CCF022313C662E6E7000F000003030C07E90B08060F172800FFC400020C0908383933383332353006000002F3060000000006005AE5230600823A0E12002F12001E1201640600381768060022CDBB0600823A0E0600000000DBA37E
    # 2025-11-08 15:23:40
    #     OctetString: 89383250
    #     Uint32: 0x000002F3 (755)     # 1.1.7.0 Instant positive
    #     Uint32: 0x00000000 (0)       # 1.2.7.0 ??? Instant negative?
    #     Uint32: 0x005AE523 (5956899) # 1.1.8.0
    #     Uint32: 0x00823A0E (8534542) # 1.2.8.0
    #     Uint16: 0x002F (47)
    #     Uint16: 0x001E (30)
    #     Uint16: 0x0164 (356)
    #     Uint32: 0x00381768 (3676008) # 1.1.8.1
    #     Uint32: 0x0022CDBB (2280891) # 1.1.8.2
    #     Uint32: 0x00823A0E (8534542) # 1.2.8.1
    #     Uint32: 0x00000000 (0)       # 1.2.8.2
    data = bytes.fromhex('7EA05CCF022313C662E6E7000F000003030C07E90B08060F172800FFC400020C0908383933383332353006000002F3060000000006005AE5230600823A0E12002F12001E1201640600381768060022CDBB0600823A0E0600000000DBA37E')
    print(am550.parse(data))
elif MODE == Mode.DYNAMIC:
    ser = get_serial()
    while True:
        print(am550.parse(ser.read(100)))
elif MODE == Mode.PROMETHEUS:
    from prometheus_client import start_http_server, Gauge
    obis_170 = Gauge('1.7.0', 'Positive active instananeous power')
    obis_270 = Gauge('2.7.0', 'Negative active instananeous power')
    obis_180 = Gauge('1.8.0', 'Active energy consumed')
    obis_280 = Gauge('2.8.0', 'Active energy returned')
    unkn_001 = Gauge('unknown 001', 'unknown 001')
    unkn_002 = Gauge('unknown 002', 'unknown 002')
    unkn_003 = Gauge('unknown 003', 'unknown 003')
    obis_181 = Gauge('1.8.1', 'Active energy consumed, tarif 1')
    obis_182 = Gauge('1.8.2', 'Active energy consumed, tarif 2')
    obis_281 = Gauge('2.8.1', 'Active energy returned, tarif 1')
    obis_282 = Gauge('2.8.2', 'Active energy returned, tarif 2')
    start_http_server(10000)
    ser = get_serial()
    while True:
        values = am550.parse(ser.read(100))
        dt, serial, inst_p, inst_n, cons_tot, ret_tor, un1, un2, un3, cons_t1, cons_t2, ret_t1, ret_t2 = values
        obis_170.set(inst_p)
        obis_270.set(inst_n)
        obis_180.set(cons_tot)
        obis_280.set(ret_tor)
        unkn_001.set(un1)
        unkn_002.set(un2)
        unkn_003.set(un3)
        obis_181.set(cons_t1)
        obis_182.set(cons_t2)
        obis_281.set(ret_t1)
        obis_282.set(ret_t2)
else:
    raise Exception('Unsupported')
