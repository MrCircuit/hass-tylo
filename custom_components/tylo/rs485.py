import serial
import datetime
from crc import Calculator, Configuration

# Initialize the CRC calculator
crc_calc = Calculator(Configuration(width=16, polynomial=0x90d9, init_value=0xffff, final_xor_value=0, reverse_input=False, reverse_output=False), optimized=True)
        
run = True
ser = serial.Serial('COM6', 19200, timeout=1, parity=serial.PARITY_EVEN)

while run:
    data = ser.read_until(bytes.fromhex('9c'))
    if len(data) > 0 and data[0] == 0x98:
        # Decode the frame
        ts = datetime.datetime.now()
        payload = []
        isEscaped = False
        for i in range(1, len(data) - 1):
            d = data[i]
            if d == 0x91:
                isEscaped = True
                continue
            elif isEscaped:
                isEscaped = False
                if d == 0x63:
                    # The EOF byte
                    d = 0x9c
                elif d == 0x67:
                    # The SOF byte
                    d = 0x98
                elif d == 0x6E:
                    # The ESC byte itself
                    d = 0x91
                else:
                    print('Unknown escape sequence: 91 ' + '{:02x}'.format(d))
                    payload.append(0x91)      

            payload.append(d)
        
        # Check the CRC
        crc_ok = crc_calc.checksum(bytearray(payload)) == 0
        
        if len(payload) > 4:
            # print('[Frame] ' + data.hex())
            print(ts, bytearray(payload).hex() + ' -', 'CRC OK' if crc_ok else 'CRC wrong')

        if not crc_ok:
            continue

        # Decode the command. Known structure:
        # First byte is always 40, except at the start (7f = broadcast?) - maybe an address?
        # 7F 00 340A CRC          - First messages on the bus - probably a broadcast
        # 40 06 CRC               - keepalive, from heater to control
        # 40 07 CRC               - keepalive, from control to heater (probably ACK)
        # 40 06 xxxx yyyyyyyy CRC - request, from heater to control
        # 40 07 xxxx yyyyyyyy CRC - command, from control to heater
        # 40 08 xxxx yyyyyyyy CRC - data, from heater to control
        # 40 09 xxxx yyyyyyyy CRC - data, from control to heater (probably ACK)
        # 40 0A ???? CRC          - unknown
        #
        # Usually (but not in any case), the 06/07 and 08/09 doublets will come in pairs, directly one after the other.
        #
        # Code Data (? unknown, 0/1 fixed data, # numeric data, b binary data)
        # xxxx yyyyyyyy - Function description
        # ------------------------------------
        # 1800 ???????? - (During startup) After a 06 request, the control sends a 07 answer, followed by 08/09 mutual ACKs
        # 1801 ???????? - (During startup) After a 06 request, the control sends a 07 answer, followed by 08/09 mutual ACKs
        # 1802 ???????? - (During startup) After a 06 request, the control sends a 07 answer, followed by 08/09 mutual ACKs
        # 1803 ???????? - (During startup) After a 06 request, the control sends a 07 answer, followed by 08/09 mutual ACKs
        # 1A00 ???????? - (During startup) After a 06 request, the control sends a 07 answer, followed by 08/09 mutual ACKs
        # 1A01 ???????? - (During startup) After a 06 request, the control sends a 07 answer, followed by 08/09 mutual ACKs
        # 3800 ???????? - (During startup) After a 06 request, the control sends a 07 answer, followed by 08/09 mutual ACKs
        # 3801 ???????? - (During startup) After a 06 request, the control sends a 07 answer, followed by 08/09 mutual ACKs
        # 1400 ???????? - (During startup) A 08/09 pair
        # 1401 ???????? - (During startup) A 08/09 pair
        # 1402 ???????? - (During startup) A 08/09 pair - (same content as in 1803 before)
        # 1600 ???????? - (During startup) A 08/09 pair
        # 1700 7BCB4180 - (During startup) A 08/09 pair - (tested in program #1) probably the heater tells the control the maximum bathing time setting
        # 2600 ???????? - (During startup) A 08/09 pair
        # 4000 ???????? - (During startup) A 08/09 pair
        # 5000 ???????? - (During startup) A 08/09 pair
        # C400 ???????? - (During startup) A 08/09 pair
        # C401 ???????? - (During startup) A 08/09 pair
        # C410 ???????? - (During startup) A 08/09 pair
        # C411 ???????? - (During startup) A 08/09 pair
        # C430 ???????? - (During startup) A 08/09 pair
        # (normal operation)
        # 3400 bbbbbbbb - State bits, sent between on/off command and acknowledge, known values so far:
        #      00000001 - light off / heater off
        #      00000009 - light on / heater off
        #      00000011 - light off / heater on
        #      00000019 - light on / heater on
        # 4002 7BCB4040 - Bathing time setting #1 1h (tested in program #1)
        #          4080 - Bathing time setting #2 2h (tested in program #1)
        #          40C0 - Bathing time setting #3 3h (tested in program #1)
        #          4100 - Bathing time setting #4 4h (tested in program #1)
        #          4140 - Bathing time setting #5 5h (tested in program #1)
        #          4180 - Bathing time setting #6 6h (tested in program #1)
        # 4003 ???????? - Unknown yet, big number or state code, occurs every 15s
        # 6000 ######## - Temperature with following bit definition
        #               - Bits  0..10 (0..227°C, 1/9K steps) - current measured temperature
        #               - Bits 11..20 (0..227°C, 1/9K steps) - temperature setting
        #               - Bits 21..31 - unused 
        # 7000 00000000 - Command acknowledge
        #      00000001 - Heater on/off toggle
        #      00000002 - Light on/off toggle
        # 7180 bbbbbbbb - State bits, sent after on/off acknowledge, known values so far:
        #      00000000 - light off / heater off
        #      00020000 - light on / heater off
        #      0001C000 - light off / heater on
        #      0003C000 - light on / heater on
        # 9400 ######## - Minute up counter (total operating time of the heater)
        # 9401 ######## - Minute down counter (selected bathing time setting)