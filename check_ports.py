#!/usr/bin/env python3
"""Check available serial ports."""
try:
    import serial.tools.list_ports
    
    print('Available COM ports:')
    ports = list(serial.tools.list_ports.comports())
    
    if ports:
        for port in ports:
            print(f'  {port.device} - {port.description}')
            if port.manufacturer:
                print(f'    Manufacturer: {port.manufacturer}')
            print()
    else:
        print('  No COM ports detected')
        print('  Make sure your RS485 adapter is connected')
        print()
        
except ImportError:
    print('  pyserial not installed - run: pip install pyserial')
except Exception as e:
    print(f'  Error: {e}')